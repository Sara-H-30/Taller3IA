"""Resultados y tablass para la terminal."""


def number(value):
    return 'Sin estimación' if value is None else f'{value:.6f}'


def table(headers, rows):
    rows = [list(map(str, row)) for row in rows]
    widths = [max([len(h), *[len(row[i]) for row in rows]]) for i, h in enumerate(headers)]
    print(' | '.join(h.ljust(w) for h, w in zip(headers, widths)))
    print('-+-'.join('-' * w for w in widths))
    for row in rows:
        print(' | '.join(v.ljust(w) for v, w in zip(row, widths)))


def display(report, model):
    print(f'\nAlerta Bosque | Punto {report["point"]} | {model.name}')
    if report['point'] <= 3:
        display_bayes(report, model)
    else:
        display_mdp(report, model)


def display_bayes(r, model):
    evidence = ', '.join(f'{x}={v}' for x, v in r['evidence'].items()) or 'ninguna'
    methods = {'enumeration': 'Enumeración', 'elimination': 'Eliminación de variables',
               'prior': 'Muestreo a priori', 'rejection': 'Muestreo por rechazo'}
    print(f'Consulta: {r["query"]} | Evidencia: {evidence}')
    print(f'Método: {methods.get(r["method"], r["method"])}')
    if len(r['repetitions']) > 1:
        print('Distribución final de la última ejecución:')
    headers = ['Resultado', 'Probabilidad'] + (['Referencia exacta'] if 'exact' in r else [])
    table(headers, [(f'{r["query"]}={v}', number(r['distribution'][v] if r['distribution'] else None),
                     *([number(r['exact'][v])] if 'exact' in r else [])) for v in (0, 1)])
    if r['method'] in ('prior', 'rejection'):
        table(['Ejecución', 'Semilla', 'Intentos', 'Aceptadas', 'Estimación P(1)', 'Error absoluto'],
              [(i, row['seed'], row['generated'], row['accepted'], number(row['p1']),
                number(row['absolute_error'])) for i, row in enumerate(r['repetitions'], 1)])
    if r.get('action'):
        print('\nUtilidad esperada por acción:')
        table(['Acción', 'Utilidad esperada'], [(a, number(v)) for a, v in r['utilities'].items()])
        print(f'Acción elegida: {r["action"]} | Utilidad esperada: {number(r["utilities"][r["action"]])}')
    if r['message']:
        print(r['message'])
    if r['point'] == 1:
        print('\nDistribución conjunta:')
        table([*model.variables, 'Probabilidad', 'Compatible con evidencia'],
              [(*[row['event'][v] for v in model.variables], number(row['probability']),
                'Sí' if all(row['event'][x] == v for x, v in r['evidence'].items()) else 'No')
               for row in r['joint_table']])
    if r['method'] == 'elimination':
        for i, step in enumerate(r['history'], 1):
            print(f'\nPaso {i}: eliminar {step["eliminated"]} | Producto: {step["product_rows"]} filas')
            table([*step['variables'], 'Factor resultante'],
                  [(*row['values'], number(row['p'])) for row in step['table']])
    if r['point'] in (1, 2):
        print('\nEstructura y probabilidades locales:')
        for node in model.nodes:
            print(f'\n{node["name"]} | Padres: {", ".join(node["parents"]) or "ninguno"}')
            table([*node['parents'], 'P(0)', 'P(1)'],
                  [(*bits, number(1-p), number(p)) for bits, p in node['cpt'].items()])


def display_mdp(r, model):
    print(f'Ruido={model.noise} | Recompensa por movimiento={model.living_reward} | Descuento={model.discount}')
    print(f'Barridos={r["iterations"]} | Convergió: {"Sí" if r["converged"] else "No"} | V(inicio)={number(r["start_value"])}')
    start_key = f'{model.start[0]},{model.start[1]}'
    if r['policy']:
        print(f'Acción de la política en el inicio: {r["policy"][start_key]}')
    print('\nValores finales' + (' y política:' if r['policy'] else ':'))
    print('Inicio: estado inicial | R: riesgo | T: terminal (V=0) | #: muro')
    print('N/E/S/W: dirección de la política')
    rows = []
    for y in range(model.height):
        cells = []
        for x in range(model.width):
            s, key = (x, y), f'{x},{y}'
            if s not in model.state_set:
                cells.append('#')
                continue
            label = 'Inicio ' if s == model.start else ''
            if s in model.terminals:
                label += f'T(R={model.terminals[s]:g}) '
            elif model.cell(s) == 'R':
                label += 'R '
            action = (r['policy'] or {}).get(key) or ''
            cells.append(f'{label}{r["values"][key]:.3f} {action}'.strip())
        rows.append([y, *cells])
    table(['y / x', *map(str, range(model.width))], rows)
    print('\nValores de las acciones en el inicio:')
    table(['Acción', 'Q(inicio, acción)'], [(a, number(v)) for a, v in r['start_q'].items()])
    if r['point'] == 4:
        total = len(r['deltas'])
        indices = sorted(set(range(min(3, total))) | set(range(max(0, total-3), total)))
        print('\nConvergencia: primeros tres y últimos tres barridos (sin repetir).')
        table(['Barrido', 'Cambio máximo', 'V(inicio)'],
              [(i+1, f'{r["deltas"][i]:.6g}', number(r['history'][i+1][start_key])) for i in indices])
    if r.get('trajectory'):
        t = r['trajectory']
        print('\nTrayectoria de ejemplo; no es la política completa:')
        table(['Paso', 'Estado (x, y)', 'Recompensa al llegar'],
              [(i, f'({s[0]}, {s[1]})', '-' if i == 0 else number(t['rewards'][i-1])) for i, s in enumerate(t['path'])])
        print(f'Llegó a un terminal: {"Sí" if t["finished"] else "No"} | Retorno descontado: {number(t["return"])}')
