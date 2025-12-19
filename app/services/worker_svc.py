"""
Worker daemon que procesa jobs de la cola de forma secuencial.
Se ejecuta como proceso separado en background.
"""
import asyncio
import logging
import signal
import sys
import os
from .queue_svc import QueueService
from . import ffmpeg_svc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class Worker:
    """Worker para procesar jobs de la cola."""
    
    def __init__(self):
        self.queue = QueueService()
        self.running = True
        logger.info("[WORKER] Worker inicializado")
    
    def handle_shutdown(self, signum, frame):
        """Maneja señales de shutdown gracefully."""
        logger.info("[WORKER] Recibida señal de shutdown, terminando...")
        self.running = False
    
    async def process_job(self, job_id: str):
        """
        Procesa un job de la cola.
        
        Args:
            job_id: ID del job a procesar
        """
        try:
            job_data = self.queue.get_job_status(job_id)
            if not job_data:
                logger.error(f"[WORKER] Job no encontrado: {job_id}")
                return
            
            logger.info("=" * 80)
            logger.info(f"[WORKER] Iniciando job: {job_id}")
            logger.info(f"[WORKER] Tipo: {job_data['type']}")
            logger.info(f"[WORKER] Archivo: {job_data['metadata']['original_filename']}")
            logger.info(f"[WORKER] Tamaño: {job_data['metadata']['file_size_mb']:.2f} MB")
            logger.info(f"[WORKER] Prioridad: {job_data['priority']}")
            logger.info("=" * 80)
            
            self.queue.update_job_status(job_id, "processing", progress=0)
            
            job_type = job_data["type"]
            input_file = job_data["input_file"]
            params = job_data["metadata"]["parameters"]
            
            # Validar que el archivo de entrada exista
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Archivo de entrada no encontrado: {input_file}")
            
            # Generar ruta de salida
            output_ext = self._get_output_extension(job_type)
            output_file = os.path.join(
                "/disk/results",
                f"{job_id}_output.{output_ext}"
            )
            
            # Asegurar que el directorio de resultados existe
            os.makedirs("/disk/results", exist_ok=True)
            
            # Ejecutar operación correspondiente
            logger.info(f"[WORKER] Ejecutando operación: {job_type}")
            
            if job_type == "compress_video":
                ffmpeg_svc.compress_video(
                    input_file, 
                    output_file,
                    max_threads=params.get("max_threads", 4)
                )
            
            elif job_type == "convert_mp4":
                ffmpeg_svc.convert_to_mp4(
                    input_file,
                    output_file,
                    max_threads=params.get("max_threads", 4)
                )
            
            elif job_type == "extract_audio":
                ffmpeg_svc.extract_audio_from_video(
                    input_file, 
                    output_file,
                    quality=params.get("quality", 2)
                )
            
            elif job_type == "cut_audio":
                ffmpeg_svc.cut_audio(
                    input_file,
                    output_file,
                    start_time=params.get("start_time"),
                    end_time=params.get("end_time")
                )
            
            elif job_type == "concat_audios":
                # Para concat, input_file es una lista
                ffmpeg_svc.concat_audios(
                    input_paths=params.get("input_files", [input_file]),
                    output_path=output_file
                )
            
            elif job_type == "capture_frame":
                ffmpeg_svc.capture_frame(
                    input_file,
                    output_file,
                    timestamp=params.get("timestamp"),
                    quality=params.get("quality", 85)
                )
            
            elif job_type == "get_metadata":
                # Obtener metadatos del video
                import json
                metadata = ffmpeg_svc.get_video_metadata(input_file)
                
                # Guardar como JSON
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"[WORKER] Metadata guardada como JSON: {output_file}")
            
            else:
                raise ValueError(f"Tipo de job no soportado: {job_type}")
            
            # Verificar que se generó el archivo de salida
            if not os.path.exists(output_file):
                raise FileNotFoundError(f"No se generó el archivo de salida: {output_file}")
            
            output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            logger.info(f"[WORKER] Archivo de salida generado: {output_size_mb:.2f} MB")
            
            # Marcar como completado
            self.queue.update_job_status(
                job_id, 
                "completed", 
                progress=100,
                output_file=output_file
            )
            
            # Decrementar referencia del upload (solo tracking, NO elimina)
            if job_data.get("upload_id"):
                from .upload_svc import UploadService
                upload_service = UploadService()
                upload_service.decrement_ref(job_data["upload_id"], auto_delete=False)
                logger.info(f"[WORKER] Referencia decrementada para upload: {job_data['upload_id']} (limpieza delegada a cleanup)")
            else:
                # Legacy: si no tiene upload_id, eliminar archivo manualmente
                if os.path.exists(input_file):
                    try:
                        os.remove(input_file)
                        logger.info(f"[WORKER] Archivo de entrada eliminado (legacy): {input_file}")
                    except Exception as e:
                        logger.warning(f"[WORKER] No se pudo eliminar archivo de entrada: {str(e)}")
            
            logger.info(f"[WORKER] Job completado exitosamente: {job_id}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"[WORKER] Error procesando job {job_id}: {str(e)}")
            logger.error("=" * 80)
            
            self.queue.update_job_status(
                job_id, 
                "failed",
                error=str(e)
            )
            
            # Decrementar referencia del upload (solo tracking, NO elimina)
            if job_data and job_data.get("upload_id"):
                from .upload_svc import UploadService
                upload_service = UploadService()
                upload_service.decrement_ref(job_data["upload_id"], auto_delete=False)
                logger.info(f"[WORKER] Referencia decrementada para upload (error): {job_data['upload_id']} (limpieza delegada a cleanup)")
            else:
                # Legacy: limpiar archivos en caso de error
                if job_data and job_data.get("input_file"):
                    input_file = job_data["input_file"]
                    if os.path.exists(input_file):
                        try:
                            os.remove(input_file)
                            logger.info(f"[WORKER] Archivo de entrada eliminado tras error (legacy): {input_file}")
                        except:
                            pass
    
    def _get_output_extension(self, job_type: str) -> str:
        """
        Determina la extensión del archivo de salida según el tipo de job.
        
        Args:
            job_type: Tipo de operación
            
        Returns:
            Extensión del archivo (sin punto)
        """
        extensions = {
            "compress_video": "mp4",
            "convert_mp4": "mp4",
            "extract_audio": "mp3",
            "cut_audio": "mp3",
            "concat_audios": "mp3",
            "capture_frame": "webp",
            "get_metadata": "json"
        }
        return extensions.get(job_type, "bin")
    
    async def run(self):
        """Loop principal del worker."""
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        logger.info("=" * 80)
        logger.info("[WORKER] Worker iniciado - esperando jobs en la cola...")
        logger.info("=" * 80)
        
        while self.running:
            try:
                # Obtener siguiente job de la cola (con prioridad)
                job_id = self.queue.get_next_job()
                
                if job_id:
                    await self.process_job(job_id)
                else:
                    # No hay jobs, esperar un segundo
                    await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"[WORKER] Error en loop principal: {str(e)}")
                await asyncio.sleep(5)
        
        logger.info("[WORKER] Worker detenido")


if __name__ == "__main__":
    import asyncio
    from .cleanup_svc import cleanup_old_files
    
    # Asegurar que los directorios existen
    os.makedirs("/disk/uploads", exist_ok=True)
    os.makedirs("/disk/results", exist_ok=True)
    os.makedirs("/disk/temp", exist_ok=True)
    
    async def cleanup_task():
        """Tarea de limpieza automática que se ejecuta cada hora."""
        from .cleanup_svc import cleanup_old_files, cleanup_old_uploads
        
        logger.info("[CLEANUP] Iniciando tarea de limpieza automática (ejecución cada 1 hora)")
        
        # Esperar 5 minutos antes de la primera limpieza (dar tiempo al worker a iniciar)
        await asyncio.sleep(300)
        
        while True:
            try:
                logger.info("[CLEANUP] Ejecutando limpieza programada...")
                
                # Limpiar resultados procesados
                results_stats = cleanup_old_files()
                logger.info(
                    f"[CLEANUP_RESULTS] Archivos eliminados: {results_stats['files_deleted']}, "
                    f"Espacio liberado: {results_stats['space_freed_mb']} MB"
                )
                
                # Limpiar uploads antiguos
                uploads_stats = cleanup_old_uploads()
                logger.info(
                    f"[CLEANUP_UPLOADS] Archivos eliminados: {uploads_stats['files_deleted']}, "
                    f"Espacio liberado: {uploads_stats['space_freed_mb']} MB"
                )
                
            except Exception as e:
                logger.error(f"[CLEANUP] Error en tarea de limpieza: {str(e)}")
            
            # Esperar 1 hora (3600 segundos) antes de la siguiente limpieza
            await asyncio.sleep(3600)
    
    async def main():
        """Ejecuta worker y tarea de limpieza en paralelo."""
        worker = Worker()
        
        # Ejecutar worker y cleanup en paralelo
        await asyncio.gather(
            worker.run(),
            cleanup_task()
        )
    
    asyncio.run(main())

