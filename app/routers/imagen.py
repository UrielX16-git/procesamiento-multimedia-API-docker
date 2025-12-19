"""
Router para endpoints relacionados con procesamiento de imágenes.
"""
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import uuid
import logging
from ..services import ffmpeg_svc
from ..services.queue_svc import QueueService

router = APIRouter(prefix="/imagen", tags=["Imagen"])
logger = logging.getLogger(__name__)

UPLOADS_DIR = "/disk/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Instancia del servicio de cola
queue = QueueService()


@router.post("/captura")
async def capture_frame(
    file: UploadFile = File(...),
    tiempo: str = Form(..., description="Tiempo del frame en formato HH:MM:SS"),
    calidad: int = Form(85, description="Calidad WebP (0-100, default: 85)")
):
    """
    Captura un frame de un video en un tiempo específico (ASÍNCRONO).
    
    Args:
        file: Archivo de video
        tiempo: Tiempo del frame en formato HH:MM:SS (ejemplo: 00:01:30)
        calidad: Calidad de compresión WebP (0-100, mayor = mejor calidad)
    
    Returns:
        JSON con job_id para consultar estado y descargar imagen WebP
    """
    logger.info(f"[ENDPOINT] POST /imagen/captura - Archivo: {file.filename}, tiempo: {tiempo}, calidad: {calidad}")
    
    # Guardar archivo y calcular tamaño
    file_size_mb = 0
    upload_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4()}_{file.filename}")
    
    with open(upload_path, "wb") as buffer:
        chunk_size = 8 * 1024 * 1024  # 8MB chunks
        while chunk := await file.read(chunk_size):
            buffer.write(chunk)
            file_size_mb += len(chunk) / (1024 * 1024)
    
    logger.info(f"[ENDPOINT] Archivo guardado: {file_size_mb:.2f} MB")
    
    # Crear job con PRIORIDAD ALTA (operación rápida)
    job_id = queue.create_job(
        job_type="capture_frame",
        input_file=upload_path,
        original_filename=file.filename,
        file_size_mb=file_size_mb,
        parameters={"timestamp": tiempo, "quality": calidad},
        priority=QueueService.PRIORITY_HIGH  # Prioridad ALTA
    )
    
    logger.info(f"[ENDPOINT] Job creado: {job_id} - Prioridad ALTA")
    
    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "message": "Job agregado a la cola con prioridad ALTA",
        "status_url": f"/jobs/status/{job_id}",
        "download_url": f"/jobs/download/{job_id}",
        "file_size_mb": round(file_size_mb, 2),
        "priority": "high",
        "estimated_time": "1-2 segundos una vez iniciado el procesamiento"
    })
