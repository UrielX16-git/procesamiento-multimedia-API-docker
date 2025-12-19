"""
Router para endpoints relacionados con procesamiento de audio.
"""
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List
import os
import uuid
import logging
from ..services import ffmpeg_svc
from ..services.queue_svc import QueueService

router = APIRouter(prefix="/audio", tags=["Audio"])
logger = logging.getLogger(__name__)

UPLOADS_DIR = "/disk/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Instancia del servicio de cola
queue = QueueService()


@router.post("/cortar")
async def cut_audio(
    file: UploadFile = File(...),
    inicio: str = Form(..., description="Tiempo de inicio (HH:MM:SS)"),
    fin: str = Form(..., description="Tiempo de fin (HH:MM:SS)")
):
    """
    Recorta un archivo de audio entre dos timestamps (ASÍNCRONO).
    
    Args:
        file: Archivo de audio a recortar
        inicio: Tiempo de inicio en formato HH:MM:SS
        fin: Tiempo de fin en formato HH:MM:SS
    
    Returns:
        JSON con job_id para consultar estado y descargar audio recortado
    """
    logger.info(f"[ENDPOINT] POST /audio/cortar - Archivo: {file.filename}, inicio: {inicio}, fin: {fin}")
    
    # Guardar archivo y calcular tamaño
    file_size_mb = 0
    upload_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4()}_{file.filename}")
    
    with open(upload_path, "wb") as buffer:
        chunk_size = 8 * 1024 * 1024  # 8MB chunks
        while chunk := await file.read(chunk_size):
            buffer.write(chunk)
            file_size_mb += len(chunk) / (1024 * 1024)
    
    logger.info(f"[ENDPOINT] Archivo guardado: {file_size_mb:.2f} MB")
    
    # Crear job con PRIORIDAD NORMAL
    job_id = queue.create_job(
        job_type="cut_audio",
        input_file=upload_path,
        original_filename=file.filename,
        file_size_mb=file_size_mb,
        parameters={"start_time": inicio, "end_time": fin},
        priority=QueueService.PRIORITY_NORMAL
    )
    
    logger.info(f"[ENDPOINT] Job creado: {job_id} - Prioridad NORMAL")
    
    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "message": "Job agregado a la cola con prioridad NORMAL",
        "status_url": f"/jobs/status/{job_id}",
        "download_url": f"/jobs/download/{job_id}",
        "file_size_mb": round(file_size_mb, 2),
        "priority": "normal",
        "estimated_time": "1-10 segundos una vez iniciado el procesamiento"
    })


@router.post("/unir")
async def join_audios(
    files: List[UploadFile] = File(..., description="Lista de archivos de audio a unir")
):
    """
    Une múltiples archivos de audio en uno solo (ASÍNCRONO).
    
    Args:
        files: Lista de archivos de audio (mínimo 2)
    
    Returns:
        JSON con job_id para consultar estado y descargar audio concatenado
    """
    logger.info(f"[ENDPOINT] POST /audio/unir - Número de archivos: {len(files)}")
    
    if len(files) < 2:
        logger.warning(f"[ENDPOINT] Se requieren mínimo 2 archivos, recibidos: {len(files)}")
        return JSONResponse(
            status_code=400,
            content={"error": "Se requieren al menos 2 archivos para unir"}
        )
    
    # Guardar todos los archivos y calcular tamaño total
    input_paths = []
    total_size_mb = 0
    
    for i, file in enumerate(files, 1):
        logger.info(f"[ENDPOINT] Guardando archivo {i}/{len(files)}: {file.filename}")
        file_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4()}_{file.filename}")
        
        file_size_mb = 0
        with open(file_path, "wb") as buffer:
            chunk_size = 8 * 1024 * 1024  # 8MB chunks
            while chunk := await file.read(chunk_size):
                buffer.write(chunk)
                file_size_mb += len(chunk) / (1024 * 1024)
        
        input_paths.append(file_path)
        total_size_mb += file_size_mb
    
    logger.info(f"[ENDPOINT] Archivos guardados: {total_size_mb:.2f} MB total")
    
    # Crear job con PRIORIDAD NORMAL
    job_id = queue.create_job(
        job_type="concat_audios",
        input_file=input_paths[0],  # Primer archivo como referencia
        original_filename=f"merged_{len(files)}_audios.mp3",
        file_size_mb=total_size_mb,
        parameters={"input_files": input_paths},
        priority=QueueService.PRIORITY_NORMAL
    )
    
    logger.info(f"[ENDPOINT] Job creado: {job_id} - Prioridad NORMAL")
    
    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "message": "Job agregado a la cola con prioridad NORMAL",
        "status_url": f"/jobs/status/{job_id}",
        "download_url": f"/jobs/download/{job_id}",
        "file_size_mb": round(total_size_mb, 2),
        "files_count": len(files),
        "priority": "normal",
        "estimated_time": "5-30 segundos una vez iniciado el procesamiento"
    })
