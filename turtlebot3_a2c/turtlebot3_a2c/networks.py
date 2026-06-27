"""
networks.py
Red Actor-Critic para accion CONTINUA (politica Gaussiana).

Estructura (igual que tu clase: tronco compartido + 2 cabezas):
  estado --> tronco --> [cabeza ACTOR  -> media de la Gaussiana]
                        [cabeza CRITICO -> V(s) escalar       ]

La politica trabaja en un espacio normalizado [-1, 1] por dimension;
luego se escala a (v, w) reales para enviar al robot. Esto mantiene la
desviacion estandar con una escala util y estabiliza el entrenamiento.
"""
import torch
import torch.nn as nn
from torch.distributions import Normal


class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim, hidden=256, v_max=0.22, w_max=2.0):
        super().__init__()
        self.v_max = v_max
        self.w_max = w_max

        # Tronco compartido (Tanh: mas estable que ReLU en policy gradient)
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
        )
        # Cabeza ACTOR: media de la accion (en espacio normalizado, via tanh)
        self.mean_head = nn.Linear(hidden, action_dim)
        # Cabeza CRITICO: valor escalar del estado V(s)
        self.value_head = nn.Linear(hidden, 1)
        # log(std) aprendible e independiente del estado (estable y simple)
        self.log_std_head = nn.Linear(hidden, action_dim) 

        # Inicializacion ortogonal (buena practica en RL)
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=1.0)
                nn.init.constant_(m.bias, 0.0)

    def forward(self, state):
        feat = self.trunk(state)
        mean = torch.tanh(self.mean_head(feat))
        log_std = self.log_std_head(feat).clamp(-2.0, 0.5)   
        std = torch.exp(log_std)
        value = self.value_head(feat).squeeze(-1)
        dist = Normal(mean, std)
        return dist, value

    def scale_action(self, norm_action):
        """Convierte accion normalizada [-1,1]^2 -> (v, w) reales."""
        a = norm_action.clamp(-1.0, 1.0)
        v = (a[..., 0] + 1.0) * 0.5 * self.v_max         # [0, v_max] (adelante)
        w = a[..., 1] * self.w_max                       # [-w_max, w_max]
        return torch.stack([v, w], dim=-1)

    @torch.no_grad()
    def act(self, state):
        """Muestrea una accion para interactuar con el entorno."""
        dist, value = self.forward(state)
        norm_action = dist.sample()                      # accion normalizada
        logp = dist.log_prob(norm_action).sum(-1)        # log-prob (suma de dims)
        exec_action = self.scale_action(norm_action)     # (v, w) para el robot
        return norm_action, exec_action, logp, value

    def evaluate(self, states, norm_actions):
        """Re-evalua acciones para calcular las losses durante el update."""
        dist, values = self.forward(states)
        logp = dist.log_prob(norm_actions).sum(-1)
        entropy = dist.entropy().sum(-1)
        return logp, values, entropy
