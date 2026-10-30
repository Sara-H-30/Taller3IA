"""Punto 3. Muestreo a priori y su extensión por rechazo."""
import random
from algorithms.probability import normalize


def prior_sample(network, rng: random.Random) -> dict:
    """Genera un mundo completo, muestreando padres antes que hijos.

    Entradas: network es la red y rng el generador aleatorio.
    Salida: un diccionario {nombre de variable: 0 o 1} con todos los nodos.

    Tips:
    - Use exclusivamente rng.random(); X=1 si r < P(X=1 | padres).
    - No fije evidencia aquí: esta función genera muestras a priori.
    - network.variables ya está en orden topológico. Consulte la CPT con
      network.probability(variable, 1, event), usando el evento parcial.
    """
    # TODO: Add your code here
    raise NotImplementedError("Complete este bloque TODO")
    # FIN DEL BLOQUE DEL ESTUDIANTE


def sampling_ask(network, query, evidence, samples, rng, reject=False):
    """Estima una marginal o una condicional, usando exactamente samples intentos.

    Entradas: query es un nombre de variable; evidence es {variable: 0 o 1};
    samples es el número de intentos; rng es el generador aleatorio;
    reject indica si se descartan muestras incompatibles con la evidencia.
    Salida: (distribución estimada, número de muestras aceptadas).
    Use (None, 0) si ninguna muestra es compatible con la evidencia.

    Tips:
    - Reutilice prior_sample. Sin rechazo solo se permite evidence vacío.
    - Con rechazo cuente únicamente mundos compatibles con toda la evidencia.
    - Normalice los conteos aceptados, no divida entre intentos totales.
    - Si no acepta muestras, distribution=None; no invente ceros ni uniformes.
    """
    # Validación de las entradas; no modificar.
    network.validate_query(query, evidence)
    if samples < 1:
        raise ValueError("El número de muestras debe ser positivo")
    if evidence and not reject:
        raise ValueError("Muestreo a priori estima marginales; use rechazo con evidencia")
    # TODO: Add your code here
    raise NotImplementedError("Complete este bloque TODO")
    # FIN DEL BLOQUE DEL ESTUDIANTE
