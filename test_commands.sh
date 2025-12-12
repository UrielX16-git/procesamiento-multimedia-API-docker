#!/bin/bash
# Script de comandos de prueba con curl para la API
# Ejecuta estos comandos después de que la API esté corriendo

echo "==================================================="
echo "  COMANDOS DE PRUEBA - API MULTIMEDIA"
echo "==================================================="
echo ""

echo "1. Health Check:"
echo "   curl http://localhost:8000/health"
echo ""

echo "2. Información de la API:"
echo "   curl http://localhost:8000/"
echo ""

echo "3. Extraer metadatos de video:"
echo "   curl -X POST -F 'file=@video.mp4' http://localhost:8000/video/detalles"
echo ""

echo "4. Extraer audio de video:"
echo "   curl -X POST -F 'file=@video.mp4' http://localhost:8000/video/extraer-audio -o audio.mp3"
echo ""

echo "5. Comprimir video:"
echo "   curl -X POST -F 'file=@video.mp4' http://localhost:8000/video/comprimir -o compressed.mp4"
echo ""

echo "6. Cortar audio (del segundo 5 al 15):"
echo "   curl -X POST -F 'file=@audio.mp3' -F 'inicio=00:00:05' -F 'fin=00:00:15' http://localhost:8000/audio/cortar -o cut_audio.mp3"
echo ""

echo "7. Unir múltiples audios:"
echo "   curl -X POST -F 'files=@audio1.mp3' -F 'files=@audio2.mp3' -F 'files=@audio3.mp3' http://localhost:8000/audio/unir -o merged.mp3"
echo ""

echo "==================================================="
echo "  DOCUMENTACIÓN INTERACTIVA"
echo "==================================================="
echo ""
echo "Swagger UI: http://localhost:8000/docs"
echo "ReDoc:      http://localhost:8000/redoc"
echo ""
