"""
report.py
=========

Genera el INFORME DIARIO en texto legible. Contiene tres secciones:
  1) Divulgaciones NUEVAS detectadas en esta corrida.
  2) Top de tickers de los últimos N días.
  3) Desglose por sector de los últimos N días.

MUY IMPORTANTE (y va escrito en el propio informe):
  Esto es DESCRIPTIVO E INFORMATIVO. NO es asesoría financiera ni una
  recomendación de compra/venta. Los datos tienen un desfase legal de hasta
  ~45 días, así que NUNCA reflejan operaciones "en tiempo real".

El informe se imprime en pantalla Y se guarda en un archivo .txt con la fecha.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import List

import config
import storage

# Aviso legal que encabeza CADA informe.
DISCLAIMER = (
    "AVISO: Informe DESCRIPTIVO con datos públicos divulgados bajo la STOCK "
    "Act. NO es asesoría financiera ni recomendación de compra/venta. Los "
    "datos pueden tener hasta ~45 días de desfase legal respecto a la "
    "operación real y pueden contener errores u omisiones de la fuente."
)


def build_report(conn: sqlite3.Connection, run_id: int) -> str:
    """Construye el texto completo del informe y lo devuelve como string."""
    dias = config.REPORT_WINDOW_DAYS
    lineas: List[str] = []

    def add(texto: str = "") -> None:
        lineas.append(texto)

    # ---- Encabezado ----
    add("=" * 70)
    add(f"  INFORME DIARIO — DIVULGACIONES STOCK ACT")
    add(f"  Fecha de generación: {date.today().isoformat()}")
    add("=" * 70)
    add(_wrap(DISCLAIMER))
    add("=" * 70)
    add()

    # ---- Sección 1: divulgaciones nuevas ----
    nuevas = storage.get_new_in_run(conn, run_id)
    add(f"1) DIVULGACIONES NUEVAS EN ESTA CORRIDA: {len(nuevas)}")
    add("-" * 70)
    if not nuevas:
        add("   (No se detectaron divulgaciones nuevas desde la última corrida.)")
    else:
        for r in nuevas:
            add(_format_disclosure_line(r))
    add()

    # ---- Sección 2: top de tickers ----
    top = storage.get_top_tickers(conn, dias, config.REPORT_TICKER_TOP_N)
    add(f"2) TOP {config.REPORT_TICKER_TOP_N} TICKERS — últimos {dias} días")
    add("-" * 70)
    if not top:
        add("   (Aún no hay transacciones con ticker en la ventana de tiempo.)")
    else:
        for i, r in enumerate(top, start=1):
            add(f"   {i:>2}. {r['ticker']:<8} — "
                f"{r['operaciones']} operación(es)")
    add()

    # ---- Sección 3: desglose por sector ----
    sectores = storage.get_sector_breakdown(conn, dias)
    add(f"3) DESGLOSE POR SECTOR — últimos {dias} días")
    add("-" * 70)
    if not sectores:
        add("   (Sin datos en la ventana de tiempo.)")
    else:
        total = sum(r["operaciones"] for r in sectores) or 1
        for r in sectores:
            pct = 100.0 * r["operaciones"] / total
            barra = "█" * int(pct / 4)   # mini-gráfico de barras en texto
            add(f"   {r['sector']:<28} {r['operaciones']:>4} "
                f"({pct:4.1f}%) {barra}")
    add()
    add("=" * 70)
    add("Fin del informe.")

    return "\n".join(lineas)


def save_report(texto: str) -> Path:
    """Guarda el informe en output/informe-YYYY-MM-DD.txt y devuelve la ruta."""
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ruta = config.OUTPUT_DIR / f"informe-{date.today().isoformat()}.txt"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


# ----------------------------------------------------------------------
# Ayudantes de formato
# ----------------------------------------------------------------------
def _format_disclosure_line(r: sqlite3.Row) -> str:
    """Una línea legible por divulgación."""
    enmienda = " [ENMIENDA]" if r["is_amendment"] else ""
    ticker = r["ticker"] or "—"
    tx = r["tx_type"] or "—"
    monto = _format_amount(r["amount_min"], r["amount_max"])
    fecha = r["tx_date"] or r["filing_date"] or "—"
    return (f"   • {r['filer_name']} ({r['filer_state'] or '—'}) | "
            f"{ticker:<6} | {tx:<8} | {monto:<20} | {fecha}{enmienda}\n"
            f"     {(r['asset_description'] or '')[:80]}")


def _format_amount(lo, hi) -> str:
    if lo is None and hi is None:
        return "monto no informado"
    if lo is not None and hi is not None:
        return f"${lo:,} - ${hi:,}"
    return f"${(lo or hi):,}"


def _wrap(texto: str, ancho: int = 70) -> str:
    """Parte un texto largo en líneas de `ancho` caracteres."""
    import textwrap
    return "\n".join(textwrap.wrap(texto, ancho))
