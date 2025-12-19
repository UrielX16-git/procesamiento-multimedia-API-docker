"""
Router para gestión de uploads.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
import logging
from ..services.upload_svc import UploadService

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = logging.getLogger(__name__)

UPLOADS_DIR = "/disk/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Instancia del servicio de uploads
upload_svc = UploadService()


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """
    Sube un archivo y retorna upload_id INSTANTÁNEAMENTE.
    
    El archivo queda disponible para crear múltiples jobs.
    Este endpoint retorna inmediatamente sin esperar a que termine el upload.
    
    Returns:
        JSON con upload_id y información del archivo
    """
    logger.info(f"[ENDPOINT] POST /upload - Iniciando upload: {file.filename}")
    
    # Generar upload_id
    upload_id = str(uuid.uuid4())
    filename = file.filename
    file_path = os.path.join(UPLOADS_DIR, f"{upload_id}_{filename}")
    
    # Guardar archivo en chunks (streaming)
    file_size_mb = 0
    with open(file_path, "wb") as buffer:
        chunk_size = 8 * 1024 * 1024  # 8MB chunks
        while chunk := await file.read(chunk_size):
            buffer.write(chunk)
            file_size_mb += len(chunk) / (1024 * 1024)
    
    logger.info(f"[ENDPOINT] Archivo guardado: {file_size_mb:.2f} MB")
    
    # Crear registro de upload
    upload_svc.create_upload(filename, file_path, file_size_mb, upload_id=upload_id)
    
    logger.info(f"[ENDPOINT] Upload creado: {upload_id}")
    
    return JSONResponse({
        "upload_id": upload_id,
        "filename": filename,
        "file_size_mb": round(file_size_mb, 2),
        "status": "ready",
        "message": "Archivo subido exitosamente. Usa este upload_id para crear jobs",
        "create_job_url": "/jobs/create"
    })


@router.get("/{upload_id}")
async def get_upload_info(upload_id: str):
    """
    Obtiene información de un upload.
    
    Args:
        upload_id: ID del upload
        
    Returns:
        JSON con datos del upload
    """
    logger.info(f"[ENDPOINT] GET /upload/{upload_id}")
    
    upload_data = upload_svc.get_upload(upload_id)
    if not upload_data:
        raise HTTPException(status_code=404, detail="Upload no encontrado")
    
    return upload_data


@router.get("s")
async def list_uploads():
    """
    Lista uploads activos.
    
    Returns:
        Lista de uploads ordenados por fecha
    """
    logger.info("[ENDPOINT] GET /uploads")
    
    uploads = upload_svc.list_uploads(limit=100)
    
    return {
        "uploads": uploads,
        "total": len(uploads)
    }


@router.delete("/{upload_id}")
async def delete_upload(upload_id: str):
    """
    Elimina un upload manualmente (solo si ref_count = 0).
    
    Args:
        upload_id: ID del upload a eliminar
        
    Returns:
        JSON confirmando eliminación
    """
    logger.info(f"[ENDPOINT] DELETE /upload/{upload_id}")
    
    upload_data = upload_svc.get_upload(upload_id)
    if not upload_data:
        raise HTTPException(status_code=404, detail="Upload no encontrado")
    
    if upload_data["ref_count"] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {upload_data['ref_count']} jobs activos usando este archivo"
        )
    
    success = upload_svc.delete_upload_manual(upload_id)
    
    if success:
        return {"message": "Upload eliminado exitosamente", "upload_id": upload_id}
    else:
        raise HTTPException(status_code=500, detail="No se pudo eliminar el upload")
