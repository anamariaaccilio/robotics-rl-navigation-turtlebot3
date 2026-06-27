"""
dagger_agent.py
DAgger (Dataset Aggregation) con EXPERTO HUMANO por teclado.

Cumple la consigna 4.2:
  - El agente A2C pilotea el robot en Gazebo (modo AUTO).
  - El humano puede intervenir en cualquier momento con el teclado (modo HUMANO).
  - Mientras interviene, se CAPTURA el par (estado, accion experta continua).
  - Con esos pares se hace FINE-TUNING de la red (imitacion) in situ.
  - Se valida que el agente aprende de la intervencion.

Uso:
  ros2 run turtlebot3_a2c dagger          # parte del modelo a2c_sim.pth
  ros2 run turtlebot3_a2c dagger MODELO   # parte de a2c_models/MODELO.pth

CONTROLES (en la terminal del agente):
  i           -> alternar INTERVENCION humana (AUTO <-> HUMANO)
  w / x       -> mas / menos velocidad lineal
  a / d       -> girar izquierda / derecha
  s o espacio -> detener (v=0, w=0)
  t           -> FINE-TUNING con lo capturado (imitar al experto)
  r           -> reiniciar episodio
  q           -> guardar (a2c_dagger.pth) y salir
"""
import os
import sys
import time
import threading
import numpy as np

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

import rclpy
from rclpy.executors import MultiThreadedExecutor

from . import settings as S
from .environment import Turtlebot3Env
from .networks import ActorCritic
from .utils import RunningMeanStd
from .keyboard import KeyboardReader

LIN_STEP = 0.02
ANG_STEP = 0.2
DAGGER_MODEL_NAME = "a2c_dagger"


class DAggerAgent:
    def __init__(self, env, base_name='a2c_sim'):
        self.env = env
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.model = ActorCritic(S.STATE_DIM, S.ACTION_DIM, S.HIDDEN,
                                 S.V_MAX, S.W_MAX).to(self.device)
        self.rms = RunningMeanStd(S.STATE_DIM) if S.USE_STATE_NORM else None
        self._load_base(base_name)

        # optimizador de fine-tuning (lr pequeno: solo ajustamos, no reentrenamos)
        self.opt = torch.optim.Adam(self.model.parameters(), lr=1e-4)

        # dataset agregado de DAgger: (estado_normalizado, accion_experta_normalizada)
        self.X = []   # estados
        self.Y = []   # acciones expertas (en espacio normalizado [-1,1])

        # estado de la teleoperacion
        self.human_mode = False
        self.hv = 0.0   # velocidad lineal comandada por el humano
        self.hw = 0.0   # velocidad angular comandada por el humano

    # ---------- cargar el modelo base A2C ----------
    def _load_base(self, name):
        path = os.path.join(S.MODEL_DIR, f'{name}.pth')
        if os.path.exists(path):
            data = torch.load(path, map_location=self.device)
            self.model.load_state_dict(data['model'])
            if self.rms is not None and 'rms_mean' in data:
                self.rms.mean = data['rms_mean']
                self.rms.var = data['rms_var']
            self.env.get_logger().info(f'Modelo base cargado: {path}')
        else:
            self.env.get_logger().warn(
                f'No existe {path}. Empiezo con pesos nuevos. '
                f'(Deja que A2C entrene >=50 episodios para tener a2c_sim.pth)')

    # ---------- helpers ----------
    def _norm(self, state):
        if self.rms is None:
            return state.astype(np.float32)
        return self.rms.normalize(state).astype(np.float32)

    def _to_tensor(self, x):
        return torch.as_tensor(x, dtype=torch.float32, device=self.device)

    def _action_to_norm(self, v, w):
        """Convierte una accion real (v, w) del experto a espacio normalizado [-1,1]."""
        a0 = 2.0 * v / S.V_MAX - 1.0
        a1 = w / S.W_MAX
        return np.clip([a0, a1], -1.0, 1.0).astype(np.float32)

    def _policy_action(self, ns):
        """Accion del agente A2C (la media, determinista)."""
        with torch.no_grad():
            dist, _ = self.model(self._to_tensor(ns).unsqueeze(0))
            exec_a = self.model.scale_action(dist.mean).squeeze(0).cpu().numpy()
        return exec_a

    # ---------- fine-tuning por imitacion (DAgger) ----------
    def finetune(self, epochs=60, batch=64):
        n = len(self.X)
        if n < 16:
            self.env.get_logger().warn(
                f'Pocos datos para entrenar ({n}). Interviene mas con el teclado.')
            return
        X = self._to_tensor(np.array(self.X, dtype=np.float32))
        Y = self._to_tensor(np.array(self.Y, dtype=np.float32))
        loader = DataLoader(TensorDataset(X, Y), batch_size=batch, shuffle=True)

        self.model.train()
        last = 0.0
        for _ in range(epochs):
            for xb, yb in loader:
                dist, _ = self.model(xb)
                pred = dist.mean                       # accion que predice la red
                loss = ((pred - yb) ** 2).mean()       # imitar al experto (MSE)
                self.opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), S.MAX_GRAD_NORM)
                self.opt.step()
                last = float(loss)
        self.model.eval()
        self._save()
        self.env.get_logger().info(
            f'Fine-tuning hecho con {n} pares | loss imitacion {last:.4f} '
            f'-> guardado {DAGGER_MODEL_NAME}.pth. Vuelve a AUTO (i) y valida.')

    def _save(self):
        path = os.path.join(S.MODEL_DIR, f'{DAGGER_MODEL_NAME}.pth')
        data = {'model': self.model.state_dict()}
        if self.rms is not None:
            data['rms_mean'] = self.rms.mean
            data['rms_var'] = self.rms.var
        torch.save(data, path)

    # ---------- manejo de teclas ----------
    def _handle_key(self, key):
        if key == 'i':
            self.human_mode = not self.human_mode
            if not self.human_mode:
                self.hv, self.hw = 0.0, 0.0
            modo = 'HUMANO (intervencion)' if self.human_mode else 'AUTO (agente A2C)'
            self.env.get_logger().info(f'>>> Modo: {modo}')
        elif key == 'w':
            self.hv = min(self.hv + LIN_STEP, S.V_MAX)
        elif key == 'x':
            self.hv = max(self.hv - LIN_STEP, 0.0)
        elif key == 'a':
            self.hw = min(self.hw + ANG_STEP, S.W_MAX)
        elif key == 'd':
            self.hw = max(self.hw - ANG_STEP, -S.W_MAX)
        elif key in (' ', 's'):
            self.hv, self.hw = 0.0, 0.0
        elif key == 't':
            self.env.get_logger().info('Entrenando (imitacion)...')
            self.finetune()
        elif key == 'r':
            self.env.reset()
        return key == 'q'

    # ---------- bucle principal ----------
    def run(self):
        kb = KeyboardReader()
        self._print_help()
        state = self.env.reset()
        try:
            while rclpy.ok():
                key = kb.get_key()
                if key and self._handle_key(key):
                    break

                ns = self._norm(state)
                if self.human_mode:
                    exec_action = np.array([self.hv, self.hw], dtype=np.float32)
                    # CAPTURAR el par (estado, accion experta) -> dataset DAgger
                    self.X.append(ns)
                    self.Y.append(self._action_to_norm(self.hv, self.hw))
                else:
                    exec_action = self._policy_action(ns)

                next_state, reward, done, info = self.env.step(exec_action)
                state = self.env.reset() if done else next_state
        except KeyboardInterrupt:
            pass
        finally:
            kb.restore()
            self.env._stop_robot()
            self._save()
            self.env.get_logger().info(
                f'Saliendo. Dataset final: {len(self.X)} pares. Modelo: {DAGGER_MODEL_NAME}.pth')

    def _print_help(self):
        print("\n==================== DAgger - Experto Humano ====================")
        print(" i = intervenir (AUTO <-> HUMANO) | t = entrenar (imitar)")
        print(" w/x = lineal +/-  | a/d = girar izq/der | s = parar")
        print(" r = reiniciar episodio            | q = guardar y salir")
        print(" Empieza en AUTO: el agente A2C pilotea. Pulsa 'i' para tomar el control.")
        print("=================================================================\n")


def main():
    rclpy.init()
    env = Turtlebot3Env()
    executor = MultiThreadedExecutor()
    executor.add_node(env)
    threading.Thread(target=executor.spin, daemon=True).start()
    time.sleep(1.0)

    base = sys.argv[1] if len(sys.argv) > 1 else 'a2c_sim'
    agent = DAggerAgent(env, base_name=base)
    try:
        agent.run()
    finally:
        env.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
