"""MDP. Recompensa al entrar al terminal, valor terminal cero."""
import json
import math
from pathlib import Path

ACTIONS = ('N', 'E', 'S', 'W')
DELTAS = {'N': (0, -1), 'E': (1, 0), 'S': (0, 1), 'W': (-1, 0)}


class GridMDP:
    def __init__(self, data, noise=None, living_reward=None, discount=None):
        self.name = data['name']
        self.description = data['description']
        self.grid = data['grid']
        self.noise = data['noise'] if noise is None else noise
        self.living_reward = data['living_reward'] if living_reward is None else living_reward
        self.discount = data['discount'] if discount is None else discount
        if not 0 <= self.noise <= 1 or not 0 <= self.discount < 1:
            raise ValueError('Se requiere 0 <= ruido <= 1 y 0 <= descuento < 1')
        if not math.isfinite(self.living_reward):
            raise ValueError('Recompensa por movimiento no finita')
        self.height, self.width = len(self.grid), len(self.grid[0])
        if not self.width or any(len(row) != self.width for row in self.grid):
            raise ValueError('La cuadrícula debe ser rectangular')
        if any(c not in '#.SGXR' for row in self.grid for c in row):
            raise ValueError('Símbolo de mapa desconocido')
        self.states = [(x, y) for y, row in enumerate(self.grid) for x, c in enumerate(row) if c != '#']
        self.state_set = set(self.states)
        starts = [s for s in self.states if self.cell(s) == 'S']
        if len(starts) != 1:
            raise ValueError('Debe existir un único inicio S')
        self.start = starts[0]
        self.terminals = {s: data['terminal_rewards'][self.cell(s)] for s in self.states if self.cell(s) in 'GX'}
        self.risk_penalty = data.get('risk_penalty', -0.4)
        if not self.terminals or not all(math.isfinite(v) for v in [*self.terminals.values(), self.risk_penalty]):
            raise ValueError('Se requieren recompensas terminales y de riesgo finitas')

    @classmethod
    def load(cls, path: Path, **kwargs):
        return cls(json.loads(path.read_text(encoding='utf-8')), **kwargs)

    def cell(self, state):
        x, y = state
        return self.grid[y][x]

    def actions(self, state):
        return () if state in self.terminals else ACTIONS

    def transitions(self, state, action):
        """Lista (sucesor, probabilidad). Desvío total noise dividido a ambos lados."""
        if state in self.terminals:
            return [(state, 1.0)]
        if action not in ACTIONS:
            raise ValueError('Acción desconocida')
        i = ACTIONS.index(action)
        options = [(action, 1-self.noise), (ACTIONS[(i-1) % 4], self.noise/2),
                   (ACTIONS[(i+1) % 4], self.noise/2)]
        result = {}
        for direction, p in options:
            dx, dy = DELTAS[direction]
            candidate = state[0]+dx, state[1]+dy
            target = candidate if candidate in self.state_set else state
            if p > 0:
                result[target] = result.get(target, 0) + p
        return list(result.items())

    def reward(self, state, action, successor):
        if state in self.terminals:
            return 0.0
        if successor in self.terminals:
            return self.terminals[successor]
        return self.living_reward + (self.risk_penalty if self.cell(successor) == 'R' else 0)


def simulate(mdp, policy, rng, max_steps=100):
    """Una trayectoria ilustrativa; usa RNG independiente al de inferencia."""
    state = mdp.start
    path = [state]
    rewards = []
    for _ in range(max_steps):
        if state in mdp.terminals:
            break
        action = policy[state]
        transitions = mdp.transitions(state, action)
        successors, weights = zip(*transitions)
        successor = rng.choices(successors, weights=weights)[0]
        rewards.append(mdp.reward(state, action, successor))
        state = successor
        path.append(state)
    return {'path': path, 'rewards': rewards,
            'return': sum(mdp.discount**i * r for i, r in enumerate(rewards)),
            'finished': state in mdp.terminals}
