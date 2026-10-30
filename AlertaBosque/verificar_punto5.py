"""Pruebas reproducibles del punto 5 y del soporte de Bellman, sin dependencias."""
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from algorithms.planning import action_value, extract_policy, value_iteration
from models.mdp import GridMDP


ROOT = Path(__file__).resolve().parent


def load(name, **kwargs):
    return GridMDP.load(ROOT / 'layouts' / 'mdp' / f'{name}.json', **kwargs)


def evaluate_policy(mdp, policy):
    """Control independiente: resuelve (I - gamma P_pi) V_pi = r_pi.

    Eliminación de Gauss con pivoteo, sin invocar action_value ni value_iteration.
    """
    states = [s for s in mdp.states if s not in mdp.terminals]
    index = {s: i for i, s in enumerate(states)}
    size = len(states)
    matrix = [[float(i == j) for j in range(size)] + [0.0] for i in range(size)]
    for state, i in index.items():
        action = policy[state]
        for successor, probability in mdp.transitions(state, action):
            matrix[i][-1] += probability * mdp.reward(state, action, successor)
            if successor in index:
                matrix[i][index[successor]] -= mdp.discount * probability
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(matrix[row][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = matrix[col][col]
        if abs(scale) < 1e-14:
            raise ArithmeticError('Sistema de evaluación singular')
        matrix[col] = [entry / scale for entry in matrix[col]]
        for row in range(size):
            if row != col:
                factor = matrix[row][col]
                matrix[row] = [a - factor * b for a, b in zip(matrix[row], matrix[col])]
    return {s: matrix[index[s]][-1] if s in index else 0.0 for s in mdp.states}


class Punto5Tests(unittest.TestCase):
    def test_control_terminal_reward_once(self):
        mdp = load('control')
        result = value_iteration(mdp)
        self.assertEqual(result.values, {(0, 0): 1.0, (1, 0): 0.0})
        self.assertEqual(extract_policy(mdp, result.values), {(0, 0): 'E', (1, 0): None})
        self.assertEqual(result.deltas, [1.0, 0.0])
        self.assertTrue(result.converged)

    def test_q_with_noise_and_rebound_by_hand(self):
        mdp = load('cuadricula')
        values = dict.fromkeys(mdp.states, 0.0)
        values.update({(0, 1): 2.0, (1, 2): 3.0, (0, 2): 4.0})
        # N desde S: 0.8 al norte, 0.1 al este, 0.1 rebota al oeste.
        expected = 0.8 * (-0.04 + 0.9 * 2) + 0.1 * (-0.04 + 0.9 * 3) + 0.1 * (-0.04 + 0.9 * 4)
        self.assertAlmostEqual(action_value(mdp, mdp.start, 'N', values), expected)
        self.assertAlmostEqual(expected, 2.03)

    def test_synchronous_sweeps_and_history(self):
        mdp = GridMDP({'name': 'cadena', 'description': '', 'grid': ['S.G'],
                       'noise': 0, 'living_reward': -0.04, 'discount': 0.9,
                       'terminal_rewards': {'G': 1}})
        result = value_iteration(mdp, max_iterations=2)
        self.assertEqual(result.history[0], {(0, 0): 0.0, (1, 0): 0.0, (2, 0): 0.0})
        self.assertEqual(result.history[1], {(0, 0): -0.04, (1, 0): 1.0, (2, 0): 0.0})
        self.assertAlmostEqual(result.values[(0, 0)], 0.86)
        self.assertFalse(result.converged)
        result.values[(0, 0)] = 999
        self.assertAlmostEqual(result.history[-1][(0, 0)], 0.86)

    def test_exact_tie_keeps_first_and_terminal_is_not_evaluated(self):
        mdp = load('control')
        with patch('algorithms.planning.action_value', return_value=-2.0) as q:
            policy = extract_policy(mdp, dict.fromkeys(mdp.states, 0.0))
        self.assertEqual(policy[mdp.start], 'N')
        self.assertIsNone(policy[(1, 0)])
        self.assertEqual([call.args[2] for call in q.call_args_list], ['N', 'E', 'S', 'W'])
        self.assertTrue(all(call.args[1] == mdp.start for call in q.call_args_list))

    def test_near_tie_is_not_rounded(self):
        mdp = load('control')
        scores = {'N': 1.0, 'E': 1.0 + 1e-12, 'S': 0.0, 'W': 0.0}
        with patch('algorithms.planning.action_value', side_effect=lambda m, s, a, v: scores[a]):
            self.assertEqual(extract_policy(mdp, {})[mdp.start], 'E')

    def test_respects_available_actions(self):
        mdp = load('control')
        with patch.object(mdp, 'actions', side_effect=lambda s: ('S', 'W') if s == mdp.start else ()):
            with patch('algorithms.planning.action_value', return_value=-3.0):
                self.assertEqual(extract_policy(mdp, {})[mdp.start], 'S')

    def test_does_not_mutate_inputs(self):
        mdp = load('zona_riesgo')
        values = value_iteration(mdp).values
        before_values, before_model = values.copy(), deepcopy(mdp.__dict__)
        policy = extract_policy(mdp, values)
        self.assertEqual(values, before_values)
        self.assertEqual(mdp.__dict__, before_model)
        self.assertEqual(set(policy), set(mdp.states))

    def test_risk_penalty_including_rebound(self):
        mdp = GridMDP({'name': 'riesgo', 'description': '', 'grid': ['SRG'],
                       'noise': 0, 'living_reward': -0.04, 'discount': 0.95,
                       'risk_penalty': -0.4, 'terminal_rewards': {'G': 2}})
        values = dict.fromkeys(mdp.states, 0.0)
        self.assertAlmostEqual(action_value(mdp, (1, 0), 'N', values), -0.44)
        self.assertEqual(action_value(mdp, (1, 0), 'E', values), 2.0)

    def test_policy_is_optimal_under_independent_evaluation(self):
        cases = [('control', {}), ('cuadricula', {}), ('atajo', {'noise': 0}),
                 ('atajo', {'noise': 0.3}), ('zona_riesgo', {}),
                 ('zona_riesgo', {'living_reward': -0.30}),
                 ('zona_riesgo', {'discount': 0.50})]
        for name, options in cases:
            with self.subTest(layout=name, **options):
                mdp = load(name, **options)
                result = value_iteration(mdp)
                self.assertTrue(result.converged)
                self.assertLess(result.deltas[-1], 1e-8)
                policy = extract_policy(mdp, result.values)
                exact = evaluate_policy(mdp, policy)
                self.assertLess(max(abs(exact[s] - result.values[s]) for s in mdp.states), 2e-7)
                for state in mdp.states:
                    if state in mdp.terminals:
                        self.assertIsNone(policy[state])
                        self.assertEqual(result.values[state], 0.0)
                        continue
                    # Bellman óptimo sobre V_pi calculado por un método independiente.
                    alternatives = [sum(p * (mdp.reward(state, a, nxt) + mdp.discount * exact[nxt])
                                        for nxt, p in mdp.transitions(state, a)) for a in mdp.actions(state)]
                    self.assertAlmostEqual(exact[state], max(alternatives), delta=1e-7)

    def test_noise_changes_start_decision(self):
        policies = []
        for noise in (0.0, 0.3):
            mdp = load('atajo', noise=noise)
            policies.append(extract_policy(mdp, value_iteration(mdp).values)[mdp.start])
        self.assertEqual(policies, ['E', 'N'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
