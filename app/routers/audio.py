"""
Router para endpoints relacionados con procesamiento de audio.
"""
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import shutil
import os
import uuid
import logging
from ..services import ffmpeg_svc

router = APIRouter(prefix="/audio", tags=["Audio"])
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


def cleanup_files(filepaths: List[str]):
    """Elimina múltiples archivos."""
    for filepath in filepaths:
        cleanup_file(filepath)


@router.post("/cortar")
async def cut_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    inicio: str = Form(..., description="Tiempo de inicio (HH:MM:SS)"),
    fin: str = Form(..., description="Tiempo de fin (HH:MM:SS)")
):
    """
    Recorta un archivo de audio entre dos timestamps.
    
    Args:
        file: Archivo de audio a recortar
        inicio: Tiempo de inicio en formato HH:MM:SS
        fin: Tiempo de fin en formato HH:MM:SS
    
    Returns:
        Archivo de audio recortado
    """
    logger.info(f"[ENDPOINT] POST /audio/cortar - Recibida solicitud, archivo: {file.filename}, inicio: {inicio}, fin: {fin}")
    input_path = save_upload(file)
    output_filename = f"cut_{uuid.uuid4()}.mp3"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
    try:
        ffmpeg_svc.cut_audio(input_path, output_path, inicio, fin)
        
        # Limpiar archivos después de enviar la respuesta
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        
        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename=f"cut_{file.filename}"
        )
    except Exception as e:
        logger.error(f"[ENDPOINT] Error al cortar audio: {str(e)}")
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al cortar audio: {str(e)}"}
        )


@router.post("/unir")
async def join_audios(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Lista de archivos de audio a unir")
):
    """
    Une múltiples archivos de audio en uno solo.
    
    Args:
        files: Lista de archivos de audio (mínimo 2)
    
    Returns:
        Archivo de audio con todos los archivos concatenados
    """
    logger.info(f"[ENDPOINT] POST /audio/unir - Recibida solicitud, numero de archivos: {len(files)}")
    if len(files) < 2:
        logger.warning(f"[ENDPOINT] Se requieren minimo 2 archivos, recibidos: {len(files)}")
        return JSONResponse(
            status_code=400,
            content={"error": "Se requieren al menos 2 archivos para unir"}
        )
    
    input_paths = []
    output_filename = f"merged_{uuid.uuid4()}.mp3"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
    try:
        # Guardar todos los archivos subidos
        for i, file in enumerate(files, 1):
            logger.info(f"[ENDPOINT] Guardando archivo {i}/{len(files)}: {file.filename}")
            input_paths.append(save_upload(file))
        
        # Concatenar audios
        ffmpeg_svc.concat_audios(input_paths, output_path)
        
        # Limpiar archivos después de enviar la respuesta
        background_tasks.add_task(cleanup_files, input_paths)
        background_tasks.add_task(cleanup_file, output_path)
        
        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename="merged_audio.mp3"
        )
    except Exception as e:
        logger.error(f"[ENDPOINT] Error al unir audios: {str(e)}")
        background_tasks.add_task(cleanup_files, input_paths)
        background_tasks.add_task(cleanup_file, output_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al unir audios: {str(e)}"}
        )
