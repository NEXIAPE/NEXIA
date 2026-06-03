"""
config.py
=========

TODA la configuración del proyecto en un solo lugar. Si eres principiante,
este es el único archivo que normalmente necesitarás tocar.

Lo más importante: el diccionario CONNECTORS, que ENCIENDE o APAGA cada
fuente. En la versión 1 SOLO está activa la Cámara (House). Las demás están
listas pero desactivadas. Para activarlas, cambia `False` por `True`
(y lee las instrucciones del README, sección "Activar fuentes adicionales").
"""

from datetime import date
from pathlib import Path

# Carpeta base del proyecto (se calcula sola; no la cambies).
BASE_DIR = Path(__file__).resolve().parent

# ----------------------------------------------------------------------
# 1) FUENTES (CONECTORES): encender / apagar
# ----------------------------------------------------------------------
# Clave  -> nombre interno del conector.
# enabled-> True para activarlo, False para dejarlo dormido.
#
#  >>> EN LA v1, SOLO "house" ESTÁ EN True. NO TOQUES LAS DEMÁS TODAVÍA. <<<
CONNECTORS = {
    "house": {
        "enabled": True,            # ✅ ACTIVO en la v1
        "years": [date.today().year],   # años del índice a descargar
        # Límite de PDFs a descargar por corrida (cortesía / rate limit).
        "max_pdf_downloads": 40,
        # Intentar extraer transacciones del PDF (necesita 'pdfplumber').
        # Si lo pones en False, igual registra la presentación pero sin tickers.
        "parse_pdf_transactions": True,
    },
    "senate": {
        "enabled": False,           # ⛔ DESACTIVADO (listo para activar luego)
        "years": [date.today().year],
    },
    "aggregator": {
        "enabled": False,           # ⛔ DESACTIVADO (solo es un hueco/plantilla)
        "api_key": "",              # se rellenará cuando elijas un agregador
    },
}

# ----------------------------------------------------------------------
# 2) RED: cómo nos comportamos al pedir datos (¡respeta a los servidores!)
# ----------------------------------------------------------------------
# Los sitios oficiales bloquean clientes "robóticos". Hay que identificarse
# con un User-Agent realista y de contacto, e ir despacio.
HTTP_HEADERS = {
    "User-Agent": (
        "STOCKAct-Tracker-Educativo/1.0 "
        "(proyecto personal de aprendizaje; contacto: admin@nexia.fit)"
    ),
    "Accept": "*/*",
}

# Segundos de espera ENTRE peticiones a la misma fuente (rate limiting).
# Subir este número si te bloquean (HTTP 403/429). No bajar de 1.0.
REQUEST_DELAY_SECONDS = 2.0

# Tiempo máximo de espera por petición (segundos) antes de rendirse.
REQUEST_TIMEOUT_SECONDS = 30

# Cuántas veces reintentar una descarga fallida, con esperas crecientes.
HTTP_MAX_RETRIES = 3

# ----------------------------------------------------------------------
# 3) ARCHIVOS DE SALIDA
# ----------------------------------------------------------------------
DB_PATH = BASE_DIR / "stockact.db"          # base de datos SQLite
OUTPUT_DIR = BASE_DIR / "output"            # aquí se guardan los informes
CACHE_DIR = BASE_DIR / "output" / "_cache"  # PDFs/ZIPs descargados (cache)

# ----------------------------------------------------------------------
# 4) INFORME
# ----------------------------------------------------------------------
REPORT_TICKER_TOP_N = 10        # top de tickers a mostrar
REPORT_WINDOW_DAYS = 30         # ventana de tiempo del análisis (días)
