"""Ejecución: escenarios, resultados e historiales."""
from pathlib import Path
import random
from algorithms.probability import normalize, best_action
from algorithms.inference import enumeration_ask
from algorithms.sampling import sampling_ask
from algorithms.planning import value_iteration, extract_policy, action_value
from models.bayes import BayesianNetwork, basic_distribution
from models.elimination import variable_elimination
from models.mdp import GridMDP, simulate

ROOT = Path(__file__).resolve().parent


def run(args):
    if args.point <= 3:
        path = ROOT / 'layouts' / 'bayes' / f'{args.layout}.json'
        network = BayesianNetwork.load(path)
        if args.case not in network.cases:
            raise ValueError(f'Caso desconocido. Opciones: {", ".join(network.cases)}')
        evidence = dict(network.cases[args.case])
        if args.evidence is not None:
            evidence = {}
            for item in filter(None, args.evidence.split(',')):
                key, value = item.split('=')
                evidence[key.strip()] = int(value)
        network.validate_query(args.query, evidence)
        # Control exacto para comparar los métodos del punto 3.
        exact = enumeration_ask(network, args.query, evidence) if args.point == 3 else None
        distribution = None
        history, message = [], ''
        repetitions = []
        order = None
        if args.order == 'reverse':
            order = list(reversed([x for x in network.variables if x != args.query and x not in evidence]))
        elif args.order != 'forward':
            order = args.order.split(',')
        for repetition in range(args.repeat):
            if args.point == 1:
                distribution = normalize(basic_distribution(network, args.query, evidence))
                method = 'tabla conjunta'
            elif args.point == 2:
                distribution = enumeration_ask(network, args.query, evidence)
                method = 'enumeration'
            elif args.method == 'elimination':
                result = variable_elimination(network, args.query, evidence, order)
                distribution, history, message = result.distribution, result.history, result.message
                method = 'elimination'
            else:
                distribution, accepted = sampling_ask(network, args.query, evidence, args.samples,
                                      random.Random(args.seed + repetition), args.method == 'rejection')
                message = '' if accepted else 'Sin muestras aceptadas; aumente los intentos.'
                method = args.method
            estimate = distribution[1] if distribution else None
            row = {'p1': estimate}
            if method in ('prior', 'rejection'):
                row.update(seed=args.seed + repetition,
                           generated=args.samples, accepted=accepted)
            if exact is not None:
                row['absolute_error'] = abs(estimate-exact[1]) if estimate is not None else None
            repetitions.append(row)
        report = {'point': args.point, 'scenario': args.layout, 'method': method,
                  'query': args.query, 'evidence': evidence,
                  'distribution': distribution, 'repetitions': repetitions,
                  'history': history, 'message': message}
        if exact is not None:
            report['exact'] = exact
        if args.point == 1 and args.query == 'Incendio' and distribution:
            utilities = {a: {int(k): v for k, v in table.items()} for a, table in network.utilities.items()}
            chosen, values = best_action(distribution, utilities)
            report.update(action=chosen, utilities=values)
        if args.point == 1:
            report['joint_table'] = network.joint_table()
        return report, network
    mdp = GridMDP.load(ROOT / 'layouts' / 'mdp' / f'{args.layout}.json',
                       noise=args.noise, living_reward=args.living_reward, discount=args.discount)
    result = value_iteration(mdp, args.tolerance, args.iterations)
    policy = extract_policy(mdp, result.values) if args.point == 5 else None
    report = {'point': args.point, 'scenario': args.layout, 'noise': mdp.noise,
              'living_reward': mdp.living_reward, 'discount': mdp.discount,
              'iterations': len(result.deltas), 'converged': result.converged,
              'tolerance': args.tolerance,
              'start_value': result.values[mdp.start], 'deltas': result.deltas,
              'values': {f'{x},{y}': v for (x, y), v in result.values.items()},
              'history': [{f'{x},{y}': v for (x, y), v in values.items()} for values in result.history],
              'policy': {f'{x},{y}': a for (x, y), a in policy.items()} if policy else None,
              'start_q': {a: action_value(mdp, mdp.start, a, result.values) for a in mdp.actions(mdp.start)}}
    if policy:
        report['trajectory'] = simulate(mdp, policy, random.Random(args.seed), args.max_steps)
    return report, mdp
