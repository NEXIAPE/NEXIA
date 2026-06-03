"""
models.py
=========

Aquí vive el "FORMATO COMÚN" de datos de todo el proyecto.

Idea central (y la más importante para principiantes):
  Cada fuente (Cámara, Senado, agregador externo) habla un "idioma" distinto.
  En lugar de que el resto del programa tenga que entender 3 idiomas, cada
  conector TRADUCE sus datos a UNA sola estructura: la clase `Disclosure`.

  Así, la capa de consolidación, la base de datos y el informe solo necesitan
  entender `Disclosure`. Si mañana agregas una 4ª fuente, solo escribes un
  conector nuevo que devuelva `Disclosure`; nada más se rompe.

Una `Disclosure` = UNA operación bursátil reportada (una compra o una venta
de un activo). Un mismo documento PDF puede generar muchas `Disclosure`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


# Tipos de transacción normalizados. Cada conector debe mapear sus códigos
# propios (ej. la Cámara usa "P", "S", "E") a uno de estos valores.
TX_PURCHASE = "purchase"   # compra
TX_SALE = "sale"           # venta (total o parcial)
TX_EXCHANGE = "exchange"   # canje / intercambio
TX_UNKNOWN = "unknown"     # no se pudo determinar


@dataclass
class Disclosure:
    """
    Una operación bursátil divulgada bajo la STOCK Act.

    Los campos están pensados para ser "el mínimo común denominador" entre
    todas las fuentes. Si una fuente no aporta algún dato, se deja en None
    o cadena vacía: el programa nunca debe asumir que un campo opcional existe.
    """

    # --- De dónde salió el dato (trazabilidad) ---
    source: str                      # id corto del conector, ej. "house"
    chamber: str                     # "House" o "Senate" (o "Aggregator")
    doc_id: str                      # id del documento en la fuente original
    source_url: str = ""             # enlace al documento original (auditoría)

    # --- Quién reportó ---
    filer_name: str = ""             # nombre del legislador (normalizado)
    filer_state: str = ""            # estado / distrito, ej. "TX07"
    owner: str = ""                  # dueño del activo: self/spouse/joint/dependent

    # --- Tipo de presentación ---
    filing_type: str = ""            # ej. "PTR" (Periodic Transaction Report)
    filing_date: Optional[date] = None   # fecha en que se presentó el reporte
    is_amendment: bool = False       # ¿es una corrección/enmienda?
    amends_doc_id: str = ""          # doc_id del original que corrige (si se sabe)

    # --- Qué se operó ---
    asset_description: str = ""      # texto del activo tal como aparece
    ticker: str = ""                 # símbolo bursátil, ej. "AAPL" ("" si no hay)
    tx_type: str = TX_UNKNOWN        # purchase / sale / exchange / unknown
    tx_date: Optional[date] = None   # fecha de la operación
    notification_date: Optional[date] = None  # fecha en que se notificó
    amount_min: Optional[int] = None  # extremo bajo del rango en USD
    amount_max: Optional[int] = None  # extremo alto del rango en USD

    # --- Enriquecimiento (se completa después de consolidar) ---
    sector: str = ""                 # sector económico del ticker

    # --- Datos crudos opcionales (por si quieres depurar) ---
    raw: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Claves de identidad. Son la base del "quitar duplicados".
    # ------------------------------------------------------------------
    def logical_key(self) -> str:
        """
        Identidad LÓGICA de la operación, IGNORANDO si es original o enmienda.

        Sirve para detectar que "la misma operación" aparece tanto en el
        reporte original como en una corrección posterior. Si dos `Disclosure`
        tienen la misma logical_key, son (probablemente) la misma operación y
        nos quedamos con la versión más reciente / la enmienda.

        Nota honesta: esto puede fusionar de más si alguien compró el mismo
        ticker, el mismo día, del mismo tipo, dos veces. Es un compromiso
        razonable y está documentado.
        """
        parts = [
            _norm(self.filer_name),
            _norm(self.ticker) or _norm(self.asset_description)[:40],
            self.tx_type,
            _iso(self.tx_date),
        ]
        return _sha1("|".join(parts))

    def row_hash(self) -> str:
        """
        Identidad EXACTA de la fila (incluye monto y si es enmienda).

        Es la clave primaria en SQLite: garantiza que no insertemos dos veces
        exactamente el mismo registro entre corridas distintas.
        """
        parts = [
            self.source,
            self.doc_id,
            _norm(self.filer_name),
            _norm(self.ticker),
            self.tx_type,
            _iso(self.tx_date),
            str(self.amount_min),
            str(self.amount_max),
            "A" if self.is_amendment else "O",
        ]
        return _sha1("|".join(parts))

    def to_db_row(self) -> dict:
        """Convierte la operación a un diccionario listo para SQLite."""
        d = asdict(self)
        d.pop("raw", None)                 # no guardamos el crudo en la tabla
        d["filing_date"] = _iso(self.filing_date)
        d["tx_date"] = _iso(self.tx_date)
        d["notification_date"] = _iso(self.notification_date)
        d["is_amendment"] = 1 if self.is_amendment else 0
        d["row_hash"] = self.row_hash()
        return d


# ----------------------------------------------------------------------
# Funciones auxiliares pequeñas (privadas de este módulo)
# ----------------------------------------------------------------------
def _norm(text: str) -> str:
    """Normaliza texto para comparar: minúsculas y sin espacios extra."""
    return " ".join((text or "").lower().split())


def _iso(d: Optional[date]) -> str:
    """Convierte una fecha a 'YYYY-MM-DD' (o '' si es None)."""
    return d.isoformat() if d else ""


def _sha1(text: str) -> str:
    """Hash corto y estable para usar como identificador."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
