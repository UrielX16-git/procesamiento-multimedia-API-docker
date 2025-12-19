"""
Router para gestión de jobs (cola de procesamiento).
"""
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
import os
import json
import logging
from ..services.queue_svc import QueueService
from ..services.upload_svc import UploadService

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)

# Instancia de servicios
queue = QueueService()
upload_svc = UploadService()


@router.post("/create")
async def create_job_from_upload(
    upload_id: str = Form(..., description="ID del archivo subido"),
    job_type: str = Form(..., description="Tipo de operación"),
    parameters: str = Form("{}", description="Parámetros adicionales en formato JSON")
):
    """
    Crea un job desde un archivo ya subido.
    
    Retorna INSTANTÁNEAMENTE con job_id.
    
    Tipos de job disponibles:
    - get_metadata: Extraer metadatos de video
    - extract_audio: Extraer audio a MP3
    - compress_video: Comprimir video (params: max_threads)
    - convert_mp4: Convertir a MP4 (params: max_threads)
    - cut_audio: Recortar audio (params: start_time, end_time)
    - concat_audios: Unir audios (params: upload_ids como lista)
    - capture_frame: Capturar frame (params: timestamp, quality)
    
    Args:
        upload_id: ID del upload (obtenido de POST /upload)
        job_type: Tipo de operación
        parameters: JSON con parámetros específicos de la operación
        
    Returns:
        JSON con job_id para consultar estado y descargar
    """
    logger.info(f"[ENDPOINT] POST /jobs/create - upload_id: {upload_id}, job_type: {job_type}")
    
    # Validar upload existe
    upload_data = upload_svc.get_upload(upload_id)
    if not upload_data:
        raise HTTPException(status_code=404, detail="Upload no encontrado o expirado")
    
    # Parsear parámetros
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Parámetros inválidos (debe ser JSON válido)")
    
    # Mapa de prioridades según tipo de job
    priority_map = {
        "get_metadata": QueueService.PRIORITY_HIGH,
        "capture_frame": QueueService.PRIORITY_HIGH,
        "extract_audio": QueueService.PRIORITY_NORMAL,
        "cut_audio": QueueService.PRIORITY_NORMAL,
        "concat_audios": QueueService.PRIORITY_NORMAL,
        "compress_video": QueueService.PRIORITY_LOW,
        "convert_mp4": QueueService.PRIORITY_LOW
    }
    
    if job_type not in priority_map:
        raise HTTPException(
            status_code=400, 
            detail=f"Tipo de job inválido. Tipos válidos: {list(priority_map.keys())}"
        )
    
    priority = priority_map[job_type]
    
    # Crear job
    job_id = queue.create_job(
        job_type=job_type,
        upload_id=upload_id,
        input_file=upload_data["file_path"],
        original_filename=upload_data["filename"],
        file_size_mb=upload_data["file_size_mb"],
        parameters=params,
        priority=priority
    )
    
    priority_names = {
        QueueService.PRIORITY_HIGH: "high",
        QueueService.PRIORITY_NORMAL: "normal",
        QueueService.PRIORITY_LOW: "low"
    }
    
    logger.info(f"[ENDPOINT] Job creado: {job_id} (prioridad: {priority_names[priority]})")
    
    return JSONResponse({
        "job_id": job_id,
        "upload_id": upload_id,
        "job_type": job_type,
        "status": "pending",
        "priority": priority_names[priority],
        "message": f"Job creado con prioridad {priority_names[priority].upper()}",
        "status_url": f"/jobs/status/{job_id}",
        "download_url": f"/jobs/download/{job_id}"
    })


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Obtiene el estado actual de un job.
    
    Args:
        job_id: ID del job
        
    Returns:
        JSON con datos del job (id, status, progress, etc.)
    """
    logger.info(f"[ENDPOINT] GET /jobs/status/{job_id}")
    job_data = queue.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    
    return job_data


@router.get("/queue")
async def get_queue_info():
    """
    Obtiene información de la cola y lista de jobs pendientes.
    
    Returns:
        JSON con estadísticas y lista de jobs pendientes ordenados por prioridad
    """
    logger.info("[ENDPOINT] GET /jobs/queue")
    
    stats = queue.get_queue_stats()
    pending_jobs = queue.get_queue_jobs(limit=50)
    
    return {
        "stats": stats,
        "pending_jobs": pending_jobs,
        "total_pending": len(pending_jobs)
    }


@router.get("/download/{job_id}")
async def download_result(job_id: str):
    """
    Descarga el resultado de un job completado.
    
    Args:
        job_id: ID del job
        
    Returns:
        Archivo procesado
    """
    logger.info(f"[ENDPOINT] GET /jobs/download/{job_id}")
    job_data = queue.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            content={
                "error": f"Job no completado. Estado actual: {job_data['status']}",
                "status": job_data["status"],
                "progress": job_data.get("progress", 0)
            }
        )
    
    output_file = job_data["output_file"]
    
    if not os.path.exists(output_file):
        raise HTTPException(
            status_code=404, 
            detail="Archivo de resultado no encontrado o ya expiró (TTL: 3 horas)"
        )
    
    # Determinar tipo MIME según extensión
    media_types = {
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".webp": "image/webp",
        ".json": "application/json"
    }
    ext = os.path.splitext(output_file)[1]
    media_type = media_types.get(ext, "application/octet-stream")
    
    # Generar nombre de descarga basado en el archivo original
    original_filename = job_data['metadata']['original_filename']
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_filename = f"{base_name}{ext}"
    
    logger.info(f"[ENDPOINT] Enviando archivo: {output_file} ({media_type})")
    
    return FileResponse(
        output_file,
        media_type=media_type,
        filename=download_filename
    )


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancela un job pendiente en la cola.
    
    Args:
        job_id: ID del job a cancelar
        
    Returns:
        JSON con resultado de la operación
    """
    logger.info(f"[ENDPOINT] DELETE /jobs/{job_id}")
    job_data = queue.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    
    if job_data["status"] == "processing":
        raise HTTPException(
            status_code=400, 
            detail="No se puede cancelar un job que está en procesamiento"
        )
    
    if job_data["status"] in ["completed", "failed"]:
        return JSONResponse({
            "message": f"Job ya está {job_data['status']}",
            "status": job_data["status"]
        })
    
    # Intentar cancelar
    success = queue.cancel_job(job_id)
    
    if success:
        logger.info(f"[ENDPOINT] Job cancelado exitosamente: {job_id}")
        return {"message": "Job cancelado exitosamente", "job_id": job_id}
    else:
        raise HTTPException(status_code=500, detail="No se pudo cancelar el job")


@router.get("/stats")
async def get_stats():
    """
    Obtiene estadísticas generales de la cola.
    
    Returns:
        JSON con contadores de jobs por estado
    """
    logger.info("[ENDPOINT] GET /jobs/stats")
    stats = queue.get_queue_stats()
    
    return {
        "queue": {
            "pending": stats["pending"],
            "processing": stats["processing"]
        },
        "completed": {
            "last_3_hours": stats["completed_3h"]
        },
        "failed": {
            "last_7_days": stats["failed_7d"]
        },
        "total_active": stats["pending"] + stats["processing"]
    }
