"""
Router para endpoints relacionados con procesamiento de imágenes.
"""
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uuid
from ..services import ffmpeg_svc

router = APIRouter(prefix="/imagen", tags=["Imagen"])

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


@router.post("/captura")
async def capture_frame(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tiempo: str = Form(..., description="Tiempo del frame en formato HH:MM:SS"),
    calidad: int = Form(85, description="Calidad WebP (0-100, default: 85)")
):
    """
    Captura un frame de un video en un tiempo específico.
    
    Args:
        file: Archivo de video
        tiempo: Tiempo del frame en formato HH:MM:SS (ejemplo: 00:01:30)
        calidad: Calidad de compresión WebP (0-100, mayor = mejor calidad)
    
    Returns:
        Imagen WebP del frame capturado (optimizada, ~70% menos peso que PNG)
    """
    input_path = save_upload(file)
    output_filename = f"frame_{uuid.uuid4()}.webp"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
    try:
        ffmpeg_svc.capture_frame(input_path, output_path, tiempo, calidad)
        
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        
        return FileResponse(
            output_path,
            media_type="image/webp",
            filename=f"frame_{tiempo.replace(':', '-')}.webp"
        )
    except Exception as e:
        background_tasks.add_task(cleanup_file, input_path)
        background_tasks.add_task(cleanup_file, output_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al capturar frame: {str(e)}"}
        )
