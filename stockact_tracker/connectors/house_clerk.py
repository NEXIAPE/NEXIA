"""
connectors/house_clerk.py
=========================

Conector de la CÁMARA DE REPRESENTANTES de EE.UU. (House Clerk).
✅ ESTE ES EL ÚNICO CONECTOR ACTIVO EN LA VERSIÓN 1.

¿Cómo funciona la fuente oficial?
  1) La Cámara publica, por AÑO, un ZIP con el ÍNDICE de todas las
     presentaciones financieras:
         https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{AÑO}FD.zip
     Dentro del ZIP hay un archivo {AÑO}FD.xml.
  2) Ese XML lista cada presentación con campos:
         DocID, FilingType, Last/First (nombre), StateDst, Year, FilingDate.
     OJO: el XML NO trae las transacciones (ticker, monto). Solo el índice.
  3) El DETALLE de cada PTR (las compras/ventas) está en un PDF aparte:
         https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{AÑO}/{DocID}.pdf
     Ese PDF lo parseamos con house_ptr_parser.py (solo PTR electrónicos).

FilingType que nos interesa: "P" = Periodic Transaction Report (PTR), que es
donde se reportan las compras/ventas de acciones bajo la STOCK Act.

Flujo del conector:
  índice XML  ->  filtra PTRs (y por fecha 'since')  ->  baja cada PDF
              ->  parsea transacciones  ->  devuelve List[Disclosure]
"""

from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import List, Optional

import config
import httpclient
from connectors.base import BaseConnector
from connectors.house_ptr_parser import parse_ptr_pdf, pdfplumber_available
from models import Disclosure


# Plantillas de URL oficiales (se rellena {year} y {doc}).
INDEX_ZIP_URL = (
    "https://disclosures-clerk.house.gov/public_disc/"
    "financial-pdfs/{year}FD.zip"
)
PTR_PDF_URL = (
    "https://disclosures-clerk.house.gov/public_disc/"
    "ptr-pdfs/{year}/{doc}.pdf"
)


class HouseClerkConnector(BaseConnector):
    name = "house"
    label = "Cámara de Representantes (House Clerk)"

    def fetch(self, since: Optional[datetime] = None) -> List[Disclosure]:
        print(f"📥 [{self.label}] iniciando...")
        resultados: List[Disclosure] = []

        if self.settings.get("parse_pdf_transactions", True) and not pdfplumber_available():
            print("   ⚠️  'pdfplumber' no está instalado: registraré las "
                  "presentaciones PERO sin transacciones (sin tickers).")

        for year in self.settings.get("years", [date.today().year]):
            try:
                filings = self._download_index(year)
            except Exception as e:   # noqa: BLE001
                print(f"   ❌ No pude descargar el índice {year}: {e}")
                continue

            # Nos quedamos solo con los PTR (FilingType == 'P').
            ptrs = [f for f in filings if f["filing_type"].upper() == "P"]

            # Filtro incremental: si 'since' existe, solo lo presentado después.
            if since is not None:
                corte = since.date()
                ptrs = [f for f in ptrs
                        if f["filing_date"] and f["filing_date"] >= corte]

            print(f"   • Año {year}: {len(ptrs)} PTR a procesar "
                  f"(de {len(filings)} presentaciones totales).")

            # Cortesía / rate limit: no bajar más de N PDFs por corrida.
            tope = self.settings.get("max_pdf_downloads", 40)
            for filing in ptrs[:tope]:
                resultados.extend(self._process_ptr(filing, year))
                self.polite_sleep()    # esperar entre descargas

            if len(ptrs) > tope:
                print(f"   ⚠️  Había {len(ptrs)} PTR pero corté en {tope} "
                      f"(ver config 'max_pdf_downloads'). El resto se tomará "
                      f"en próximas corridas.")

        print(f"✅ [{self.label}] {len(resultados)} operaciones recolectadas.")
        return resultados

    # ------------------------------------------------------------------
    # Paso 1: descargar y leer el índice XML del año.
    # ------------------------------------------------------------------
    def _download_index(self, year: int) -> List[dict]:
        url = INDEX_ZIP_URL.format(year=year)
        print(f"   • Descargando índice: {url}")
        zip_bytes = httpclient.download_bytes(url)
        return parse_index_xml_from_zip(zip_bytes)

    # ------------------------------------------------------------------
    # Paso 2: para un PTR, bajar el PDF y extraer sus transacciones.
    # ------------------------------------------------------------------
    def _process_ptr(self, filing: dict, year: int) -> List[Disclosure]:
        doc_id = filing["doc_id"]
        pdf_url = PTR_PDF_URL.format(year=year, doc=doc_id)

        # Campos del legislador, comunes a todas las transacciones del PDF.
        comunes = dict(
            source="house",
            chamber="House",
            doc_id=doc_id,
            source_url=pdf_url,
            filer_name=filing["filer_name"],
            filer_state=filing["filer_state"],
            filing_type="PTR",
            filing_date=filing["filing_date"],
            # El XML no marca enmiendas de forma fiable; el parser puede
            # detectar "amendment" en el texto del PDF (mejora futura).
            is_amendment=filing.get("is_amendment", False),
        )

        # Si el usuario apagó el parseo de PDF, registramos solo la presentación.
        if not self.settings.get("parse_pdf_transactions", True):
            return [Disclosure(**comunes,
                               asset_description="(transacciones no parseadas)")]

        try:
            pdf_bytes = httpclient.download_bytes(pdf_url)
        except Exception as e:   # noqa: BLE001
            print(f"     ⚠️  No pude bajar el PDF {doc_id}: {e}")
            return [Disclosure(**comunes, asset_description="(PDF no disponible)")]

        transacciones = parse_ptr_pdf(pdf_bytes)
        if not transacciones:
            # PDF escaneado o ilegible: igual registramos la presentación.
            return [Disclosure(**comunes,
                               asset_description="(PDF no parseable / escaneado)")]

        # Completar cada transacción parseada con los datos del legislador.
        for t in transacciones:
            t.source = comunes["source"]
            t.chamber = comunes["chamber"]
            t.doc_id = comunes["doc_id"]
            t.source_url = comunes["source_url"]
            t.filer_name = comunes["filer_name"]
            t.filer_state = comunes["filer_state"]
            t.filing_type = comunes["filing_type"]
            t.filing_date = comunes["filing_date"]
        return transacciones


# ----------------------------------------------------------------------
# Función pública y REUTILIZABLE para leer el XML.
# La dejamos fuera de la clase para poder probarla sola (ver --self-test).
# ----------------------------------------------------------------------
def parse_index_xml_from_zip(zip_bytes: bytes) -> List[dict]:
    """Abre el ZIP en memoria, encuentra el .xml y lo parsea."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        nombre_xml = next((n for n in zf.namelist()
                           if n.lower().endswith(".xml")), None)
        if not nombre_xml:
            raise ValueError("El ZIP del índice no contiene un .xml")
        xml_bytes = zf.read(nombre_xml)
    return parse_index_xml(xml_bytes)


def parse_index_xml(xml_bytes: bytes) -> List[dict]:
    """
    Convierte el XML del índice en una lista de diccionarios sencillos.

    Es tolerante: si a una entrada le falta un campo, usa un valor por defecto
    en lugar de fallar.
    """
    root = ET.fromstring(xml_bytes)
    salida: List[dict] = []
    # Cada presentación es un elemento <Member> dentro del root.
    for m in root.iter("Member"):
        first = _text(m, "First")
        last = _text(m, "Last")
        salida.append({
            "doc_id": _text(m, "DocID"),
            "filing_type": _text(m, "FilingType"),
            "filer_name": f"{first} {last}".strip(),
            "filer_state": _text(m, "StateDst"),
            "filing_date": _parse_us_date(_text(m, "FilingDate")),
            "year": _text(m, "Year"),
            "is_amendment": False,
        })
    return salida


def _text(elem: ET.Element, tag: str) -> str:
    """Lee el texto de un sub-elemento; '' si no existe."""
    child = elem.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _parse_us_date(texto: str) -> Optional[date]:
    """La Cámara usa 'M/D/YYYY' en FilingDate."""
    for fmt in ("%m/%d/%Y", "%-m/%-d/%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None
