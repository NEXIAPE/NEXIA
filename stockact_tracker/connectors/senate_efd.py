"""
connectors/senate_efd.py
========================

Conector del SENADO de EE.UU. — portal EFD (Electronic Financial Disclosure).
⛔ DESACTIVADO EN LA v1. Está listo como ESQUELETO para que lo actives después.

POR QUÉ NO VIENE ACTIVO (y por qué es más difícil que la Cámara):
  - El Senado NO ofrece un ZIP/XML anual descargable como la Cámara.
  - Su portal (https://efdsearch.senate.gov/) exige primero ACEPTAR los
    términos de uso vía un formulario, lo que crea una "sesión" (cookie/CSRF)
    antes de poder buscar.
  - La búsqueda devuelve resultados paginados en HTML/JSON; cada PTR es un
    documento aparte (a veces HTML estructurado, a veces PDF).

CÓMO ACTIVARLO (cuando estés listo, ver también el README):
  1) Pon  "senate": {"enabled": True}  en config.py.
  2) Implementa los pasos marcados con TODO más abajo:
       a. Aceptar términos: POST a /search/home/ para obtener cookies + CSRF.
       b. Buscar PTRs: POST a /search/report/data/ con filtros y paginación.
       c. Para cada resultado, descargar el documento y mapear a Disclosure.
  3) RESPETA el rate limit (usa self.polite_sleep()) y los términos del sitio.

Mientras 'enabled' sea False, este conector NO se usa y devuelve [].
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from connectors.base import BaseConnector
from models import Disclosure

# Constantes útiles para cuando lo implementes (referencia):
EFD_HOME = "https://efdsearch.senate.gov/search/home/"
EFD_SEARCH_DATA = "https://efdsearch.senate.gov/search/report/data/"


class SenateEFDConnector(BaseConnector):
    name = "senate"
    label = "Senado de EE.UU. (portal EFD)"

    def fetch(self, since: Optional[datetime] = None) -> List[Disclosure]:
        # Cuando 'enabled' sea True pero el código aún no esté implementado,
        # avisamos con claridad en vez de fingir que funciona.
        print(f"⏭️  [{self.label}] DESACTIVADO o no implementado todavía. "
              f"Ver instrucciones en connectors/senate_efd.py y README.")
        return []

        # ------------------------------------------------------------------
        # ESQUELETO DE REFERENCIA (descomenta y completa para activarlo):
        # ------------------------------------------------------------------
        # import requests
        # import config
        #
        # session = requests.Session()
        # session.headers.update(config.HTTP_HEADERS)
        #
        # # a. Aceptar términos para obtener cookies + token CSRF.
        # #    TODO: GET EFD_HOME, extraer csrfmiddlewaretoken del HTML,
        # #          POST EFD_HOME con prohibition_agreement=1 + el token.
        #
        # # b. Buscar PTRs (paginado). El endpoint /search/report/data/
        # #    espera parámetros tipo DataTables (draw, start, length, ...)
        # #    y filtros (report_types=[11] para PTR, dates, etc.).
        # #    TODO: iterar páginas con self.polite_sleep() entre cada una.
        #
        # # c. Para cada fila, construir un Disclosure mapeando los campos
        # #    del Senado al formato común. TODO.
        #
        # resultados: List[Disclosure] = []
        # return resultados
