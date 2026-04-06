# app/facturacion/parser_cfdi.py
from datetime import datetime
from typing import Dict, Any
import xml.etree.ElementTree as ET

from ...schemas.cfdi_schemes import CFDICreate, CFDIRead, CFDIBatchItem, CFDIBatchResponse
# Namespaces típicos del SAT
NS = {
    "cfdi": "http://www.sat.gob.mx/cfd/4",
    "cfdi33": "http://www.sat.gob.mx/cfd/3",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
}

def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    # SAT: '2021-01-16T10:43:27'
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def parse_cfdi_xml(xml_content: bytes | str) -> CFDICreate:
    """
    Lee un XML CFDI (SAT) y regresa un CFDICreate listo para guardarse.
    Soporta CFDI 3.3 y 4.0 (asumiendo namespaces estándar).
    """
    if isinstance(xml_content, bytes):
        xml_str = xml_content.decode("utf-8", errors="ignore")
    else:
        xml_str = xml_content

    root = ET.fromstring(xml_str)

    # Detectar namespace principal (3.3 o 4.0)
    tag = root.tag  # algo como '{http://www.sat.gob.mx/cfd/4}Comprobante'
    if "cfd/4" in tag:
        ns_cfdi = "cfdi"
    else:
        ns_cfdi = "cfdi33"

    # Comprobante
    version = root.attrib.get("Version") or root.attrib.get("version")
    serie = root.attrib.get("Serie") or root.attrib.get("serie")
    folio = root.attrib.get("Folio") or root.attrib.get("folio")
    fecha = _parse_datetime(root.attrib.get("Fecha") or root.attrib.get("fecha"))

    forma_pago = root.attrib.get("FormaPago") or root.attrib.get("formaPago")
    metodo_pago = root.attrib.get("MetodoPago") or root.attrib.get("metodoPago")
    moneda = root.attrib.get("Moneda") or root.attrib.get("moneda")
    tipo_comprobante = root.attrib.get("TipoDeComprobante") or root.attrib.get("tipoDeComprobante")
    lugar_expedicion = root.attrib.get("LugarExpedicion") or root.attrib.get("lugarExpedicion")

    subtotal = root.attrib.get("SubTotal") or root.attrib.get("subTotal")
    descuento = root.attrib.get("Descuento") or root.attrib.get("descuento")
    total = root.attrib.get("Total") or root.attrib.get("total")

    subtotal_f = float(subtotal) if subtotal is not None else None
    descuento_f = float(descuento) if descuento is not None else None
    total_f = float(total) if total is not None else None

    # Emisor
    emisor = root.find(f".//{{{NS[ns_cfdi]}}}Emisor")
    emisor_rfc = emisor.attrib.get("Rfc") if emisor is not None else None
    emisor_nombre = emisor.attrib.get("Nombre") if emisor is not None else None
    emisor_regimen_fiscal = emisor.attrib.get("RegimenFiscal") if emisor is not None else None

    # Receptor
    receptor = root.find(f".//{{{NS[ns_cfdi]}}}Receptor")
    receptor_rfc = receptor.attrib.get("Rfc") if receptor is not None else None
    receptor_nombre = receptor.attrib.get("Nombre") if receptor is not None else None
    receptor_uso_cfdi = receptor.attrib.get("UsoCFDI") if receptor is not None else None

    # Timbre Fiscal Digital
    # TFD casi siempre va en Complemento
    tfd = root.find(f".//{{{NS['tfd']}}}TimbreFiscalDigital")
    if tfd is None:
        raise ValueError("No se encontró el TimbreFiscalDigital en el XML (no es un CFDI timbrado).")

    uuid = tfd.attrib.get("UUID")
    fecha_timbrado = _parse_datetime(tfd.attrib.get("FechaTimbrado"))
    sello_cfd = tfd.attrib.get("SelloCFD")
    sello_sat = tfd.attrib.get("SelloSAT")
    no_certificado_sat = tfd.attrib.get("NoCertificadoSAT")

    if not uuid:
        raise ValueError("El XML CFDI no contiene UUID.")

    data: Dict[str, Any] = {
        "version": version,
        "serie": serie,
        "folio": folio,
        "fecha": fecha,
        "forma_pago": forma_pago,
        "metodo_pago": metodo_pago,
        "moneda": moneda,
        "tipo_comprobante": tipo_comprobante,
        "lugar_expedicion": lugar_expedicion,
        "subtotal": subtotal_f,
        "descuento": descuento_f,
        "total": total_f,
        "emisor_rfc": emisor_rfc,
        "emisor_nombre": emisor_nombre,
        "emisor_regimen_fiscal": emisor_regimen_fiscal,
        "receptor_rfc": receptor_rfc,
        "receptor_nombre": receptor_nombre,
        "receptor_uso_cfdi": receptor_uso_cfdi,
        "uuid": uuid,
        "fecha_timbrado": fecha_timbrado,
        "sello_cfd": sello_cfd,
        "sello_sat": sello_sat,
        "no_certificado_sat": no_certificado_sat,
        "xml_raw": xml_str,
        "estado": "ACTIVO",
    }

    return CFDICreate(**data)
