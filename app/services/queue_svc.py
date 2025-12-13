"""
Servicio de gestión de cola usando Valkey.
Maneja creación, actualización y consulta de jobs con sistema de prioridades.
"""
import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import valkey
import logging

logger = logging.getLogger(__name__)


class QueueService:
    """Servicio para gestionar cola de procesamiento con Valkey."""
    
    # Prioridades: menor número = mayor prioridad
    PRIORITY_HIGH = 10    # Operaciones ligeras (captura de frame, metadatos)
    PRIORITY_NORMAL = 50  # Operaciones medianas (extraer audio, cortar)
    PRIORITY_LOW = 100    # Operaciones pesadas (comprimir, convertir)
    
    def __init__(self, host: str = None, port: int = 6379, db: int = 0):
        """
        Inicializa conexión con Valkey.
        
        Args:
            host: Host de Valkey (default: variable de entorno VALKEY_HOST o 'valkey')
            port: Puerto de Valkey
            db: Base de datos de Valkey
        """
        if host is None:
            host = os.getenv('VALKEY_HOST', 'valkey')
        
        self.redis = valkey.Redis(
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True
        )
        logger.info(f"[QUEUE] Conectado a Valkey en {host}:{port}")
    
    def create_job(
        self, 
        job_type: str, 
        input_file: str,
        original_filename: str,
        file_size_mb: float,
        parameters: Dict[str, Any],
        priority: int = PRIORITY_NORMAL
    ) -> str:
        """
        Crea un nuevo job y lo agrega a la cola con prioridad.
        
        Args:
            job_type: Tipo de operación (compress_video, convert_mp4, etc.)
            input_file: Ruta del archivo de entrada
            original_filename: Nombre original del archivo
            file_size_mb: Tamaño del archivo en MB
            parameters: Parámetros adicionales para la operación
            priority: Prioridad del job (menor = mayor prioridad)
            
        Returns:
            ID del job creado
        """
        job_id = str(uuid.uuid4())
        
        job_data = {
            "id": job_id,
            "status": "pending",
            "type": job_type,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "progress": 0,
            "input_file": input_file,
            "output_file": None,
            "result_url": None,
            "error": None,
            "metadata": {
                "original_filename": original_filename,
                "file_size_mb": round(file_size_mb, 2),
                "parameters": parameters
            }
        }
        
        # Guardar job en Valkey
        self.redis.set(f"job:{job_id}", json.dumps(job_data))
        
        # Agregar a índice de pendientes con timestamp
        self.redis.zadd("pending_jobs", {job_id: datetime.utcnow().timestamp()})
        
        # Agregar a cola con prioridad (ZSET ordenado por prioridad + timestamp)
        # Score = prioridad * 1000000 + timestamp (para mantener FIFO dentro de cada prioridad)
        score = priority * 1000000 + datetime.utcnow().timestamp()
        self.redis.zadd("job_queue", {job_id: score})
        
        logger.info(
            f"[QUEUE] Job creado: {job_id} - {job_type} "
            f"(prioridad: {priority}, tamaño: {file_size_mb:.2f}MB)"
        )
        return job_id
    
    def get_next_job(self, timeout: int = 0) -> Optional[str]:
        """
        Obtiene el siguiente job de la cola según prioridad.
        
        Args:
            timeout: Tiempo de espera en segundos (0 = no bloqueante)
            
        Returns:
            ID del job o None si no hay jobs
        """
        # ZPOPMIN obtiene el elemento con menor score (mayor prioridad)
        result = self.redis.zpopmin("job_queue", count=1)
        
        if result:
            job_id, score = result[0]
            logger.info(f"[QUEUE] Job obtenido de la cola: {job_id}")
            return job_id
        
        return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado actual de un job.
        
        Args:
            job_id: ID del job
            
        Returns:
            Datos del job o None si no existe
        """
        job_data = self.redis.get(f"job:{job_id}")
        if not job_data:
            return None
        return json.loads(job_data)
    
    def update_job_status(
        self, 
        job_id: str, 
        status: str,
        progress: Optional[int] = None,
        output_file: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Actualiza el estado de un job.
        
        Args:
            job_id: ID del job
            status: Nuevo estado (pending, processing, completed, failed)
            progress: Progreso 0-100
            output_file: Ruta del archivo de salida (si completó)
            error: Mensaje de error (si falló)
        """
        job_data = self.get_job_status(job_id)
        if not job_data:
            logger.warning(f"[QUEUE] Job no encontrado para actualizar: {job_id}")
            return
        
        job_data["status"] = status
        
        if progress is not None:
            job_data["progress"] = progress
        
        if status == "processing" and not job_data["started_at"]:
            job_data["started_at"] = datetime.utcnow().isoformat()
            self.redis.zrem("pending_jobs", job_id)
            self.redis.sadd("processing_jobs", job_id)
            logger.info(f"[QUEUE] Job iniciado: {job_id}")
        
        if status in ["completed", "failed"]:
            job_data["completed_at"] = datetime.utcnow().isoformat()
            job_data["progress"] = 100 if status == "completed" else job_data["progress"]
            
            self.redis.srem("processing_jobs", job_id)
            
            if status == "completed":
                job_data["output_file"] = output_file
                job_data["result_url"] = f"/jobs/download/{job_id}"
                # TTL de 8 horas para jobs completados
                self.redis.zadd("completed_jobs", {job_id: datetime.utcnow().timestamp()})
                self.redis.expire(f"job:{job_id}", 28800)  # 8 horas
                logger.info(f"[QUEUE] Job completado: {job_id}")
            else:
                job_data["error"] = error
                # TTL de 7 días para jobs fallidos (debugging)
                self.redis.zadd("failed_jobs", {job_id: datetime.utcnow().timestamp()})
                self.redis.expire(f"job:{job_id}", 604800)  # 7 días
                logger.error(f"[QUEUE] Job fallido: {job_id} - {error}")
        
        self.redis.set(f"job:{job_id}", json.dumps(job_data))
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la cola.
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            "pending": self.redis.zcard("job_queue"),
            "processing": self.redis.scard("processing_jobs"),
            "completed_8h": self.redis.zcard("completed_jobs"),
            "failed_7d": self.redis.zcard("failed_jobs")
        }
    
    def get_queue_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Lista jobs pendientes en la cola ordenados por prioridad.
        
        Args:
            limit: Número máximo de jobs a retornar
            
        Returns:
            Lista de jobs con sus datos
        """
        # Obtener IDs de jobs ordenados por prioridad (menor score primero)
        job_ids_with_scores = self.redis.zrange("job_queue", 0, limit - 1, withscores=True)
        
        jobs = []
        for job_id, score in job_ids_with_scores:
            job_data = self.get_job_status(job_id)
            if job_data:
                # Agregar posición en cola
                job_data["queue_position"] = len(jobs) + 1
                jobs.append(job_data)
        
        return jobs
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancela un job pendiente.
        
        Args:
            job_id: ID del job a cancelar
            
        Returns:
            True si se canceló, False si no se pudo cancelar
        """
        job_data = self.get_job_status(job_id)
        
        if not job_data:
            return False
        
        if job_data["status"] == "processing":
            logger.warning(f"[QUEUE] No se puede cancelar job en procesamiento: {job_id}")
            return False
        
        if job_data["status"] == "pending":
            # Remover de la cola
            self.redis.zrem("job_queue", job_id)
            self.redis.zrem("pending_jobs", job_id)
            
            # Marcar como fallido
            self.update_job_status(job_id, "failed", error="Cancelado por usuario")
            
            # Limpiar archivo de entrada si existe
            if job_data.get("input_file") and os.path.exists(job_data["input_file"]):
                try:
                    os.remove(job_data["input_file"])
                    logger.info(f"[QUEUE] Archivo de entrada eliminado: {job_data['input_file']}")
                except Exception as e:
                    logger.error(f"[QUEUE] Error al eliminar archivo: {str(e)}")
            
            logger.info(f"[QUEUE] Job cancelado: {job_id}")
            return True
        
        return False
