# app/services/cfdi/cfdi_service.py
from typing import Tuple
import io
import zipfile

from sqlalchemy.orm import Session

from app.models.cfdi_model_sat import CFDI
from app.schemas.cfdi_schemes import (
    CFDICreate,
    CFDIBatchItem,
    CFDIBatchResponse,
)
from app.services.cfdi.parser_cfdi import parse_cfdi_xml


def create_or_get_cfdi_from_xml(
    db: Session,
    xml_content: bytes | str,
) -> Tuple[CFDI, bool]:
    """
    Procesa un XML CFDI:
    - Lo parsea
    - Si existe el UUID en BD, devuelve el existente y created=False
    - Si no existe, lo crea y devuelve created=True
    """
    cfdi_data: CFDICreate = parse_cfdi_xml(xml_content)

    # Buscar existente por UUID
    existente = db.query(CFDI).filter(CFDI.uuid == cfdi_data.uuid).first()
    if existente:
        return existente, False

    nuevo_cfdi = CFDI(**cfdi_data.dict())
    db.add(nuevo_cfdi)
    db.flush()  # para que tenga ID antes del commit si se requiere

    return nuevo_cfdi, True


def process_cfdi_zip(
    db: Session,
    zip_bytes: bytes,
) -> CFDIBatchResponse:
    """
    Procesa un ZIP con múltiples XML de CFDI.
    - Solo toma archivos .xml
    - Lleva conteo de creados, duplicados, errores, etc.
    """
    bytes_io = io.BytesIO(zip_bytes)

    try:
        zf = zipfile.ZipFile(bytes_io)
    except zipfile.BadZipFile as e:
        raise ValueError(f"El archivo no es un ZIP válido: {e}")

    total_files = 0
    processed = 0
    created = 0
    duplicates = 0
    failed = 0
    skipped = 0

    items: list[CFDIBatchItem] = []

    # Recorremos entradas del ZIP
    for name in zf.namelist():
        # ignorar directorios
        if name.endswith("/"):
            continue

        total_files += 1

        if not name.lower().endswith(".xml"):
            skipped += 1
            items.append(
                CFDIBatchItem(
                    filename=name,
                    status="skipped",
                    error="No es un archivo XML",
                )
            )
            continue

        try:
            xml_content = zf.read(name)
        except Exception as e:
            failed += 1
            items.append(
                CFDIBatchItem(
                    filename=name,
                    status="error",
                    error=f"Error al leer del ZIP: {e}",
                )
            )
            continue

        try:
            cfdi_obj, is_created = create_or_get_cfdi_from_xml(db, xml_content)
            processed += 1

            if is_created:
                created += 1
                items.append(
                    CFDIBatchItem(
                        filename=name,
                        uuid=cfdi_obj.uuid,
                        status="created",
                    )
                )
            else:
                duplicates += 1
                items.append(
                    CFDIBatchItem(
                        filename=name,
                        uuid=cfdi_obj.uuid,
                        status="duplicate",
                        error="UUID ya registrado",
                    )
                )
        except Exception as e:
            failed += 1
            items.append(
                CFDIBatchItem(
                    filename=name,
                    status="error",
                    error=str(e),
                )
            )

    # Commit al final para todo el lote
    db.commit()

    return CFDIBatchResponse(
        total_files=total_files,
        processed=processed,
        created=created,
        duplicates=duplicates,
        failed=failed,
        skipped=skipped,
        items=items,
    )
