"""
API REST para procesamiento de archivos multimedia usando FFmpeg.
Arquitectura de "conmutador ligero" que procesa bajo demanda.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import video, audio
import os

# Crear directorio temporal si no existe
TEMP_DIR = "/tmp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

# Inicializar FastAPI
app = FastAPI(
    title="API de Procesamiento Multimedia",
    description="API REST para procesamiento de video y audio usando FFmpeg",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(video.router)
app.include_router(audio.router)


@app.get("/")
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "message": "API de Procesamiento Multimedia",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "video": {
                "/video/detalles": "Extraer metadatos de video",
                "/video/extraer-audio": "Extraer audio de video a MP3",
                "/video/comprimir": "Comprimir video"
            },
            "audio": {
                "/audio/cortar": "Recortar audio entre timestamps",
                "/audio/unir": "Unir múltiples archivos de audio"
            }
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Endpoint de salud para monitoreo."""
    return {"status": "healthy"}


@app.delete("/reset")
async def reset_temp_files():
    """
    Limpia manualmente todos los archivos temporales del directorio /tmp_media.
    
    Returns:
        JSON con estadísticas de limpieza: archivos eliminados y espacio liberado
    """
    import shutil
    
    if not os.path.exists(TEMP_DIR):
        return {
            "status": "success",
            "message": "Directorio temporal no existe",
            "files_deleted": 0,
            "space_freed_mb": 0
        }
    
    files_deleted = 0
    space_freed = 0
    
    try:
        for filename in os.listdir(TEMP_DIR):
            filepath = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(filepath):
                space_freed += os.path.getsize(filepath)
                files_deleted += 1
        
        for filename in os.listdir(TEMP_DIR):
            filepath = os.path.join(TEMP_DIR, filename)
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
            except Exception as e:
                print(f"Error eliminando {filepath}: {e}")
        
        space_freed_mb = round(space_freed / (1024 * 1024), 2)
        
        return {
            "status": "success",
            "message": "Archivos temporales eliminados",
            "files_deleted": files_deleted,
            "space_freed_mb": space_freed_mb
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al limpiar archivos: {str(e)}",
            "files_deleted": 0,
            "space_freed_mb": 0
        }

