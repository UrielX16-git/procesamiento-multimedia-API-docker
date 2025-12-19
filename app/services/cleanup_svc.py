"""
Servicio de limpieza automática de archivos procesados.
Elimina archivos en /disk/results con más de 3 horas de antigüedad.
"""
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

RESULTS_DIR = "/disk/results"
UPLOADS_DIR = "/disk/uploads"  # NUEVO
TTL_HOURS = 3  # Tiempo de vida de archivos procesados


def cleanup_old_uploads(ttl_hours: int = TTL_HOURS) -> dict:
    """
    Elimina archivos en /disk/uploads con más de 3 horas de antigüedad.
    
    Args:
        ttl_hours: Tiempo de vida en horas (default: 3)
        
    Returns:
        Diccionario con estadísticas de limpieza
    """
    if not os.path.exists(UPLOADS_DIR):
        logger.warning(f"[CLEANUP_UPLOADS] Directorio no existe: {UPLOADS_DIR}")
        return {
            "files_deleted": 0,
            "space_freed_mb": 0,
            "errors": 0
        }
    
    now = datetime.now()
    cutoff_time = now - timedelta(hours=ttl_hours)
    cutoff_timestamp = cutoff_time.timestamp()
    
    files_deleted = 0
    space_freed = 0
    errors = 0
    
    logger.info("=" * 80)
    logger.info(f"[CLEANUP_UPLOADS] Iniciando limpieza de uploads antiguos")
    logger.info(f"[CLEANUP_UPLOADS] Directorio: {UPLOADS_DIR}")
    logger.info(f"[CLEANUP_UPLOADS] TTL: {ttl_hours} horas")
    
    try:
        for filename in os.listdir(UPLOADS_DIR):
            filepath = os.path.join(UPLOADS_DIR, filename)
            
            # Solo procesar archivos, no directorios
            if not os.path.isfile(filepath):
                continue
            
            try:
                # Obtener timestamp de modificación del archivo
                file_mtime = os.path.getmtime(filepath)
                file_age_hours = (now.timestamp() - file_mtime) / 3600
                
                # Si el archivo tiene más de TTL_HOURS horas, eliminarlo
                if file_mtime < cutoff_timestamp:
                    file_size = os.path.getsize(filepath)
                    
                    logger.info(
                        f"[CLEANUP_UPLOADS] Eliminando: {filename} "
                        f"(antigüedad: {file_age_hours:.1f}h, tamaño: {file_size / (1024 * 1024):.2f}MB)"
                    )
                    
                    os.remove(filepath)
                    files_deleted += 1
                    space_freed += file_size
            
            except Exception as e:
                errors += 1
                logger.error(f"[CLEANUP_UPLOADS] Error procesando {filename}: {str(e)}")
    
    except Exception as e:
        logger.error(f"[CLEANUP_UPLOADS] Error al listar directorio {UPLOADS_DIR}: {str(e)}")
        errors += 1
    
    space_freed_mb = space_freed / (1024 * 1024)
    
    logger.info("=" * 80)
    logger.info(f"[CLEANUP_UPLOADS] Limpieza completada")
    logger.info(f"[CLEANUP_UPLOADS] Archivos eliminados: {files_deleted}")
    logger.info(f"[CLEANUP_UPLOADS] Espacio liberado: {space_freed_mb:.2f} MB")
    logger.info(f"[CLEANUP_UPLOADS] Errores: {errors}")
    logger.info("=" * 80)
    
    return {
        "files_deleted": files_deleted,
        "space_freed_mb": round(space_freed_mb, 2),
        "errors": errors
    }


def cleanup_old_files() -> dict:
    """
    Elimina archivos en /disk/results con más de 3 horas de antigüedad.
    
    Returns:
        Diccionario con estadísticas de limpieza
    """
    if not os.path.exists(RESULTS_DIR):
        logger.warning(f"[CLEANUP] Directorio no existe: {RESULTS_DIR}")
        return {
            "files_deleted": 0,
            "space_freed_mb": 0,
            "errors": 0
        }
    
    now = datetime.now()
    cutoff_time = now - timedelta(hours=TTL_HOURS)
    cutoff_timestamp = cutoff_time.timestamp()
    
    files_deleted = 0
    space_freed = 0
    errors = 0
    
    logger.info("=" * 80)
    logger.info(f"[CLEANUP] Iniciando limpieza de archivos antiguos")
    logger.info(f"[CLEANUP] Directorio: {RESULTS_DIR}")
    logger.info(f"[CLEANUP] TTL: {TTL_HOURS} horas")
    logger.info(f"[CLEANUP] Hora actual: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"[CLEANUP] Eliminando archivos anteriores a: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        for filename in os.listdir(RESULTS_DIR):
            filepath = os.path.join(RESULTS_DIR, filename)
            
            # Solo procesar archivos, no directorios
            if not os.path.isfile(filepath):
                continue
            
            try:
                # Obtener timestamp de modificación del archivo
                file_mtime = os.path.getmtime(filepath)
                file_age_hours = (now.timestamp() - file_mtime) / 3600
                
                # Si el archivo tiene más de TTL_HOURS horas, eliminarlo
                if file_mtime < cutoff_timestamp:
                    file_size = os.path.getsize(filepath)
                    
                    logger.info(
                        f"[CLEANUP] Eliminando: {filename} "
                        f"(antigüedad: {file_age_hours:.1f}h, tamaño: {file_size / (1024 * 1024):.2f}MB)"
                    )
                    
                    os.remove(filepath)
                    files_deleted += 1
                    space_freed += file_size
                else:
                    logger.debug(
                        f"[CLEANUP] Conservando: {filename} "
                        f"(antigüedad: {file_age_hours:.1f}h)"
                    )
            
            except Exception as e:
                errors += 1
                logger.error(f"[CLEANUP] Error procesando {filename}: {str(e)}")
    
    except Exception as e:
        logger.error(f"[CLEANUP] Error al listar directorio {RESULTS_DIR}: {str(e)}")
        errors += 1
    
    space_freed_mb = space_freed / (1024 * 1024)
    
    logger.info("=" * 80)
    logger.info(f"[CLEANUP] Limpieza completada")
    logger.info(f"[CLEANUP] Archivos eliminados: {files_deleted}")
    logger.info(f"[CLEANUP] Espacio liberado: {space_freed_mb:.2f} MB")
    logger.info(f"[CLEANUP] Errores: {errors}")
    logger.info("=" * 80)
    
    return {
        "files_deleted": files_deleted,
        "space_freed_mb": round(space_freed_mb, 2),
        "errors": errors,
        "cleanup_time": now.isoformat()
    }


def get_directory_stats() -> dict:
    """
    Obtiene estadísticas del directorio de resultados.
    
    Returns:
        Diccionario con información del directorio
    """
    if not os.path.exists(RESULTS_DIR):
        return {
            "exists": False,
            "total_files": 0,
            "total_size_mb": 0
        }
    
    total_files = 0
    total_size = 0
    
    try:
        for filename in os.listdir(RESULTS_DIR):
            filepath = os.path.join(RESULTS_DIR, filename)
            if os.path.isfile(filepath):
                total_files += 1
                total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"[CLEANUP] Error obteniendo estadísticas: {str(e)}")
    
    return {
        "exists": True,
        "total_files": total_files,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "ttl_hours": TTL_HOURS
    }
