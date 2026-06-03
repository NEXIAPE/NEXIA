#!/usr/bin/env python3
"""
main.py
=======

El ORQUESTADOR: el archivo que ejecutas. Une todas las piezas:

  conectores activos  ->  consolidación (dedup)  ->  SQLite  ->  informe

Modos de uso (desde la terminal, dentro de la carpeta del proyecto):

  python main.py                # corrida normal (usa las fuentes activas)
  python main.py --self-test    # PRUEBA OFFLINE: verifica el flujo sin internet
  python main.py --report-only  # regenera el informe con lo que ya hay en la BD

Para principiantes: empieza SIEMPRE por `--self-test`. Confirma que todo el
"esqueleto" funciona antes de salir a internet a buscar datos reales.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import config
import storage
from connectors import get_enabled_connectors
from consolidation import consolidate
from models import Disclosure, TX_PURCHASE, TX_SALE
from report import build_report, save_report


def run(self_test: bool = False, report_only: bool = False) -> int:
    """Ejecuta una corrida completa. Devuelve un código de salida (0 = OK)."""
    conn = storage.connect()

    # Modo "solo informe": no busca datos nuevos, solo reimprime.
    if report_only:
        # Tomamos la última corrida registrada para el bloque "nuevas".
        ultimo = conn.execute(
            "SELECT id FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        run_id = ultimo["id"] if ultimo else 0
        _emit_report(conn, run_id)
        return 0

    run_id = storage.start_run(conn)
    since = storage.get_last_finished_run_time(conn)
    if since:
        print(f"⏱️  Última corrida: {since:%Y-%m-%d %H:%M}. "
              f"Buscaré solo lo presentado desde entonces.")
    else:
        print("⏱️  Primera corrida: no hay marca previa, tomaré lo disponible.")

    # --- Recolectar datos ---
    if self_test:
        print("\n🧪 MODO SELF-TEST: usando datos de ejemplo (sin internet).\n")
        grupos = [_sample_disclosures()]
    else:
        conectores = get_enabled_connectors()
        print(f"\n🔌 Conectores activos: "
              f"{', '.join(c.name for c in conectores) or 'NINGUNO'}\n")
        if not conectores:
            print("⚠️  No hay conectores activos en config.py. "
                  "Activa al menos 'house'. Abortando.")
            storage.finish_run(conn, run_id, 0, 0)
            return 1
        grupos = []
        for c in conectores:
            try:
                grupos.append(c.fetch(since=since))
            except Exception as e:   # noqa: BLE001
                print(f"❌ El conector '{c.name}' falló: {e}. Continúo con el resto.")
                grupos.append([])

    # --- Consolidar (quitar duplicados y resolver enmiendas) ---
    consolidadas = consolidate(grupos)

    # --- Guardar y detectar lo nuevo ---
    nuevas = storage.save_disclosures(conn, run_id, consolidadas)
    storage.finish_run(conn, run_id, nuevas, len(consolidadas))
    print(f"\n💾 Guardado en SQLite: {nuevas} nuevas de "
          f"{len(consolidadas)} consolidadas.\n")

    # --- Informe ---
    _emit_report(conn, run_id)
    return 0


def _emit_report(conn, run_id: int) -> None:
    texto = build_report(conn, run_id)
    print(texto)
    ruta = save_report(texto)
    print(f"\n📝 Informe guardado en: {ruta}")


def _sample_disclosures():
    """
    Datos de ejemplo para --self-test. Incluyen A PROPÓSITO:
      - un duplicado EXACTO (para probar el dedup por row_hash),
      - una ENMIENDA de una operación original (para probar la fusión).
    Así puedes ver que la consolidación funciona sin depender de internet.
    """
    hoy = date.today()
    base = Disclosure(
        source="house", chamber="House", doc_id="20000001",
        filer_name="Jane Doe", filer_state="CA12", filing_type="PTR",
        filing_date=hoy, asset_description="Apple Inc. (AAPL)",
        ticker="AAPL", tx_type=TX_PURCHASE, tx_date=hoy,
        amount_min=1001, amount_max=15000,
    )
    duplicado_exacto = Disclosure(
        source="house", chamber="House", doc_id="20000001",
        filer_name="Jane Doe", filer_state="CA12", filing_type="PTR",
        filing_date=hoy, asset_description="Apple Inc. (AAPL)",
        ticker="AAPL", tx_type=TX_PURCHASE, tx_date=hoy,
        amount_min=1001, amount_max=15000,
    )
    original_con_error = Disclosure(
        source="house", chamber="House", doc_id="20000002",
        filer_name="John Smith", filer_state="TX07", filing_type="PTR",
        filing_date=hoy, asset_description="Microsoft Corp (MSFT)",
        ticker="MSFT", tx_type=TX_SALE, tx_date=hoy,
        amount_min=15001, amount_max=50000,   # monto que luego se corrige
    )
    enmienda = Disclosure(
        source="house", chamber="House", doc_id="20000003",
        filer_name="John Smith", filer_state="TX07", filing_type="PTR",
        filing_date=hoy, asset_description="Microsoft Corp (MSFT)",
        ticker="MSFT", tx_type=TX_SALE, tx_date=hoy,
        amount_min=50001, amount_max=100000,  # monto corregido
        is_amendment=True, amends_doc_id="20000002",
    )
    otra = Disclosure(
        source="house", chamber="House", doc_id="20000004",
        filer_name="Maria Lopez", filer_state="FL09", filing_type="PTR",
        filing_date=hoy, asset_description="NVIDIA Corp (NVDA)",
        ticker="NVDA", tx_type=TX_PURCHASE, tx_date=hoy,
        amount_min=1001, amount_max=15000,
    )
    return [base, duplicado_exacto, original_con_error, enmienda, otra]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rastreador modular de divulgaciones STOCK Act (v1).")
    parser.add_argument("--self-test", action="store_true",
                        help="Prueba el flujo completo con datos de ejemplo, sin internet.")
    parser.add_argument("--report-only", action="store_true",
                        help="Solo regenera el informe con lo que ya hay en la BD.")
    args = parser.parse_args()
    sys.exit(run(self_test=args.self_test, report_only=args.report_only))


if __name__ == "__main__":
    main()
