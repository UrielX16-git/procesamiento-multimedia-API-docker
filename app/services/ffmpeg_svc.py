"""
Servicio de FFmpeg para procesamiento de archivos multimedia.
Encapsula toda la lógica de comandos FFmpeg.
"""
import subprocess
import json
import os
import multiprocessing
import logging
from typing import List, Dict, Any

# Configurar logger
logger = logging.getLogger(__name__)


def get_video_metadata(input_path: str) -> Dict[str, Any]:
    """
    Extrae metadatos de un archivo de video usando ffprobe.
    
    Args:
        input_path: Ruta al archivo de video
        
    Returns:
        Diccionario con metadatos del video
    """
    logger.info(f"[GET_METADATA] Iniciando extraccion de metadatos")
    logger.info(f"[GET_METADATA] Archivo: {input_path}")
    
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        input_path
    ]
    
    logger.info(f"[GET_METADATA] Ejecutando ffprobe...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    metadata = json.loads(result.stdout)
    logger.info(f"[GET_METADATA] Metadatos extraidos exitosamente")
    return metadata


def extract_audio_from_video(input_path: str, output_path: str, quality: int = 2) -> None:
    """
    Extrae el audio de un video y lo convierte a MP3.
    
    Args:
        input_path: Ruta al archivo de video
        output_path: Ruta donde guardar el audio MP3
        quality: Calidad del MP3 (0-9, donde 0 es mejor calidad)
    """
    logger.info(f"[EXTRACT_AUDIO] Iniciando extraccion de audio de video")
    logger.info(f"[EXTRACT_AUDIO] Archivo entrada: {input_path}")
    logger.info(f"[EXTRACT_AUDIO] Archivo salida: {output_path}")
    logger.info(f"[EXTRACT_AUDIO] Calidad MP3: {quality} (0=mejor, 9=peor)")
    
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vn",  # Sin video
        "-acodec", "libmp3lame",
        "-q:a", str(quality),
        "-y",  # Sobrescribir sin preguntar
        output_path
    ]
    
    logger.info(f"[EXTRACT_AUDIO] Ejecutando FFmpeg...")
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f"[EXTRACT_AUDIO] Audio extraido exitosamente")


def compress_video(input_path: str, output_path: str, crf: int = 28, fps: int = 30, audio_bitrate: str = "128k", max_threads: int = 4) -> None:
    """
    Comprime un video reduciendo su tamaño de forma optimizada.
    
    Args:
        input_path: Ruta al archivo de video original
        output_path: Ruta donde guardar el video comprimido
        crf: Constant Rate Factor (23=default, 28=más compresión, 0-51)
        fps: Frames por segundo deseados
        audio_bitrate: Bitrate del audio (ej: "128k")
        max_threads: Número máximo de threads para FFmpeg (default: 4, 0=auto detectar todos)
    """
    # Auto-detectar hilos si max_threads es 0
    if max_threads == 0:
        max_threads = multiprocessing.cpu_count()
        logger.info(f"[COMPRESS_VIDEO] Auto-detectados {max_threads} hilos del CPU")
    else:
        logger.info(f"[COMPRESS_VIDEO] Usando {max_threads} hilos especificados manualmente")
    
    logger.info(f"[COMPRESS_VIDEO] Iniciando compresion con CRF={crf}, FPS={fps}, Audio={audio_bitrate}")
    logger.info(f"[COMPRESS_VIDEO] Archivo entrada: {input_path}")
    logger.info(f"[COMPRESS_VIDEO] Archivo salida: {output_path}")
    
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
    
    logger.info(f"[COMPRESS_VIDEO] Ejecutando FFmpeg...")
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f"[COMPRESS_VIDEO] Compresion completada exitosamente")


def cut_audio(input_path: str, output_path: str, start_time: str, end_time: str) -> None:
    """
    Recorta un archivo de audio entre dos timestamps.
    
    Args:
        input_path: Ruta al archivo de audio original
        output_path: Ruta donde guardar el audio recortado
        start_time: Tiempo de inicio en formato HH:MM:SS
        end_time: Tiempo de fin en formato HH:MM:SS
    """
    logger.info(f"[CUT_AUDIO] Iniciando recorte de audio")
    logger.info(f"[CUT_AUDIO] Archivo entrada: {input_path}")
    logger.info(f"[CUT_AUDIO] Archivo salida: {output_path}")
    logger.info(f"[CUT_AUDIO] Rango: {start_time} -> {end_time}")
    
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-ss", start_time,
        "-to", end_time,
        "-c", "copy",
        "-y",
        output_path
    ]
    
    logger.info(f"[CUT_AUDIO] Ejecutando FFmpeg...")
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f"[CUT_AUDIO] Audio recortado exitosamente")


def concat_audios(input_paths: List[str], output_path: str) -> None:
    """
    Concatena múltiples archivos de audio en uno solo.
    
    Args:
        input_paths: Lista de rutas a los archivos de audio
        output_path: Ruta donde guardar el audio concatenado
    """
    logger.info(f"[CONCAT_AUDIOS] Iniciando concatenacion de audios")
    logger.info(f"[CONCAT_AUDIOS] Numero de archivos: {len(input_paths)}")
    logger.info(f"[CONCAT_AUDIOS] Archivo salida: {output_path}")
    
    list_file_path = output_path + ".list.txt"
    
    try:
        logger.info(f"[CONCAT_AUDIOS] Creando archivo temporal de lista: {list_file_path}")
        with open(list_file_path, "w") as f:
            for i, path in enumerate(input_paths, 1):
                logger.info(f"[CONCAT_AUDIOS] Archivo {i}/{len(input_paths)}: {path}")
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
        
        logger.info(f"[CONCAT_AUDIOS] Ejecutando FFmpeg...")
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"[CONCAT_AUDIOS] Audios concatenados exitosamente")
    
    finally:
        if os.path.exists(list_file_path):
            logger.info(f"[CONCAT_AUDIOS] Limpiando archivo temporal de lista")
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
    logger.info(f"[CAPTURE_FRAME] Iniciando captura de frame")
    logger.info(f"[CAPTURE_FRAME] Archivo entrada: {input_path}")
    logger.info(f"[CAPTURE_FRAME] Archivo salida: {output_path}")
    logger.info(f"[CAPTURE_FRAME] Timestamp: {timestamp}")
    logger.info(f"[CAPTURE_FRAME] Calidad WebP: {quality}")
    
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
    
    logger.info(f"[CAPTURE_FRAME] Ejecutando FFmpeg...")
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f"[CAPTURE_FRAME] Frame capturado exitosamente")


def convert_to_mp4(input_path: str, output_path: str, max_threads: int = 4, force_reencode: bool = False) -> None:
    """
    Convierte un archivo de video de cualquier formato a MP4 de forma optimizada.
    
    Estrategia inteligente por formato:
    - MKV/WEBM: Stream copy directo (SUPER RÁPIDO - segundos) sin subtítulos
    - Otros formatos: Intenta stream copy, si falla re-codifica
    
    Args:
        input_path: Ruta al archivo de video original
        output_path: Ruta donde guardar el video convertido en MP4
        max_threads: Número máximo de threads para FFmpeg (default: 4, 0=auto detectar todos)
        force_reencode: Si True, fuerza la re-codificación sin intentar stream copy
    """
    # Auto-detectar hilos si max_threads es 0
    if max_threads == 0:
        max_threads = multiprocessing.cpu_count()
        logger.info(f"[CONVERT_MP4] Auto-detectados {max_threads} hilos del CPU")
    else:
        logger.info(f"[CONVERT_MP4] Usando {max_threads} hilos especificados manualmente")
    
    # Detectar extensión del archivo de entrada
    input_extension = os.path.splitext(input_path)[1].lower()
    logger.info(f"[CONVERT_MP4] Formato detectado: {input_extension}")
    logger.info(f"[CONVERT_MP4] Archivo entrada: {input_path}")
    logger.info(f"[CONVERT_MP4] Archivo salida: {output_path}")
    
    # Para MKV y WEBM: Stream copy directo (ignora subtítulos para evitar errores)
    if input_extension in ['.mkv', '.webm'] and not force_reencode:
        logger.info(f"[CONVERT_MP4] Estrategia: Stream copy directo para {input_extension} (RAPIDO)")
        logger.info(f"[CONVERT_MP4] Ignorando subtitulos con flag -sn para evitar errores")
        mkv_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-c", "copy",  # Copiar todos los streams sin re-codificar
            "-sn",  # Ignorar subtítulos (evita errores de compatibilidad)
            "-movflags", "+faststart",  # Optimizar para streaming web
            "-y",  # Sobrescribir sin preguntar
            output_path
        ]
        
        # Para MKV/WEBM usamos stream copy directo sin fallback
        logger.info(f"[CONVERT_MP4] Ejecutando stream copy...")
        subprocess.run(mkv_cmd, check=True, capture_output=True)
        logger.info(f"[CONVERT_MP4] Conversion completada exitosamente (stream copy)")
        return
    
    # Para otros formatos: Intentar stream copy primero
    if not force_reencode:
        logger.info(f"[CONVERT_MP4] Estrategia: Intentando stream copy para {input_extension}")
        try:
            stream_copy_cmd = [
                "ffmpeg",
                "-i", input_path,
                "-c", "copy",  # Copiar streams sin re-codificar
                "-movflags", "+faststart",
                "-y",
                output_path
            ]
            
            logger.info(f"[CONVERT_MP4] Ejecutando stream copy...")
            result = subprocess.run(stream_copy_cmd, capture_output=True, text=True, check=False)
            
            # Si tuvo éxito, retornar
            if result.returncode == 0:
                logger.info(f"[CONVERT_MP4] Stream copy exitoso para {input_extension}")
                logger.info(f"[CONVERT_MP4] Conversion completada exitosamente")
                return
            
            # Si falló, limpiar archivo parcial
            logger.warning(f"[CONVERT_MP4] Stream copy fallo (codigo: {result.returncode}), intentando re-codificacion")
            if os.path.exists(output_path):
                os.remove(output_path)
        
        except Exception as e:
            # Limpiar y continuar con re-codificación
            logger.warning(f"[CONVERT_MP4] Stream copy fallo con excepcion: {str(e)}")
            if os.path.exists(output_path):
                os.remove(output_path)
    
    # Fallback: Re-codificar (solo para formatos que lo necesiten)
    logger.warning(f"[CONVERT_MP4] Iniciando re-codificacion para {input_extension} (puede tardar varios minutos)")
    logger.info(f"[CONVERT_MP4] Usando preset=veryfast, CRF=23, audio=AAC 192k, threads={max_threads}")
    reencode_cmd = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "libx264",  # Codec de video H.264
        "-preset", "veryfast",  # Preset rápido
        "-crf", "23",  # Calidad estándar
        "-c:a", "aac",  # Codec de audio AAC
        "-b:a", "192k",  # Bitrate de audio
        "-threads", str(max_threads),
        "-movflags", "+faststart",
        "-y",
        output_path
    ]
    
    logger.info(f"[CONVERT_MP4] Ejecutando re-codificacion con FFmpeg...")
    subprocess.run(reencode_cmd, check=True, capture_output=True)
    logger.info(f"[CONVERT_MP4] Re-codificacion completada exitosamente")
