import os
import sys
import time
import threading
import numpy as np

import torch
import torch.nn as nn

import rclpy
from rclpy.executors import MultiThreadedExecutor

from . import settings as S
from .environment import Turtlebot3Env
from .networks import ActorCritic
from .utils import RunningMeanStd, compute_gae


def _device():
    return torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class A2CAgent:
    def __init__(self, env, train=True, load_name=None):
        self.env = env
        self.train_mode = train
        self.device = _device()
        env.get_logger().info(f'Dispositivo: {self.device}')

        self.model = ActorCritic(S.STATE_DIM, S.ACTION_DIM, S.HIDDEN,
                                 S.V_MAX, S.W_MAX).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=S.LR)
        self.rms = RunningMeanStd(S.STATE_DIM) if S.USE_STATE_NORM else None

        os.makedirs(S.MODEL_DIR, exist_ok=True)
        if load_name:
            self._load(load_name)

    def _save(self, name):
        path = os.path.join(S.MODEL_DIR, f'{name}.pth')
        data = {'model': self.model.state_dict()}
        if self.rms is not None:
            data['rms_mean'] = self.rms.mean
            data['rms_var'] = self.rms.var
        torch.save(data, path)

    def _load(self, name):
        path = os.path.join(S.MODEL_DIR, f'{name}.pth')
        data = torch.load(path, map_location=self.device)
        self.model.load_state_dict(data['model'])
        if self.rms is not None and 'rms_mean' in data:
            self.rms.mean = data['rms_mean']
            self.rms.var = data['rms_var']
        self.env.get_logger().info(f'Modelo cargado: {path}')

    def _norm(self, state):
        if self.rms is None:
            return state
        return self.rms.normalize(state).astype(np.float32)

    def _to_tensor(self, x):
        return torch.as_tensor(x, dtype=torch.float32, device=self.device)

    def _update(self, batch, last_state, last_done):
        states = np.array(batch['states'], dtype=np.float32)
        norm_actions = np.array(batch['actions'], dtype=np.float32)
        rewards = batch['rewards']
        dones = batch['dones']
        values = batch['values']

        with torch.no_grad():
            if last_done:
                last_value = 0.0
            else:
                _, lv = self.model(self._to_tensor(self._norm(last_state)).unsqueeze(0))
                last_value = float(lv.item())

        adv, returns = compute_gae(rewards, values, dones, last_value,
                                   S.GAMMA, S.GAE_LAMBDA)
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        states_t = self._to_tensor(states)
        actions_t = self._to_tensor(norm_actions)
        adv_t = self._to_tensor(adv)
        returns_t = self._to_tensor(returns)

        logp, val, entropy = self.model.evaluate(states_t, actions_t)

        # ---- Las 3 losses de A2C ----
        loss_actor = -(logp * adv_t).mean()
        loss_critic = S.C_VALUE * (returns_t - val).pow(2).mean()
        loss_entropy = -S.C_ENTROPY * entropy.mean()
        loss = loss_actor + loss_critic + loss_entropy

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), S.MAX_GRAD_NORM)
        self.optimizer.step()
        return float(loss_actor), float(loss_critic), float(entropy.mean())

    def train(self):
        episode = 0
        ep_reward = 0.0
        successes = 0
        state = self.env.reset()
        if self.rms is not None:
            self.rms.update(state)

        batch = {k: [] for k in ['states', 'actions', 'rewards', 'dones', 'values']}

        while episode < S.MAX_EPISODES and rclpy.ok():
            for _ in range(S.ROLLOUT_STEPS):
                ns = self._norm(state)
                norm_action, exec_action, logp, value = self.model.act(
                    self._to_tensor(ns).unsqueeze(0))
                norm_action = norm_action.squeeze(0).cpu().numpy()
                exec_action = exec_action.squeeze(0).cpu().numpy()

                next_state, reward, done, info = self.env.step(exec_action)

                batch['states'].append(ns)
                batch['actions'].append(norm_action)
                batch['rewards'].append(reward)
                batch['dones'].append(1.0 if done else 0.0)
                batch['values'].append(float(value.item()))

                ep_reward += reward
                state = next_state
                if self.rms is not None:
                    self.rms.update(state)

                if done:
                    episode += 1
                    if info['outcome'] == 'success':
                        successes += 1
                    self.env.get_logger().info(
                        f"Ep {episode:4d} | reward {ep_reward:8.2f} | "
                        f"{info['outcome']:9s} | exitos {successes}")
                    ep_reward = 0.0
                    if episode % S.SAVE_EVERY == 0:
                        self._save(S.MODEL_NAME)
                        self.env.get_logger().info('  -> modelo guardado (a2c_sim.pth)')
                    if episode >= S.MAX_EPISODES:
                        break
                    state = self.env.reset()
                    if self.rms is not None:
                        self.rms.update(state)

            la, lc, ent = self._update(batch, state, batch['dones'][-1] == 1.0)
            self.env.get_logger().info(
                f"   update | L_actor {la:+.3f} | L_critic {lc:+.3f} | H {ent:+.3f}")
            batch = {k: [] for k in batch}

        self._save(S.MODEL_NAME)
        self.env.get_logger().info('Entrenamiento terminado -> a2c_sim.pth')

    def test(self):
        episode = 0
        while episode < 50 and rclpy.ok():
            state = self.env.reset()
            done = False
            ep_reward = 0.0
            while not done and rclpy.ok():
                ns = self._norm(state)
                with torch.no_grad():
                    dist, _ = self.model(self._to_tensor(ns).unsqueeze(0))
                    norm_action = dist.mean
                    exec_action = self.model.scale_action(norm_action).squeeze(0).cpu().numpy()
                state, reward, done, info = self.env.step(exec_action)
                ep_reward += reward
            episode += 1
            self.env.get_logger().info(
                f"[TEST] Ep {episode} | reward {ep_reward:.2f} | {info['outcome']}")


def _run(train_mode):
    rclpy.init()
    env = Turtlebot3Env()

    executor = MultiThreadedExecutor()
    executor.add_node(env)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    time.sleep(1.0)

    load_name = sys.argv[1] if len(sys.argv) > 1 else None
    agent = A2CAgent(env, train=train_mode, load_name=load_name)
    try:
        if train_mode:
            agent.train()
        else:
            agent.test()
    except KeyboardInterrupt:
        pass
    finally:
        env._stop_robot()
        env.destroy_node()
        rclpy.shutdown()


def main():
    _run(train_mode=True)


def main_test():
    _run(train_mode=False)


if __name__ == '__main__':
    main()