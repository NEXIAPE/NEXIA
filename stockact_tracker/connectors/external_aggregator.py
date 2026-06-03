"""
connectors/external_aggregator.py
=================================

Hueco / PLANTILLA para un AGREGADOR EXTERNO de datos de la STOCK Act.
⛔ DESACTIVADO EN LA v1. Es deliberadamente un esqueleto vacío.

¿Qué es un "agregador"? Un servicio (a veces con API) que ya recopiló y
limpió los datos de la Cámara y el Senado por ti. Pueden ahorrarte el trabajo
de parsear PDFs, pero:
  - Suelen requerir API key y tienen rate limits / cuotas.
  - Cada uno tiene SUS PROPIOS términos de uso y, a veces, costo.
  - Algunos prohíben la redistribución de sus datos. LÉELOS antes de usarlos.

DECISIÓN PENDIENTE (a propósito): no fijamos un proveedor concreto para que
elijas el que cumpla tus términos y presupuesto. Cuando elijas uno:
  1) Pon  "aggregator": {"enabled": True, "api_key": "TU_CLAVE"}  en config.py.
  2) Implementa la llamada a su API en fetch() (ver TODO).
  3) Mapea su respuesta JSON al formato común `Disclosure`.
  4) Respeta su rate limit con self.polite_sleep() y su licencia de datos.

Mientras 'enabled' sea False, este conector NO se usa y devuelve [].
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from connectors.base import BaseConnector
from models import Disclosure


class ExternalAggregatorConnector(BaseConnector):
    name = "aggregator"
    label = "Agregador externo (plantilla)"

    def fetch(self, since: Optional[datetime] = None) -> List[Disclosure]:
        print(f"⏭️  [{self.label}] DESACTIVADO. Es un hueco listo para que "
              f"conectes el agregador que elijas (ver el archivo y el README).")
        return []

        # ------------------------------------------------------------------
        # ESQUELETO DE REFERENCIA (descomenta y completa para activarlo):
        # ------------------------------------------------------------------
        # import httpclient, json
        # api_key = self.settings.get("api_key", "")
        # if not api_key:
        #     print("   ❌ Falta 'api_key' en config.py para el agregador.")
        #     return []
        #
        # # TODO: construir la URL del agregador con sus parámetros y, si
        # #       'since' existe, pedir solo lo nuevo. Llamar a la API,
        # #       parsear el JSON y mapear cada registro a Disclosure(...).
        # resultados: List[Disclosure] = []
        # return resultados
