"""
Servicio de FFmpeg para procesamiento de archivos multimedia.
Encapsula toda la lógica de comandos FFmpeg.
"""
import subprocess
import json
import os
from typing import List, Dict, Any


def get_video_metadata(input_path: str) -> Dict[str, Any]:
    """
    Extrae metadatos de un archivo de video usando ffprobe.
    
    Args:
        input_path: Ruta al archivo de video
        
    Returns:
        Diccionario con metadatos del video
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        input_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def extract_audio_from_video(input_path: str, output_path: str, quality: int = 2) -> None:
    """
    Extrae el audio de un video y lo convierte a MP3.
    
    Args:
        input_path: Ruta al archivo de video
        output_path: Ruta donde guardar el audio MP3
        quality: Calidad del MP3 (0-9, donde 0 es mejor calidad)
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vn",  # Sin video
        "-acodec", "libmp3lame",
        "-q:a", str(quality),
        "-y",  # Sobrescribir sin preguntar
        output_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)


def compress_video(input_path: str, output_path: str, crf: int = 28, fps: int = 30, audio_bitrate: str = "128k", max_threads: int = 4) -> None:
    """
    Comprime un video reduciendo su tamaño de forma optimizada.
    
    Args:
        input_path: Ruta al archivo de video original
        output_path: Ruta donde guardar el video comprimido
        crf: Constant Rate Factor (23=default, 28=más compresión, 0-51)
        fps: Frames por segundo deseados
        audio_bitrate: Bitrate del audio (ej: "128k")
        max_threads: Número máximo de threads para FFmpeg (default: 4)
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vcodec", "libx264",
        "-crf", str(crf),
        "-r", str(fps),
        "-preset", "veryfast",
        "-threads", str(max_threads),
        "-acodec", "aac",
        "-b:a", audio_bitrate,
        "-y",
        output_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)


def cut_audio(input_path: str, output_path: str, start_time: str, end_time: str) -> None:
    """
    Recorta un archivo de audio entre dos timestamps.
    
    Args:
        input_path: Ruta al archivo de audio original
        output_path: Ruta donde guardar el audio recortado
        start_time: Tiempo de inicio en formato HH:MM:SS
        end_time: Tiempo de fin en formato HH:MM:SS
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-ss", start_time,
        "-to", end_time,
        "-c", "copy",
        "-y",
        output_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)


def concat_audios(input_paths: List[str], output_path: str) -> None:
    """
    Concatena múltiples archivos de audio en uno solo.
    
    Args:
        input_paths: Lista de rutas a los archivos de audio
        output_path: Ruta donde guardar el audio concatenado
    """
    list_file_path = output_path + ".list.txt"
    
    try:
        with open(list_file_path, "w") as f:
            for path in input_paths:
                f.write(f"file '{path}'\n")
        
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file_path,
            "-c", "copy",
            "-y",
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    finally:
        if os.path.exists(list_file_path):
            os.remove(list_file_path)


def capture_frame(input_path: str, output_path: str, timestamp: str, quality: int = 85) -> None:
    """
    Captura un frame de un video en un tiempo específico en formato WebP optimizado.
    
    Args:
        input_path: Ruta al archivo de video
        output_path: Ruta donde guardar la imagen
        timestamp: Tiempo en formato HH:MM:SS
        quality: Calidad de compresión WebP (0-100, default: 85)
    """
    cmd = [
        "ffmpeg",
        "-ss", timestamp,
        "-i", input_path,
        "-frames:v", "1",
        "-c:v", "libwebp",
        "-quality", str(quality),
        "-compression_level", "6",
        "-y",
        output_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
