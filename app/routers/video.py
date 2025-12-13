"""
Router para endpoints relacionados con procesamiento de video.
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uuid
import logging
from ..services import ffmpeg_svc

router = APIRouter(prefix="/video", tags=["Video"])
logger = logging.getLogger(__name__)

TEMP_DIR = "/tmp_media"
os.makedirs(TEMP_DIR, exist_ok=True)


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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Extrae metadatos de un archivo de video.
    
    Returns:
        JSON con información detallada del video (formato, streams, duración, etc.)
    """
    logger.info(f"[ENDPOINT] POST /video/detalles - Recibida solicitud, archivo: {file.filename}")
    filepath = save_upload(file)
    
    try:
        metadata = ffmpeg_svc.get_video_metadata(filepath)
        background_tasks.add_task(cleanup_file, filepath)
        return metadata
    except Exception as e:
        logger.error(f"[ENDPOINT] Error al procesar video: {str(e)}")
        background_tasks.add_task(cleanup_file, filepath)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al procesar video: {str(e)}"}
        )


@router.post("/extraer-audio")
async def extract_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Extrae el audio de un video y lo convierte a MP3.
    
    Returns:
        Archivo MP3 con el audio extraído
    """
    logger.info(f"[ENDPOINT] POST /video/extraer-audio - Recibida solicitud, archivo: {file.filename}")
    input_path = save_upload(file)
    output_filename = f"audio_{uuid.uuid4()}.mp3"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
    try:
        ffmpeg_svc.extract_audio_from_video(input_path, output_path)
        
        # Limpiar archivos después de enviar la respuesta
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        
        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename=f"audio_{file.filename.rsplit('.', 1)[0]}.mp3"
        )
    except Exception as e:
        logger.error(f"[ENDPOINT] Error al extraer audio: {str(e)}")
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al extraer audio: {str(e)}"}
        )


@router.post("/comprimir")
async def compress_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_threads: int = 4
):
    """
    Comprime un video para reducir su tamaño de forma optimizada.
    
    Args:
        file: Archivo de video a comprimir
        max_threads: Número máximo de threads (default: 4, 0=auto detectar todos los hilos)
    
    Returns:
        Archivo de video comprimido
    """
    logger.info(f"[ENDPOINT] POST /video/comprimir - Recibida solicitud, archivo: {file.filename}, max_threads: {max_threads}")
    input_path = save_upload(file)
    output_filename = f"compressed_{uuid.uuid4()}.mp4"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
    try:
        ffmpeg_svc.compress_video(input_path, output_path, max_threads=max_threads)
        
        # Limpiar archivos después de enviar la respuesta
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        
        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=f"compressed_{file.filename}"
        )
    except Exception as e:
        logger.error(f"[ENDPOINT] Error al comprimir video: {str(e)}")
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al comprimir video: {str(e)}"}
        )


@router.post("/convertir-mp4")
async def convert_to_mp4(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_threads: int = 4
):
    """
    Convierte un video de cualquier formato a MP4 de forma ultra-optimizada.
    
    ESTRATEGIA INTELIGENTE:
    - MKV/WEBM: Stream copy directo (INSTANTÁNEO - segundos) sin subtítulos
    - Otros formatos: Intenta stream copy, si falla re-codifica
    
    Args:
        file: Archivo de video a convertir
        max_threads: Número máximo de threads (default: 4, 0=auto detectar todos los hilos)
    
    Returns:
        Archivo de video en formato MP4
    """
    logger.info(f"[ENDPOINT] POST /video/convertir-mp4 - Recibida solicitud, archivo: {file.filename}, max_threads: {max_threads}")
    input_path = save_upload(file)
    
    # Obtener el nombre base sin extensión
    base_filename = file.filename.rsplit('.', 1)[0] if '.' in file.filename else file.filename
    output_filename = f"converted_{uuid.uuid4()}.mp4"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
    try:
        ffmpeg_svc.convert_to_mp4(input_path, output_path, max_threads=max_threads)
        
        # Limpiar archivos después de enviar la respuesta
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        
        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=f"{base_filename}.mp4"
        )
    except Exception as e:
        logger.error(f"[ENDPOINT] Error al convertir video: {str(e)}")
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al convertir video: {str(e)}"}
        )

