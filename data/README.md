# Directorios de datos persistentes

## /uploads

Archivos de entrada que se procesarán. Se eliminan automáticamente después de que el job completa o falla.

## /results

Archivos de salida procesados. **TTL de 3 horas** desde que el job se completa.
**Sistema de limpieza automática** que revisa cada hora y elimina archivos expirados.

## /temp

Archivos temporales durante el procesamiento. Limpieza cada 30 minutos.

## Estructura de archivos

- `uploads/{job_id}_{filename}` - Archivo original subido
- `results/{job_id}_output.{ext}` - Resultado procesado
- `temp/{job_id}_*.tmp` - Archivos temporales de FFmpeg

## Sistema de Limpieza Automática

- **Frecuencia**: Cada 1 hora
- **TTL**: 3 horas desde creación del archivo
- **Proceso**: Ejecuta automáticamente en el worker junto con el procesamiento de jobs
- **Logging**: Todas las operaciones de limpieza se registran en los logs del worker

## Notas

- No editar estos directorios manualmente
- Los volúmenes están montados en Docker desde `./data`
- Asegurar permisos de escritura para el contenedor
- Los archivos procesados son accesibles solo durante 3 horas después de completarse
