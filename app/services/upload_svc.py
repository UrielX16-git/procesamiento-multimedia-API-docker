"""
Servicio de gestión de uploads con sistema de referencias.
Permite reutilizar archivos para múltiples jobs y limpieza automática.
"""
import json
import uuid
import os
from datetime import datetime
from typing import Dict, Optional, Any
import valkey
import logging

logger = logging.getLogger(__name__)


class UploadService:
    """Servicio para gestionar uploads con conteo de referencias."""
    
    # TTL de 3 horas para uploads sin usar
    UPLOAD_TTL_UNUSED = 10800  # 3 horas en segundos
    
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
        logger.info(f"[UPLOAD] Conectado a Valkey en {host}:{port}")
    
    def create_upload(
        self,
        filename: str,
        file_path: str,
        file_size_mb: float,
        upload_id: str = None  # NUEVO: permitir pasar ID externo
    ) -> str:
        """
        Crea un registro de upload.
        
        Args:
            filename: Nombre original del archivo
            file_path: Ruta física del archivo
            file_size_mb: Tamaño en MB
            upload_id: ID opcional (si no se pasa, se genera uno)
            
        Returns:
            upload_id
        """
        if not upload_id:
            upload_id = str(uuid.uuid4())
        
        upload_data = {
            "upload_id": upload_id,
            "filename": filename,
            "file_path": file_path,
            "file_size_mb": round(file_size_mb, 2),
            "uploaded_at": datetime.utcnow().isoformat(),
            "ref_count": 0,
            "status": "ready"
        }
        
        # Guardar en Valkey
        self.redis.set(f"upload:{upload_id}", json.dumps(upload_data))
        
        # TTL de 3 horas si no se usa
        self.redis.expire(f"upload:{upload_id}", self.UPLOAD_TTL_UNUSED)
        
        # Agregar a índice de uploads
        self.redis.zadd("uploads", {upload_id: datetime.utcnow().timestamp()})
        
        logger.info(
            f"[UPLOAD] Creado: {upload_id} - {filename} ({file_size_mb:.2f}MB) "
            f"- TTL: 3 horas"
        )
        return upload_id
    
    def get_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un upload.
        
        Args:
            upload_id: ID del upload
            
        Returns:
            Datos del upload o None si no existe
        """
        upload_data = self.redis.get(f"upload:{upload_id}")
        if not upload_data:
            return None
        return json.loads(upload_data)
    
    def increment_ref(self, upload_id: str):
        """
        Incrementa el contador de referencias de un upload.
        Remueve el TTL cuando hay referencias activas.
        
        Args:
            upload_id: ID del upload
        """
        upload_data = self.get_upload(upload_id)
        if not upload_data:
            logger.warning(f"[UPLOAD] No se puede incrementar ref: upload no encontrado: {upload_id}")
            return
        
        upload_data["ref_count"] += 1
        self.redis.set(f"upload:{upload_id}", json.dumps(upload_data))
        
        # Eliminar TTL cuando hay referencias activas
        self.redis.persist(f"upload:{upload_id}")
        
        logger.info(f"[UPLOAD] Ref incrementada: {upload_id} (ref_count: {upload_data['ref_count']})")
    
    def decrement_ref(self, upload_id: str, auto_delete: bool = False):
        """
        Decrementa el contador de referencias de un upload.
        
        Args:
            upload_id: ID del upload
            auto_delete: Si True, elimina cuando ref_count=0. Si False, solo actualiza contador.
        """
        upload_data = self.get_upload(upload_id)
        if not upload_data:
            logger.warning(f"[UPLOAD] No se puede decrementar ref: upload no encontrado: {upload_id}")
            return
        
        upload_data["ref_count"] -= 1
        
        logger.info(f"[UPLOAD] Ref decrementada: {upload_id} (ref_count: {upload_data['ref_count']})")
        
        # Solo eliminar si auto_delete está habilitado
        if auto_delete and upload_data["ref_count"] <= 0:
            self._delete_upload(upload_id, upload_data)
            logger.info(f"[UPLOAD] Upload auto-eliminado (ref_count=0): {upload_id}")
        else:
            # Actualizar contador
            self.redis.set(f"upload:{upload_id}", json.dumps(upload_data))
            if upload_data["ref_count"] <= 0:
                logger.info(f"[UPLOAD] Upload con ref_count=0, se limpiará por TTL: {upload_id}")
    
    def _delete_upload(self, upload_id: str, upload_data: Dict[str, Any]):
        """
        Elimina un upload (archivo físico y registro).
        
        Args:
            upload_id: ID del upload
            upload_data: Datos del upload
        """
        # Eliminar archivo físico
        file_path = upload_data["file_path"]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[UPLOAD] Archivo físico eliminado: {file_path}")
            except Exception as e:
                logger.error(f"[UPLOAD] Error al eliminar archivo: {str(e)}")
        
        # Eliminar registro de Valkey
        self.redis.delete(f"upload:{upload_id}")
        self.redis.zrem("uploads", upload_id)
        
        logger.info(f"[UPLOAD] Upload eliminado: {upload_id} (ref_count llegó a 0)")
    
    def list_uploads(self, limit: int = 50) -> list:
        """
        Lista uploads activos ordenados por fecha.
        
        Args:
            limit: Número máximo de uploads a retornar
            
        Returns:
            Lista de uploads
        """
        upload_ids = self.redis.zrevrange("uploads", 0, limit - 1)
        
        uploads = []
        for upload_id in upload_ids:
            upload_data = self.get_upload(upload_id)
            if upload_data:
                uploads.append(upload_data)
        
        return uploads
    
    def delete_upload_manual(self, upload_id: str) -> bool:
        """
        Elimina manualmente un upload (solo si ref_count = 0).
        
        Args:
            upload_id: ID del upload
            
        Returns:
            True si se eliminó, False si no se pudo
        """
        upload_data = self.get_upload(upload_id)
        if not upload_data:
            return False
        
        if upload_data["ref_count"] > 0:
            logger.warning(
                f"[UPLOAD] No se puede eliminar: hay {upload_data['ref_count']} referencias activas"
            )
            return False
        
        self._delete_upload(upload_id, upload_data)
        return True
