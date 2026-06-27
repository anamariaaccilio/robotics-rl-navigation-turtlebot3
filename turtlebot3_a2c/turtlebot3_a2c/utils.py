"""
utils.py
Utilidades: normalizador de estado (RunningMeanStd) y calculo de ventajas (GAE).
"""
import numpy as np


class RunningMeanStd:
    """
    Mantiene media y varianza online del estado (algoritmo de Welford por lotes).
    Normalizar el estado estabiliza mucho el aprendizaje en control continuo.
    """
    def __init__(self, shape, eps=1e-4):
        self.mean = np.zeros(shape, dtype=np.float64)
        self.var = np.ones(shape, dtype=np.float64)
        self.count = eps

    def update(self, x):
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x[None, :]
        batch_mean = x.mean(axis=0)
        batch_var = x.var(axis=0)
        batch_count = x.shape[0]

        delta = batch_mean - self.mean
        tot = self.count + batch_count
        self.mean += delta * batch_count / tot
        m_a = self.var * self.count
        m_b = batch_var * batch_count
        M2 = m_a + m_b + delta ** 2 * self.count * batch_count / tot
        self.var = M2 / tot
        self.count = tot

    def normalize(self, x):
        return (np.asarray(x, dtype=np.float64) - self.mean) / np.sqrt(self.var + 1e-8)


def compute_gae(rewards, values, dones, last_value, gamma, lam):
    """
    Generalized Advantage Estimation (GAE).
    Combina todos los estimadores n-step con peso lambda (tu lamina de GAE).
      - lam=0  -> TD de 1 paso (A2C base)
      - lam=1  -> Monte Carlo (REINFORCE)
    Devuelve (ventajas, retornos).
    """
    T = len(rewards)
    adv = np.zeros(T, dtype=np.float32)
    gae = 0.0
    for t in reversed(range(T)):
        next_value = last_value if t == T - 1 else values[t + 1]
        next_nonterminal = 1.0 - dones[t]      # 0 si el paso fue terminal
        delta = rewards[t] + gamma * next_value * next_nonterminal - values[t]
        gae = delta + gamma * lam * next_nonterminal * gae
        adv[t] = gae
    returns = adv + np.asarray(values, dtype=np.float32)
    return adv, returns
