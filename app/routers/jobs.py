"""
Router para gestión y monitoreo de jobs en la cola.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from ..services.queue_svc import QueueService
import os
import logging

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)

# Instancia global del servicio de cola
queue = QueueService()


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
        ".webp": "image/webp"
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
