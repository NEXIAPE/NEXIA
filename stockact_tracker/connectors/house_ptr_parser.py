"""
connectors/house_ptr_parser.py
===============================

Extrae las TRANSACCIONES (compras/ventas individuales) de un PDF de PTR
(Periodic Transaction Report) de la Cámara de Representantes.

¿Por qué un módulo aparte? Porque parsear PDFs es la parte más frágil y
"sucia" del proyecto. Aislarla aquí mantiene el conector limpio y te permite
mejorar el parser sin tocar el resto.

LÍMITE HONESTO E IMPORTANTE:
  - Los PTR presentados ELECTRÓNICAMENTE (DocID que suele empezar por "2",
    8 dígitos) son PDFs con texto y tabla: se pueden parsear bien.
  - Los PTR ESCANEADOS / a mano (DocIDs antiguos) son imágenes: este parser
    NO los lee. En ese caso devolvemos lista vacía y el conector registra la
    presentación SIN transacciones (igual aparece como "nueva divulgación").

Depende de la librería 'pdfplumber'. Si no está instalada, este módulo lo
informa con un mensaje claro en vez de romper el programa.
"""

from __future__ import annotations

import io
import re
from datetime import datetime, date
from typing import List, Optional

from models import (
    Disclosure, TX_PURCHASE, TX_SALE, TX_EXCHANGE, TX_UNKNOWN,
)

# Importamos pdfplumber de forma "perezosa y tolerante": si no está instalado,
# guardamos el error y avisamos al usarlo, sin tumbar todo el programa.
try:
    import pdfplumber  # type: ignore
    _PDFPLUMBER_OK = True
except Exception:       # noqa: BLE001
    pdfplumber = None   # type: ignore
    _PDFPLUMBER_OK = False


# Expresiones regulares ("patrones de texto") que usamos para reconocer datos.
_TICKER_RE = re.compile(r"\(([A-Z]{1,5})\)")          # ej. (AAPL)
_AMOUNT_RE = re.compile(r"\$([\d,]+)\s*-\s*\$([\d,]+)")  # ej. $1,001 - $15,000
_DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")          # ej. 03/15/2026


def pdfplumber_available() -> bool:
    """Permite al conector avisar si falta la dependencia opcional."""
    return _PDFPLUMBER_OK


def parse_ptr_pdf(pdf_bytes: bytes) -> List[Disclosure]:
    """
    Recibe el contenido binario de un PDF de PTR y devuelve una lista de
    `Disclosure` PARCIALES (solo los campos de la transacción).

    El conector completará después los campos del legislador (nombre, estado,
    doc_id, etc.), porque esos vienen del índice XML, no del PDF.

    Si no se puede parsear (PDF escaneado, sin texto, o falta pdfplumber),
    devuelve [] sin lanzar excepción.
    """
    if not _PDFPLUMBER_OK:
        return []

    transacciones: List[Disclosure] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                # 1) Intento preferido: leer la TABLA de la página.
                for tabla in page.extract_tables() or []:
                    transacciones.extend(_rows_from_table(tabla))
        # 2) Si la tabla no dio nada, intento de respaldo: leer texto suelto.
        if not transacciones:
            transacciones.extend(_rows_from_text(pdf_bytes))
    except Exception:   # noqa: BLE001  (un PDF roto no debe tumbar la corrida)
        return []
    return transacciones


# ----------------------------------------------------------------------
# Estrategia 1: a partir de la tabla extraída por pdfplumber.
# ----------------------------------------------------------------------
def _rows_from_table(tabla: list) -> List[Disclosure]:
    salida: List[Disclosure] = []
    for fila in tabla:
        # Unimos las celdas en un solo texto y reutilizamos el parser de línea.
        celdas = [c for c in fila if c]
        if not celdas:
            continue
        linea = " ".join(str(c).replace("\n", " ") for c in celdas)
        d = _parse_transaction_line(linea)
        if d:
            salida.append(d)
    return salida


# ----------------------------------------------------------------------
# Estrategia 2 (respaldo): a partir del texto plano del PDF.
# ----------------------------------------------------------------------
def _rows_from_text(pdf_bytes: bytes) -> List[Disclosure]:
    salida: List[Disclosure] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:  # type: ignore
            for page in pdf.pages:
                texto = page.extract_text() or ""
                for linea in texto.splitlines():
                    d = _parse_transaction_line(linea)
                    if d:
                        salida.append(d)
    except Exception:   # noqa: BLE001
        return []
    return salida


def _parse_transaction_line(linea: str) -> Optional[Disclosure]:
    """
    Intenta extraer una transacción de UNA línea de texto.

    Una línea válida de PTR electrónico contiene, típicamente:
      [Dueño] Nombre del activo (TICKER) [tipo] P/S/E  fecha  fecha  $rango
    Solo aceptamos la línea si encontramos al menos un rango de montos
    (es la señal más fiable de que es una fila de transacción).
    """
    monto = _AMOUNT_RE.search(linea)
    if not monto:
        return None  # sin rango de $ no lo tratamos como transacción

    amount_min = int(monto.group(1).replace(",", ""))
    amount_max = int(monto.group(2).replace(",", ""))

    # Ticker: tomamos el ÚLTIMO paréntesis con mayúsculas (suele ser el símbolo).
    tickers = _TICKER_RE.findall(linea)
    ticker = tickers[-1] if tickers else ""

    # Fechas: la primera suele ser la de transacción.
    fechas = [_parse_us_date(f) for f in _DATE_RE.findall(linea)]
    tx_date = fechas[0] if fechas else None
    notification_date = fechas[1] if len(fechas) > 1 else None

    # Tipo de transacción.
    tx_type = _detect_tx_type(linea)

    # Descripción del activo: lo que va antes del primer "(" o del primer "$".
    corte = linea.find("(")
    if corte == -1:
        corte = linea.find("$")
    asset = linea[:corte].strip(" .-") if corte > 0 else linea.strip()

    return Disclosure(
        source="house",
        chamber="House",
        doc_id="",                  # lo rellena el conector
        asset_description=asset[:200],
        ticker=ticker,
        tx_type=tx_type,
        tx_date=tx_date,
        notification_date=notification_date,
        amount_min=amount_min,
        amount_max=amount_max,
    )


def _detect_tx_type(linea: str) -> str:
    """Mapea los códigos de la Cámara a nuestros tipos normalizados."""
    L = f" {linea.lower()} "
    if "purchase" in L or re.search(r"\bp\b", L):
        return TX_PURCHASE
    if "sale" in L or re.search(r"\bs\b", L):
        return TX_SALE
    if "exchange" in L or re.search(r"\be\b", L):
        return TX_EXCHANGE
    return TX_UNKNOWN


def _parse_us_date(texto: str) -> Optional[date]:
    """Convierte 'MM/DD/YYYY' a un objeto date (o None si no se puede)."""
    try:
        return datetime.strptime(texto, "%m/%d/%Y").date()
    except ValueError:
        return None
