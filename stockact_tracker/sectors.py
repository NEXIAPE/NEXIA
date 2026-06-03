"""
sectors.py
==========

Traduce un TICKER (ej. "AAPL") a un SECTOR económico (ej. "Tecnología").

Para la v1 usamos un diccionario LOCAL y pequeño (sin internet, sin rate
limits). Es suficiente para aprender y para que el informe muestre un desglose
por sector de los tickers más comunes.

CÓMO MEJORARLO DESPUÉS (opcional):
  - Amplía el diccionario SECTOR_BY_TICKER con más símbolos.
  - O instala 'yfinance' (pip install yfinance) y reemplaza lookup_sector()
    por una consulta en línea. OJO: yfinance tiene rate limits y depende de
    una fuente no oficial; por eso NO es la opción por defecto.
"""

from __future__ import annotations

# Sectores de algunos de los tickers más negociados. Amplíalo a gusto.
SECTOR_BY_TICKER = {
    "AAPL": "Tecnología", "MSFT": "Tecnología", "NVDA": "Tecnología",
    "GOOGL": "Tecnología", "GOOG": "Tecnología", "META": "Tecnología",
    "AMZN": "Consumo discrecional", "TSLA": "Consumo discrecional",
    "HD": "Consumo discrecional", "NKE": "Consumo discrecional",
    "JPM": "Finanzas", "BAC": "Finanzas", "GS": "Finanzas", "WFC": "Finanzas",
    "V": "Finanzas", "MA": "Finanzas", "BRK.B": "Finanzas",
    "JNJ": "Salud", "PFE": "Salud", "UNH": "Salud", "LLY": "Salud",
    "ABBV": "Salud", "MRK": "Salud",
    "XOM": "Energía", "CVX": "Energía", "COP": "Energía",
    "BA": "Industriales", "CAT": "Industriales", "GE": "Industriales",
    "LMT": "Industriales", "RTX": "Industriales",
    "PG": "Consumo básico", "KO": "Consumo básico", "PEP": "Consumo básico",
    "WMT": "Consumo básico", "COST": "Consumo básico",
    "DIS": "Comunicaciones", "NFLX": "Comunicaciones", "T": "Comunicaciones",
    "VZ": "Comunicaciones",
    "NEE": "Servicios públicos", "DUK": "Servicios públicos",
    "PLD": "Bienes raíces", "AMT": "Bienes raíces",
}

UNKNOWN_SECTOR = "Desconocido / sin clasificar"


def lookup_sector(ticker: str) -> str:
    """Devuelve el sector del ticker, o un valor 'desconocido' si no está."""
    if not ticker:
        return UNKNOWN_SECTOR
    return SECTOR_BY_TICKER.get(ticker.upper().strip(), UNKNOWN_SECTOR)
