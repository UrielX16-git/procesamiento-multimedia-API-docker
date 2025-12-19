"""
API REST para procesamiento de archivos multimedia usando FFmpeg.
Arquitectura de "conmutador ligero" que procesa bajo demanda.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import video, audio, imagen, jobs, uploads
import os
import logging

# Configurar logging para que se vea en Docker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Crear directorio temporal si no existe
TEMP_DIR = "/tmp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

logger.info("=" * 60)
logger.info("Iniciando API de Procesamiento Multimedia con Cola")
logger.info(f"Directorio temporal: {TEMP_DIR}")
logger.info("Sistema de cola: Valkey + Worker asíncrono")
logger.info("=" * 60)

# Inicializar FastAPI
app = FastAPI(
    title="API de Procesamiento Multimedia",
    description="API REST para procesamiento de video y audio usando FFmpeg con sistema de cola",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(uploads.router)  # NUEVO: upload en 2 pasos
app.include_router(jobs.router)
app.include_router(video.router)
app.include_router(audio.router)
app.include_router(imagen.router)


@app.get("/")
async def root():
    """Endpoint raíz con información de la API."""
    logger.info("Solicitud recibida en endpoint raiz /")
    return {
        "message": "API de Procesamiento Multimedia con Cola",
        "version": "2.0.0",
        "status": "online",
        "features": {
            "queue_system": "Valkey + Worker asíncrono",
            "priority_queue": "Habilitado (high/normal/low)",
            "auto_cleanup": "Archivos procesados limpios automáticamente (TTL: 3 horas)",
            "cleanup_frequency": "Cada 1 hora",
            "async_processing": "Sistema de upload en 2 pasos con respuesta instantánea",
            "upload_ttl": "3 horas para uploads sin usar",
            "file_reuse": "Un archivo puede usarse para múltiples jobs"
        },
        "workflow": {
            "1_upload": "POST /upload → {upload_id} (respuesta instantánea)",
            "2_create_job": "POST /jobs/create → {job_id} (respuesta instantánea)",
            "3_check_status": "GET /jobs/status/{job_id} → polling cada 5s",
            "4_download": "GET /jobs/download/{job_id} → descargar resultado"
        },
        "endpoints": {
            "upload": {
                "/upload": "[POST] Subir archivo (retorna upload_id instantáneo)",
                "/upload/{upload_id}": "[GET] Info del upload",
                "/uploads": "[GET] Listar uploads activos",
                "/upload/{upload_id}": "[DELETE] Eliminar upload (si ref_count=0)"
            },
            "video": {
                "/video/detalles": "[ASÍNCRONO] Extraer metadatos de video (Prioridad: ALTA)",
                "/video/extraer-audio": "[ASÍNCRONO] Extraer audio a MP3 (Prioridad: NORMAL)",
                "/video/comprimir": "[ASÍNCRONO] Comprimir video (Prioridad: BAJA)",
                "/video/convertir-mp4": "[ASÍNCRONO] Convertir a MP4 (Prioridad: BAJA)"
            },
            "audio": {
                "/audio/cortar": "[ASÍNCRONO] Recortar audio (Prioridad: NORMAL)",
                "/audio/unir": "[ASÍNCRONO] Unir múltiples audios (Prioridad: NORMAL)"
            },
            "imagen": {
                "/imagen/captura": "[ASÍNCRONO] Capturar frame (Prioridad: ALTA)"
            },
            "jobs": {
                "/jobs/status/{job_id}": "Consultar estado de un job",
                "/jobs/queue": "Ver cola de jobs pendientes",
                "/jobs/download/{job_id}": "Descargar resultado de job completado",
                "/jobs/{job_id}": "Cancelar job pendiente (DELETE)",
                "/jobs/stats": "Estadísticas de la cola"
            },
            "utilidades": {
                "/reset": "Limpiar archivos temporales manualmente (DELETE)",
                "/health": "Estado de salud de la API"
            }
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Endpoint de salud para monitoreo."""
    logger.debug("Health check solicitado")
    return {"status": "healthy"}


@app.delete("/reset")
async def reset_temp_files():
    """
    Limpia manualmente TODOS los archivos temporales (uploads, results, temp) inmediatamente.
    Ignora los TTL configurados.
    
    Returns:
        JSON con estadísticas de limpieza
    """
    import shutil
    from .services.cleanup_svc import cleanup_old_files, cleanup_old_uploads
    
    stats = {
        "temp": {"files": 0, "space_mb": 0},
        "results": {"files": 0, "space_mb": 0},
        "uploads": {"files": 0, "space_mb": 0}
    }
    
    # 1. Limpiar carpeta temporal local
    if os.path.exists(TEMP_DIR):
        try:
            temp_files = 0
            temp_space = 0
            for filename in os.listdir(TEMP_DIR):
                filepath = os.path.join(TEMP_DIR, filename)
                try:
                    if os.path.isfile(filepath):
                        temp_space += os.path.getsize(filepath)
                        os.remove(filepath)
                        temp_files += 1
                    elif os.path.isdir(filepath):
                        shutil.rmtree(filepath)
                except Exception as e:
                    logger.error(f"Error borrando {filepath}: {e}")
            
            stats["temp"]["files"] = temp_files
            stats["temp"]["space_mb"] = round(temp_space / (1024 * 1024), 2)
        except Exception as e:
            logger.error(f"Error limpando temp: {e}")

    # 2. Forzar limpieza de Results (TTL=0)
    try:
        results_clean = cleanup_old_files(ttl_hours=0)
        stats["results"]["files"] = results_clean.get("files_deleted", 0)
        stats["results"]["space_mb"] = results_clean.get("space_freed_mb", 0)
    except Exception as e:
        logger.error(f"Error forzando limpieza results: {e}")

    # 3. Forzar limpieza de Uploads (TTL=0)
    try:
        uploads_clean = cleanup_old_uploads(ttl_hours=0)
        stats["uploads"]["files"] = uploads_clean.get("files_deleted", 0)
        stats["uploads"]["space_mb"] = uploads_clean.get("space_freed_mb", 0)
    except Exception as e:
        logger.error(f"Error forzando limpieza uploads: {e}")
    
    total_files = stats["temp"]["files"] + stats["results"]["files"] + stats["uploads"]["files"]
    total_space = stats["temp"]["space_mb"] + stats["results"]["space_mb"] + stats["uploads"]["space_mb"]

    return {
        "status": "success",
        "message": "Limpieza forzada completada",
        "timestamp": os.getenv("last_reset_time"),
        "summary": {
            "total_files_deleted": total_files,
            "total_space_freed_mb": round(total_space, 2)
        },
        "details": stats
    }
