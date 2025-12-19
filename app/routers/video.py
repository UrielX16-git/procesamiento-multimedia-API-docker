"""
Router para endpoints relacionados con procesamiento de video.
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uuid
import logging
from ..services import ffmpeg_svc
from ..services.queue_svc import QueueService

router = APIRouter(prefix="/video", tags=["Video"])
logger = logging.getLogger(__name__)

TEMP_DIR = "/tmp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

# Directorio para archivos grandes que van a cola
UPLOADS_DIR = "/disk/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Instancia del servicio de cola
queue = QueueService()


def save_upload(file: UploadFile) -> str:
    """Guarda un archivo subido con nombre único."""
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(TEMP_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return filepath


def cleanup_file(filepath: str):
    """Elimina un archivo si existe."""
    if os.path.exists(filepath):
        os.remove(filepath)


@router.post("/detalles")
async def video_details(
    file: UploadFile = File(...)
):
    """
    Extrae metadatos de un archivo de video de forma ASÍNCRONA.
    
    Returns:
        JSON con job_id para consultar estado y descargar metadatos
    """
    logger.info(f"[ENDPOINT] POST /video/detalles - Archivo: {file.filename}")
    
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
        job_type="get_metadata",
        input_file=upload_path,
        original_filename=file.filename,
        file_size_mb=file_size_mb,
        parameters={},
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
        "estimated_time": "2-5 segundos una vez iniciado el procesamiento"
    })


@router.post("/extraer-audio")
async def extract_audio(
    file: UploadFile = File(...)
):
    """
    Extrae el audio de un video y lo convierte a MP3 de forma ASÍNCRONA.
    
    Returns:
        JSON con job_id para consultar estado y descargar audio MP3
    """
    logger.info(f"[ENDPOINT] POST /video/extraer-audio - Archivo: {file.filename}")
    
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
        job_type="extract_audio",
        input_file=upload_path,
        original_filename=file.filename,
        file_size_mb=file_size_mb,
        parameters={"quality": 2},
        priority=QueueService.PRIORITY_NORMAL  # Prioridad NORMAL
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
        "estimated_time": "10-60 segundos una vez iniciado el procesamiento"
    })


@router.post("/comprimir")
async def compress_video(
    file: UploadFile = File(...),
    max_threads: int = Form(4)
):
    """
    Comprime un video para reducir su tamaño de forma optimizada (ASÍNCRONO).
    
    Todos los archivos van a la cola con PRIORIDAD BAJA (operación pesada).
    
    Args:
        file: Archivo de video a comprimir
        max_threads: Número máximo de threads (default: 4, 0=auto detectar todos los hilos)
    
    Returns:
        JSON con job_id para consultar estado y descargar video comprimido
    """
    logger.info(f"[ENDPOINT] POST /video/comprimir - Archivo: {file.filename}, max_threads: {max_threads}")
    
    # Guardar archivo y calcular tamaño
    file_size_mb = 0
    upload_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4()}_{file.filename}")
    
    with open(upload_path, "wb") as buffer:
        chunk_size = 8 * 1024 * 1024  # 8MB chunks
        while chunk := await file.read(chunk_size):
            buffer.write(chunk)
            file_size_mb += len(chunk) / (1024 * 1024)
    
    logger.info(f"[ENDPOINT] Archivo guardado: {file_size_mb:.2f} MB")
    
    # SIEMPRE usar cola con PRIORIDAD BAJA
    job_id = queue.create_job(
        job_type="compress_video",
        input_file=upload_path,
        original_filename=file.filename,
        file_size_mb=file_size_mb,
        parameters={"max_threads": max_threads},
        priority=QueueService.PRIORITY_LOW  # Prioridad BAJA
    )
    
    logger.info(f"[ENDPOINT] Job creado: {job_id} - Prioridad BAJA")
    
    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "message": "Job agregado a la cola con prioridad BAJA",
        "status_url": f"/jobs/status/{job_id}",
        "download_url": f"/jobs/download/{job_id}",
        "file_size_mb": round(file_size_mb, 2),
        "priority": "low",
        "estimated_time": "1-30 minutos dependiendo del tamaño"
    })


@router.post("/convertir-mp4")
async def convert_to_mp4(
    file: UploadFile = File(...),
    max_threads: int = Form(4)
):
    """
    Convierte un video de cualquier formato a MP4 de forma ultra-optimizada (ASÍNCRONO).
    
    Todos los archivos van a la cola con PRIORIDAD BAJA (operación pesada).
    
    ESTRATEGIA INTELIGENTE:
    - MKV/WEBM: Stream copy directo (INSTANTÁNEO - segundos) sin subtítulos
    - Otros formatos: Intenta stream copy, si falla re-codifica
    
    Args:
        file: Archivo de video a convertir
        max_threads: Número máximo de threads (default: 4, 0=auto detectar todos los hilos)
    
    Returns:
        JSON con job_id para consultar estado y descargar video MP4
    """
    logger.info(f"[ENDPOINT] POST /video/convertir-mp4 - Archivo: {file.filename}, max_threads: {max_threads}")
    
    # Guardar archivo y calcular tamaño
    file_size_mb = 0
    upload_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4()}_{file.filename}")
    
    with open(upload_path, "wb") as buffer:
        chunk_size = 8 * 1024 * 1024  # 8MB chunks
        while chunk := await file.read(chunk_size):
            buffer.write(chunk)
            file_size_mb += len(chunk) / (1024 * 1024)
    
    logger.info(f"[ENDPOINT] Archivo guardado: {file_size_mb:.2f} MB")
    
    # SIEMPRE usar cola con PRIORIDAD BAJA
    job_id = queue.create_job(
        job_type="convert_mp4",
        input_file=upload_path,
        original_filename=file.filename,
        file_size_mb=file_size_mb,
        parameters={"max_threads": max_threads},
        priority=QueueService.PRIORITY_LOW  # Prioridad BAJA
    )
    
    logger.info(f"[ENDPOINT] Job creado: {job_id} - Prioridad BAJA")
    
    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "message": "Job agregado a la cola con prioridad BAJA",
        "status_url": f"/jobs/status/{job_id}",
        "download_url": f"/jobs/download/{job_id}",
        "file_size_mb": round(file_size_mb, 2),
        "priority": "low",
        "estimated_time": "30 segundos - 10 minutos dependiendo del formato y tamaño"
    })

