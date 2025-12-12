"""
Router para endpoints relacionados con procesamiento de video.
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uuid
from ..services import ffmpeg_svc

router = APIRouter(prefix="/video", tags=["Video"])

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
    filepath = save_upload(file)
    
    try:
        metadata = ffmpeg_svc.get_video_metadata(filepath)
        background_tasks.add_task(cleanup_file, filepath)
        return metadata
    except Exception as e:
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
        max_threads: Número máximo de threads (default: 4, para ~70% CPU en 6 cores)
    
    Returns:
        Archivo de video comprimido
    """
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
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al comprimir video: {str(e)}"}
        )
