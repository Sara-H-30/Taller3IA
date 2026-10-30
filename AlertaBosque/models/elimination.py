"""Eliminación de variables. No es implementación del estudiante.

Cada fila de la traza registra la variable eliminada, el alcance y la tabla
del factor resultante.
"""
from dataclasses import dataclass
from itertools import product
from algorithms.probability import normalize


@dataclass
class EliminationResult:
    distribution: dict
    history: list
    message: str


@dataclass
class Factor:
    variables: tuple
    table: dict

    def value(self, event):
        return self.table[tuple(event[x] for x in self.variables)]


def variable_elimination(network, query, evidence, order=None):
    network.validate_query(query, evidence)
    hidden = [x for x in network.variables if x != query and x not in evidence]
    order = hidden if order is None else list(order)
    if len(order) != len(hidden) or set(order) != set(hidden):
        raise ValueError('El orden debe contener cada variable oculta exactamente una vez')
    factors = []
    peak = 0
    trace = []
    for node in network.nodes:
        variables = tuple(x for x in node['parents'] + [node['name']] if x not in evidence)
        table = {}
        for values in product((0, 1), repeat=len(variables)):
            event = {**evidence, **dict(zip(variables, values))}
            table[values] = network.probability(node['name'], event[node['name']], event)
        factors.append(Factor(variables, table))

    def multiply(group):
        nonlocal peak
        variables = tuple(x for x in network.variables if any(x in f.variables for f in group))
        table = {}
        for values in product((0, 1), repeat=len(variables)):
            event = dict(zip(variables, values))
            value = 1.0
            for f in group:
                value *= f.value(event)
            table[values] = value
        peak = max(peak, len(table))
        return Factor(variables, table)

    for variable in order:
        group = [f for f in factors if variable in f.variables]
        joint = multiply(group)
        remaining = tuple(x for x in joint.variables if x != variable)
        table = {}
        for values in product((0, 1), repeat=len(remaining)):
            event = dict(zip(remaining, values))
            table[values] = sum(joint.value({**event, variable: v}) for v in (0, 1))
        factors = [f for f in factors if f not in group] + [Factor(remaining, table)]
        trace.append({'eliminated': variable, 'variables': list(remaining),
                      'table': [{'values': list(k), 'p': v} for k, v in table.items()],
                      'product_rows': len(joint.table)})
    final = multiply(factors)
    weights = {v: (0.0 if query in evidence and evidence[query] != v
                   else final.value({query: v})) for v in (0, 1)}
    return EliminationResult(normalize(weights), trace, f'Máximo factor producto: {peak} filas')
