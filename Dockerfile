# Imagen base ligera de Python 3.11
FROM python:3.11-slim

# Evitar archivos .pyc y buffer en logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar FFmpeg y dependencias del sistema
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Instalar librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY ./app ./app

# Crear carpeta temporal para los archivos
RUN mkdir -p /tmp_media

# Exponer puerto
EXPOSE 80

# Ejecutar la app usando Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
