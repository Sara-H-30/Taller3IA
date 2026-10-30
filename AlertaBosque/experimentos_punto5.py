"""Reproduce las comparaciones del punto 5 y guarda datos completos en JSON."""
import json
from pathlib import Path

from algorithms.planning import action_value
from main import parser
from runner import run


CASES = [
    ('atajo_ruido_0', '-l atajo --noise 0 --living-reward -0.04 --discount 0.95'),
    ('atajo_ruido_03', '-l atajo --noise 0.3 --living-reward -0.04 --discount 0.95'),
    ('riesgo_base', '-l zona_riesgo --noise 0.1 --living-reward -0.04 --discount 0.95'),
    ('riesgo_paso_030', '-l zona_riesgo --noise 0.1 --living-reward -0.30 --discount 0.95'),
    ('riesgo_descuento_050', '-l zona_riesgo --noise 0.1 --living-reward -0.04 --discount 0.50'),
]


def main():
    results = {}
    for name, options in CASES:
        arguments = f'-p 5 {options} --tolerance 1e-8 --iterations 1000 --seed 7 -t'
        report, mdp = run(parser().parse_args(arguments.split()))
        values = {tuple(map(int, key.split(','))): value for key, value in report['values'].items()}
        report['command'] = f'python main.py {arguments}'
        report['grid'] = mdp.grid
        report['last_delta'] = report['deltas'][-1]
        report['q_values'] = {
            f'{s[0]},{s[1]}': {a: action_value(mdp, s, a, values) for a in mdp.actions(s)}
            for s in mdp.states
        }
        report['bellman_residual'] = max(
            abs(values[s] - max(report['q_values'][f'{s[0]},{s[1]}'].values(), default=0.0))
            for s in mdp.states
        )
        report.pop('history')
        results[name] = report
        key = f'{mdp.start[0]},{mdp.start[1]}'
        print(f'{name}: V(S)={report["start_value"]:.9f}; accion={report["policy"][key]}; '
              f'barridos={report["iterations"]}; convergio={report["converged"]}')
    for left, right in [('atajo_ruido_0', 'atajo_ruido_03'),
                        ('riesgo_base', 'riesgo_paso_030'),
                        ('riesgo_base', 'riesgo_descuento_050')]:
        changes = [s for s, a in results[left]['policy'].items() if a != results[right]['policy'][s]]
        print(f'{left} -> {right}: {len(changes)} decisiones diferentes; estados={changes}')
    destination = Path(__file__).resolve().parent / 'documentacion' / 'resultados_punto5.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Datos completos: {destination}')


if __name__ == '__main__':
    main()
