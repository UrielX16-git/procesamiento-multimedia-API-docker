# API de Procesamiento Multimedia

API REST modular y escalable para procesamiento de archivos multimedia usando **FastAPI** y **FFmpeg**, containerizada con **Docker**.

## 🎯 Características

- ✅ **Extraer metadatos** de videos (formato, duración, codecs, etc.)
- ✅ **Extraer audio** de videos y convertir a MP3
- ✅ **Comprimir videos** reduciendo tamaño sin perder mucha calidad
- ✅ **Cortar audios** entre timestamps específicos
- ✅ **Unir múltiples audios** en un solo archivo

## 🏗️ Arquitectura

**"Conmutador Ligero"**: La API actúa como orquestador que ejecuta procesos de FFmpeg bajo demanda, sin mantener servicios pesados corriendo constantemente.

```
procesamiento-multimedia-API-docker/
├── app/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── routers/
│   │   ├── video.py         # Endpoints de video
│   │   └── audio.py         # Endpoints de audio
│   └── services/
│       └── ffmpeg_svc.py    # Lógica FFmpeg
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker
- Docker Compose

### Instalación y Ejecución

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd procesamiento-multimedia-API-docker

# Construir y ejecutar
docker-compose up --build

# O en segundo plano
docker-compose up -d --build
```

La API estará disponible en `http://localhost:8000`

## 📚 Documentación

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🧪 Uso de la API

### 1. Extraer Metadatos de Video

```bash
curl -X POST \
  -F "file=@video.mp4" \
  http://localhost:8000/video/detalles
```

### 2. Extraer Audio de Video

```bash
curl -X POST \
  -F "file=@video.mp4" \
  http://localhost:8000/video/extraer-audio \
  -o audio.mp3
```

### 3. Comprimir Video

```bash
curl -X POST \
  -F "file=@video.mp4" \
  http://localhost:8000/video/comprimir \
  -o compressed.mp4
```

### 4. Cortar Audio

```bash
curl -X POST \
  -F "file=@audio.mp3" \
  -F "inicio=00:00:10" \
  -F "fin=00:00:30" \
  http://localhost:8000/audio/cortar \
  -o cut_audio.mp3
```

### 5. Unir Audios

```bash
curl -X POST \
  -F "files=@audio1.mp3" \
  -F "files=@audio2.mp3" \
  -F "files=@audio3.mp3" \
  http://localhost:8000/audio/unir \
  -o merged_audio.mp3
```

## 🧑‍💻 Desarrollo Local (sin Docker)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Asegurarse de tener FFmpeg instalado en el sistema
ffmpeg -version

# Ejecutar servidor de desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 Configuración

### Variables de Entorno

Puedes configurar las siguientes variables en `docker-compose.yml`:

- `PYTHONUNBUFFERED=1`: Desactiva buffering de logs

### Personalizar Compresión

Edita `app/services/ffmpeg_svc.py` para ajustar parámetros:

- **CRF** (Constant Rate Factor): 0-51, donde 23 es default y 28 es más comprimido
- **FPS**: Frames por segundo (30 por defecto)
- **Audio Bitrate**: Calidad del audio ("128k" por defecto)

## 🛠️ Stack Tecnológico

- **Python 3.11**: Lenguaje base
- **FastAPI**: Framework web asíncrono
- **FFmpeg**: Motor de procesamiento multimedia
- **Uvicorn**: Servidor ASGI
- **Docker**: Containerización

## 📦 Limpieza Automática

Los archivos temporales se eliminan automáticamente después de cada operación usando `BackgroundTasks` de FastAPI.

## 🚧 Mejoras Futuras

- [ ] Procesamiento asíncrono con Redis/Celery para archivos grandes
- [ ] Sistema de cola con IDs de trabajo
- [ ] Límite de tamaño de archivo
- [ ] Autenticación con JWT
- [ ] Rate limiting
- [ ] Métricas y logging estructurado
- [ ] Soporte para más formatos de salida
- [ ] WebSockets para progreso en tiempo real

## 📝 Licencia

MIT

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor abre un issue o pull request.
