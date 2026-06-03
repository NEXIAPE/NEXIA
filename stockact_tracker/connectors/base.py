"""
connectors/base.py
==================

Define el CONTRATO que todo conector debe cumplir. Piensa en esto como un
"molde": cualquier fuente nueva (la Cámara, el Senado, un agregador...) se
construye sobre este molde y, por eso, el resto del programa puede usarla
sin saber sus detalles internos.

Conceptos para principiantes:
  - Una "clase base abstracta" (ABC) es un molde que NO se usa directo: se
    hereda. Obliga a las clases hijas a implementar ciertos métodos.
  - El método obligatorio aquí es `fetch()`: devuelve una lista de objetos
    `Disclosure` (el formato común definido en models.py).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import config
from models import Disclosure


class BaseConnector(ABC):
    """Molde común para todas las fuentes de datos."""

    # Identificador corto y único del conector, ej. "house".
    # Debe coincidir con la clave usada en config.CONNECTORS.
    name: str = "base"

    # Nombre legible para los informes/logs.
    label: str = "Conector base"

    def __init__(self, settings: dict):
        # `settings` es el sub-diccionario de config.CONNECTORS[self.name].
        self.settings = settings

    @property
    def enabled(self) -> bool:
        """¿Está encendido este conector en config.py?"""
        return bool(self.settings.get("enabled", False))

    @abstractmethod
    def fetch(self, since: Optional[datetime] = None) -> List[Disclosure]:
        """
        Obtiene divulgaciones de la fuente y las devuelve en formato común.

        Parámetros:
          since: si se entrega, el conector DEBERÍA devolver solo lo presentado
                 a partir de esa fecha (para no reprocesar todo cada vez).
                 Si es None, devuelve lo que pueda (primera corrida).

        Debe devolver: una lista de objetos `Disclosure` (puede estar vacía).
        Nunca debe lanzar excepciones por datos faltantes: ante un problema,
        registra una advertencia y devuelve lo que haya podido recolectar.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Utilidad compartida: dormir entre peticiones (rate limiting).
    # La usan los conectores que hacen red. Está aquí para no repetirla.
    # ------------------------------------------------------------------
    @staticmethod
    def polite_sleep() -> None:
        """Espera el tiempo configurado para no saturar a la fuente."""
        time.sleep(config.REQUEST_DELAY_SECONDS)
