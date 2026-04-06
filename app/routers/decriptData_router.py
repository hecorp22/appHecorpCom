from fastapi import APIRouter, UploadFile, File, HTTPException
import hashlib
import tempfile
import os
from typing import Any, Dict

import magic
import exiftool
from PIL import Image
from io import BytesIO

router = APIRouter(prefix="/metadatos", tags=["metadatos"])

@router.post("/", summary="Extrae metadatos y hash de un archivo")
async def extraer_metadatos(file: UploadFile = File(...)) -> Dict[str, Any]:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"Error guardando archivo temporal: {e}")

    try:
        sha256 = hashlib.sha256()
        size = 0
        with open(tmp_path, "rb") as f:
            for bloque in iter(lambda: f.read(4096), b""):
                sha256.update(bloque)
                size += len(bloque)
        hash_hex = sha256.hexdigest()
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=f"Error calculando hash: {e}")

    try:
        mime = magic.from_file(tmp_path, mime=True)
    except Exception:
        mime = "unknown/unknown"

    # Extraer metadatos
    metadata: Dict[str, Any] = {}
    try:
        with exiftool.ExifTool() as et:
            metadata = et.get_metadata(tmp_path) or {}
    except Exception:
        metadata = {}

    # Si no hay metadatos de ExifTool, usar Pillow
    if not metadata:
        try:
            with open(tmp_path, "rb") as f:
                img = Image.open(f)
                metadata = {
                    "image_width": img.width,
                    "image_height": img.height,
                    "megapixels": round((img.width * img.height) / 1_000_000, 3),
                    "color_components": len(img.getbands()),
                    "format": img.format,
                    "mode": img.mode
                }
        except Exception:
            metadata = {"note": "No se pudo extraer metadata"}

    try:
        os.remove(tmp_path)
    except Exception:
        pass

    return {
        "filename": file.filename,
        "mime": mime,
        "size_bytes": size,
        "sha256": hash_hex,
        "metadata": metadata
    }
