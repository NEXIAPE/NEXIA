"""
consolidation.py
================

La CAPA DE CONSOLIDACIÓN. Recibe las operaciones crudas de TODOS los
conectores activos y las deja limpias y listas para guardar:

  1) Junta todo en una sola lista (ya vienen en formato común `Disclosure`).
  2) Quita DUPLICADOS exactos (misma fila byte a byte -> mismo row_hash).
  3) Resuelve ENMIENDAS: si la misma operación lógica aparece en un reporte
     original y en una corrección/enmienda, se queda con la versión que manda
     (la enmienda; o, si ambas son del mismo tipo, la de fecha más reciente).
  4) Enriqudce cada operación con su SECTOR.

Esta capa NO sabe nada de internet ni de SQLite: solo transforma listas.
Eso la hace fácil de entender y de probar.
"""

from __future__ import annotations

from typing import Dict, List

from models import Disclosure
from sectors import lookup_sector


def consolidate(grupos: List[List[Disclosure]]) -> List[Disclosure]:
    """
    `grupos` = lista de listas; una sublista por cada conector.
    Devuelve una lista única, sin duplicados, con sectores asignados.
    """
    # Paso 1: aplanar todas las sublistas en una sola.
    todas: List[Disclosure] = [d for sub in grupos for d in sub]
    print(f"🔗 Consolidando {len(todas)} operaciones de "
          f"{len(grupos)} fuente(s)...")

    # Paso 2: quitar duplicados EXACTOS por row_hash.
    por_hash: Dict[str, Disclosure] = {}
    for d in todas:
        por_hash[d.row_hash()] = d
    sin_exactos = list(por_hash.values())
    quitados_exactos = len(todas) - len(sin_exactos)

    # Paso 3: resolver enmiendas por clave lógica.
    por_logica: Dict[str, Disclosure] = {}
    for d in sin_exactos:
        clave = d.logical_key()
        if clave not in por_logica:
            por_logica[clave] = d
        else:
            por_logica[clave] = _preferir(por_logica[clave], d)
    consolidadas = list(por_logica.values())
    quitados_enmiendas = len(sin_exactos) - len(consolidadas)

    # Paso 4: asignar sector a cada operación.
    for d in consolidadas:
        d.sector = lookup_sector(d.ticker)

    print(f"   • Duplicados exactos eliminados: {quitados_exactos}")
    print(f"   • Fusionadas por enmienda/corrección: {quitados_enmiendas}")
    print(f"   • Operaciones consolidadas finales: {len(consolidadas)}")
    return consolidadas


def _preferir(a: Disclosure, b: Disclosure) -> Disclosure:
    """
    Decide cuál de dos operaciones 'lógicamente iguales' conservar.

    Regla:
      1) Si una es enmienda y la otra no, gana la enmienda (es la corrección).
      2) Si empatan, gana la de fecha de presentación más reciente.
      3) Si aún empatan, da igual: devolvemos 'a'.
    """
    if a.is_amendment != b.is_amendment:
        return a if a.is_amendment else b
    fecha_a = a.filing_date
    fecha_b = b.filing_date
    if fecha_a and fecha_b:
        return a if fecha_a >= fecha_b else b
    return a
