"""Redes binarias con CPT explícitas. Infraestructura."""
import itertools
import json
import math
from pathlib import Path


class BayesianNetwork:
    def __init__(self, data: dict):
        self.name = data['name']
        self.description = data['description']
        self.nodes = data['nodes']
        self.variables = [node['name'] for node in self.nodes]
        self.by_name = {node['name']: node for node in self.nodes}
        self.cases = data['cases']
        self.utilities = data['utilities']
        seen = set()
        for node in self.nodes:
            name, parents = node['name'], node['parents']
            if name in seen or not set(parents) <= seen or len(set(parents)) != len(parents):
                raise ValueError("Variables duplicadas o padres fuera de orden topológico")
            keys = {''.join(map(str, values)) for values in itertools.product((0, 1), repeat=len(parents))}
            if set(node['cpt']) != keys:
                raise ValueError(f"CPT incompleta: {name}")
            if any(not math.isfinite(p) or not 0 <= p <= 1 for p in node['cpt'].values()):
                raise ValueError(f"Probabilidad inválida: {name}")
            seen.add(name)

    @classmethod
    def load(cls, path: Path):
        return cls(json.loads(path.read_text(encoding='utf-8')))

    def probability(self, variable: str, value: int, event: dict) -> float:
        """P(variable=value | padres). CPT almacena P(variable=1)."""
        if value not in (0, 1):
            raise ValueError("Dominio binario: 0 o 1")
        node = self.by_name[variable]
        key = ''.join(str(event[p]) for p in node['parents'])
        p = node['cpt'][key]
        return p if value == 1 else 1 - p

    def validate_query(self, query: str, evidence: dict):
        if query not in self.variables or not set(evidence) <= set(self.variables):
            raise ValueError("Variable desconocida")
        if any(v not in (0, 1) for v in evidence.values()):
            raise ValueError("La evidencia debe usar 0 o 1")

    def joint_table(self) -> list[dict]:
        """Tabla pequeña para controles manuales, no usada por enumeración."""
        rows = []
        for values in itertools.product((0, 1), repeat=len(self.variables)):
            event = dict(zip(self.variables, values))
            p = math.prod(self.probability(x, event[x], event) for x in self.variables)
            rows.append({'event': event, 'probability': p})
        return rows


def basic_distribution(network, query, evidence):
    """Filtra y suma la tabla conjunta; pesos sin normalizar para el punto 1."""
    network.validate_query(query, evidence)
    weights = {0: 0.0, 1: 0.0}
    for row in network.joint_table():
        if all(row['event'][x] == v for x, v in evidence.items()):
            weights[row['event'][query]] += row['probability']
    return weights
