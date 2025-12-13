# Directorios de datos persistentes

## /uploads
Archivos de entrada que se procesarán. Se eliminan automáticamente después de que el job completa o falla.

## /results
Archivos de salida procesados. TTL de 8 horas desde que el job se completa.

## /temp
Archivos temporales durante el procesamiento. Limpieza cada 30 minutos.

## Estructura de archivos
- `uploads/{job_id}_{filename}` - Archivo original subido
- `results/{job_id}_output.{ext}` - Resultado procesado
- `temp/{job_id}_*.tmp` - Archivos temporales de FFmpeg

## Notas
- No editar estos directorios manualmente
- Los volúmenes están montados en Docker desde `./data`
- Asegurar permisos de escritura para el contenedor
