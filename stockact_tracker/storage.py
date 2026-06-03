"""
storage.py
==========

La capa de BASE DE DATOS (SQLite). Responsabilidades:
  - Crear las tablas si no existen.
  - Guardar operaciones SIN duplicar entre corridas (clave: row_hash).
  - Marcar qué operaciones son NUEVAS en cada corrida (para el "solo lo nuevo
    desde la última vez").
  - Responder las consultas que necesita el informe.

¿Por qué SQLite? Es una base de datos que vive en UN solo archivo
(stockact.db), no necesita servidor ni instalación. Perfecta para empezar.

Concepto clave del "incremental":
  Cada corrida crea una fila en la tabla `runs` con un id. Al guardar una
  operación nueva, le ponemos ese run_id en `first_seen_run_id`. Así, "lo
  nuevo de esta corrida" = las filas cuyo first_seen_run_id es el de ahora.
  Si una operación ya existía (mismo row_hash), INSERT OR IGNORE no la duplica
  y conserva el run_id de la PRIMERA vez que la vimos.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import config
from models import Disclosure


def connect() -> sqlite3.Connection:
    """Abre (o crea) la base de datos y asegura que existan las tablas."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row     # poder leer columnas por nombre
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at    TEXT NOT NULL,
            finished_at   TEXT,
            new_count     INTEGER DEFAULT 0,
            total_seen    INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS disclosures (
            row_hash            TEXT PRIMARY KEY,
            source              TEXT,
            chamber             TEXT,
            doc_id              TEXT,
            source_url          TEXT,
            filer_name          TEXT,
            filer_state         TEXT,
            owner               TEXT,
            filing_type         TEXT,
            filing_date         TEXT,
            is_amendment        INTEGER,
            amends_doc_id       TEXT,
            asset_description   TEXT,
            ticker              TEXT,
            tx_type             TEXT,
            tx_date             TEXT,
            notification_date   TEXT,
            amount_min          INTEGER,
            amount_max          INTEGER,
            sector              TEXT,
            first_seen_run_id   INTEGER,
            first_seen_at       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tx_date ON disclosures(tx_date);
        CREATE INDEX IF NOT EXISTS idx_ticker  ON disclosures(ticker);
        """
    )
    conn.commit()


# ----------------------------------------------------------------------
# Manejo de corridas (runs)
# ----------------------------------------------------------------------
def start_run(conn: sqlite3.Connection) -> int:
    """Crea una fila de corrida y devuelve su id."""
    cur = conn.execute(
        "INSERT INTO runs (started_at) VALUES (?)",
        (datetime.now().isoformat(timespec="seconds"),),
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int,
               new_count: int, total_seen: int) -> None:
    conn.execute(
        "UPDATE runs SET finished_at = ?, new_count = ?, total_seen = ? "
        "WHERE id = ?",
        (datetime.now().isoformat(timespec="seconds"),
         new_count, total_seen, run_id),
    )
    conn.commit()


def get_last_finished_run_time(conn: sqlite3.Connection) -> Optional[datetime]:
    """
    Devuelve cuándo terminó la ÚLTIMA corrida exitosa (o None si es la primera
    vez). Los conectores usan esto como 'since' para pedir solo lo nuevo.
    """
    row = conn.execute(
        "SELECT started_at FROM runs WHERE finished_at IS NOT NULL "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    try:
        return datetime.fromisoformat(row["started_at"])
    except (ValueError, TypeError):
        return None


# ----------------------------------------------------------------------
# Guardado de operaciones
# ----------------------------------------------------------------------
def save_disclosures(conn: sqlite3.Connection, run_id: int,
                     disclosures: List[Disclosure]) -> int:
    """
    Inserta operaciones evitando duplicados (INSERT OR IGNORE por row_hash).
    Devuelve cuántas eran NUEVAS (realmente insertadas en esta corrida).
    """
    nuevas = 0
    ahora = datetime.now().isoformat(timespec="seconds")
    for d in disclosures:
        fila = d.to_db_row()
        fila["first_seen_run_id"] = run_id
        fila["first_seen_at"] = ahora
        columnas = ", ".join(fila.keys())
        marcadores = ", ".join(["?"] * len(fila))
        cur = conn.execute(
            f"INSERT OR IGNORE INTO disclosures ({columnas}) "
            f"VALUES ({marcadores})",
            list(fila.values()),
        )
        # rowcount == 1 significa que SÍ se insertó (era nueva).
        if cur.rowcount == 1:
            nuevas += 1
    conn.commit()
    return nuevas


# ----------------------------------------------------------------------
# Consultas para el informe
# ----------------------------------------------------------------------
def get_new_in_run(conn: sqlite3.Connection, run_id: int) -> List[sqlite3.Row]:
    """Operaciones vistas por PRIMERA vez en esta corrida."""
    return conn.execute(
        "SELECT * FROM disclosures WHERE first_seen_run_id = ? "
        "ORDER BY filing_date DESC, filer_name ASC",
        (run_id,),
    ).fetchall()


def get_top_tickers(conn: sqlite3.Connection, days: int,
                    limit: int) -> List[sqlite3.Row]:
    """Top de tickers más operados en los últimos `days` días (por tx_date)."""
    return conn.execute(
        """
        SELECT ticker, COUNT(*) AS operaciones
        FROM disclosures
        WHERE ticker <> ''
          AND tx_date <> ''
          AND tx_date >= date('now', ?)
        GROUP BY ticker
        ORDER BY operaciones DESC, ticker ASC
        LIMIT ?
        """,
        (f"-{days} day", limit),
    ).fetchall()


def get_sector_breakdown(conn: sqlite3.Connection,
                         days: int) -> List[sqlite3.Row]:
    """Conteo de operaciones por sector en los últimos `days` días."""
    return conn.execute(
        """
        SELECT sector, COUNT(*) AS operaciones
        FROM disclosures
        WHERE tx_date <> ''
          AND tx_date >= date('now', ?)
        GROUP BY sector
        ORDER BY operaciones DESC
        """,
        (f"-{days} day",),
    ).fetchall()
