# API de Procesamiento Multimedia

API REST modular y escalable para procesamiento de archivos multimedia usando **FastAPI** y **FFmpeg**, containerizada con **Docker**.

## 🎯 Características

**Versión**: 1.1.0 | [Docker Hub](https://hub.docker.com/r/urielx16/multimedia-api)

- ✅ **Extraer metadatos** de videos (formato, duración, codecs, etc.)
- ✅ **Extraer audio** de videos y convertir a MP3
- ✅ **Comprimir videos** reduciendo tamaño sin perder mucha calidad
- ✅ **Cortar audios** entre timestamps específicos
- ✅ **Unir múltiples audios** en un solo archivo
- ✅ **Capturar frames** de videos en timestamps específicos

## 🏗️ Arquitectura

**"Conmutador Ligero"**: La API actúa como orquestador que ejecuta procesos de FFmpeg bajo demanda, sin mantener servicios pesados corriendo constantemente.

```
procesamiento-multimedia-API-docker/
├── app/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── routers/
│   │   ├── video.py         # Endpoints de video
│   │   ├── audio.py         # Endpoints de audio
│   │   └── imagen.py        # Endpoints de imagen
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

**Opción 1: Usar imágenes de Docker Hub (Recomendado)**

```bash
# Descargar docker-compose.yml
wget https://raw.githubusercontent.com/UrielX16-git/procesamiento-multimedia-API-docker/main/docker-compose.yml

# Ejecutar
docker-compose up -d
```

**Opción 2: Construir localmente**

```bash
# Clonar el repositorio
git clone https://github.com/UrielX16-git/procesamiento-multimedia-API-docker.git
cd procesamiento-multimedia-API-docker

# Construir y ejecutar
docker-compose up -d --build
```

La API estará disponible en `http://localhost:8000`

## 📚 Documentación

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>
- **Health Check**: <http://localhost:8000/health>

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

### 6. Capturar Frame de Video

```bash
curl -X POST \
  -F "file=@video.mp4" \
  -F "tiempo=00:01:30" \
  -F "calidad=70" \
  http://localhost:8000/imagen/captura \
  -o frame.webp
```

### 7. Convertir Video a MP4

```bash
curl -X 'POST' \
  'http://localhost:8000/video/convertir-mp4' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@compressed_PjsSiempreExcelentes.mp4;type=video/mp4'
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
