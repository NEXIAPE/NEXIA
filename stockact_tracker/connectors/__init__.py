"""
connectors/__init__.py
======================

El "REGISTRO" de conectores. Aquí se listan TODAS las fuentes posibles.
Encender/apagar cada una se hace en config.py (no aquí).

Cómo agregar una fuente nueva en el futuro (3 pasos):
  1) Crea un archivo connectors/mi_fuente.py con una clase que herede de
     BaseConnector e implemente fetch().
  2) Impórtala aquí y añádela a la lista ALL_CONNECTOR_CLASSES.
  3) Añade su configuración (con "enabled") en config.CONNECTORS.
¡Y listo! El resto del programa la tomará automáticamente.
"""

from __future__ import annotations

from typing import List

import config
from connectors.base import BaseConnector
from connectors.house_clerk import HouseClerkConnector
from connectors.senate_efd import SenateEFDConnector
from connectors.external_aggregator import ExternalAggregatorConnector

# Todas las clases de conector que existen (activas o no).
ALL_CONNECTOR_CLASSES = [
    HouseClerkConnector,
    SenateEFDConnector,
    ExternalAggregatorConnector,
]


def get_enabled_connectors() -> List[BaseConnector]:
    """
    Devuelve una lista con UNA instancia de cada conector ENCENDIDO en config.

    El orquestador (main.py) usa esto: no necesita saber qué fuentes existen,
    solo pide "las que estén activas".
    """
    activos: List[BaseConnector] = []
    for clase in ALL_CONNECTOR_CLASSES:
        settings = config.CONNECTORS.get(clase.name, {})
        instancia = clase(settings)
        if instancia.enabled:
            activos.append(instancia)
    return activos
