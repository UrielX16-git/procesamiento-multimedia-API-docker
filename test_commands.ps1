# Script de PowerShell para probar la API
# Ejecuta estos comandos después de que la API esté corriendo

Write-Host "===================================================" -ForegroundColor Blue
Write-Host "  COMANDOS DE PRUEBA - API MULTIMEDIA" -ForegroundColor Blue
Write-Host "===================================================" -ForegroundColor Blue
Write-Host ""

Write-Host "1. Health Check:" -ForegroundColor Green
Write-Host '   Invoke-WebRequest -Uri "http://localhost:8000/health" | Select-Object -Expand Content' -ForegroundColor Yellow
Write-Host ""

Write-Host "2. Información de la API:" -ForegroundColor Green
Write-Host '   Invoke-WebRequest -Uri "http://localhost:8000/" | Select-Object -Expand Content' -ForegroundColor Yellow
Write-Host ""

Write-Host "3. Extraer metadatos de video:" -ForegroundColor Green
Write-Host '   $response = Invoke-WebRequest -Uri "http://localhost:8000/video/detalles" -Method Post -InFile "video.mp4" -ContentType "multipart/form-data"' -ForegroundColor Yellow
Write-Host '   $response.Content | ConvertFrom-Json' -ForegroundColor Yellow
Write-Host ""

Write-Host "4. Extraer audio de video:" -ForegroundColor Green
Write-Host '   Invoke-WebRequest -Uri "http://localhost:8000/video/extraer-audio" -Method Post -InFile "video.mp4" -OutFile "audio.mp3"' -ForegroundColor Yellow
Write-Host ""

Write-Host "5. Comprimir video:" -ForegroundColor Green
Write-Host '   Invoke-WebRequest -Uri "http://localhost:8000/video/comprimir" -Method Post -InFile "video.mp4" -OutFile "compressed.mp4"' -ForegroundColor Yellow
Write-Host ""

Write-Host "6. Cortar audio (del segundo 5 al 15):" -ForegroundColor Green
Write-Host '   # Requiere crear un formulario multipart manualmente o usar curl en Windows' -ForegroundColor Yellow
Write-Host '   curl -X POST -F "file=@audio.mp3" -F "inicio=00:00:05" -F "fin=00:00:15" http://localhost:8000/audio/cortar -o cut_audio.mp3' -ForegroundColor Yellow
Write-Host ""

Write-Host "7. Unir múltiples audios:" -ForegroundColor Green
Write-Host '   # Requiere crear un formulario multipart manualmente o usar curl en Windows' -ForegroundColor Yellow
Write-Host '   curl -X POST -F "files=@audio1.mp3" -F "files=@audio2.mp3" http://localhost:8000/audio/unir -o merged.mp3' -ForegroundColor Yellow
Write-Host ""

Write-Host "===================================================" -ForegroundColor Blue
Write-Host "  DOCUMENTACIÓN INTERACTIVA" -ForegroundColor Blue
Write-Host "===================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Swagger UI: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "ReDoc:      http://localhost:8000/redoc" -ForegroundColor Cyan
Write-Host ""
Write-Host "RECOMENDACIÓN: Para pruebas más fáciles, usa el script Python:" -ForegroundColor Yellow
Write-Host "   python test_api.py" -ForegroundColor Cyan
Write-Host ""
