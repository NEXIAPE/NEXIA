"""
httpclient.py
=============

Un ayudante MUY pequeño para descargar cosas de internet "con buenos modales":
  - envía un User-Agent identificable (config.HTTP_HEADERS),
  - reintenta con esperas crecientes si falla la red (2s, 4s, 8s...),
  - respeta los tiempos de espera.

Lo usan los conectores que acceden a la red. Tener esto en un solo lugar evita
copiar el mismo código en cada conector.
"""

from __future__ import annotations

import time

import config

# Importamos 'requests' de forma perezosa dentro de la función, no aquí arriba.
# Así, el modo --self-test (que no usa internet) funciona aunque todavía no
# hayas hecho 'pip install -r requirements.txt'.


def download_bytes(url: str) -> bytes:
    """
    Descarga el contenido de `url` y lo devuelve como bytes.

    Reintenta hasta config.HTTP_MAX_RETRIES veces con backoff exponencial.
    Si todo falla, lanza la última excepción (el conector la captura).
    """
    import requests  # import perezoso (ver nota arriba)

    last_error = None
    for intento in range(1, config.HTTP_MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers=config.HTTP_HEADERS,
                timeout=config.REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()   # lanza error si el código HTTP es 4xx/5xx
            return resp.content
        except Exception as e:          # noqa: BLE001 (queremos capturar todo)
            last_error = e
            espera = 2 ** intento       # 2, 4, 8 segundos...
            print(f"   ⚠️  Falló la descarga ({e}). "
                  f"Reintento {intento}/{config.HTTP_MAX_RETRIES} en {espera}s")
            time.sleep(espera)
    # Si llegamos aquí, agotamos los reintentos.
    raise last_error  # type: ignore[misc]
