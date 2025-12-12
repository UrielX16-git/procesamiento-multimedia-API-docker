"""
Script de pruebas para validar todos los endpoints de la API.
Genera archivos de prueba y ejecuta todas las operaciones.

Uso:
    python test_api.py

Requisitos:
    pip install requests
"""
import requests
import time
import sys
import os

# Configuración
API_BASE_URL = "http://localhost:8000"
TEST_FILES_DIR = "test_files"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def create_test_files():
    """Crea archivos de prueba usando FFmpeg."""
    print_info("Creando archivos de prueba...")
    
    os.makedirs(TEST_FILES_DIR, exist_ok=True)
    
    # Crear video de prueba (5 segundos, con audio)
    video_path = os.path.join(TEST_FILES_DIR, "test_video.mp4")
    if not os.path.exists(video_path):
        os.system(f'ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 '
                  f'-f lavfi -i sine=frequency=1000:duration=5 '
                  f'-pix_fmt yuv420p "{video_path}" -y')
        print_success(f"Video de prueba creado: {video_path}")
    
    # Crear audio de prueba 1 (3 segundos)
    audio1_path = os.path.join(TEST_FILES_DIR, "test_audio1.mp3")
    if not os.path.exists(audio1_path):
        os.system(f'ffmpeg -f lavfi -i sine=frequency=440:duration=3 '
                  f'-b:a 128k "{audio1_path}" -y')
        print_success(f"Audio 1 creado: {audio1_path}")
    
    # Crear audio de prueba 2 (3 segundos)
    audio2_path = os.path.join(TEST_FILES_DIR, "test_audio2.mp3")
    if not os.path.exists(audio2_path):
        os.system(f'ffmpeg -f lavfi -i sine=frequency=880:duration=3 '
                  f'-b:a 128k "{audio2_path}" -y')
        print_success(f"Audio 2 creado: {audio2_path}")
    
    return video_path, audio1_path, audio2_path


def test_health_check():
    """Prueba el endpoint de health check."""
    print_info("\n1. Probando Health Check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print_success("Health check OK")
            print(f"   Respuesta: {response.json()}")
            return True
        else:
            print_error(f"Health check falló: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error al conectar con la API: {e}")
        return False


def test_root_endpoint():
    """Prueba el endpoint raíz."""
    print_info("\n2. Probando Endpoint Raíz...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            print_success("Endpoint raíz OK")
            data = response.json()
            print(f"   Versión: {data.get('version')}")
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print_error(f"Endpoint raíz falló: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_video_metadata(video_path):
    """Prueba la extracción de metadatos."""
    print_info("\n3. Probando Extracción de Metadatos...")
    try:
        with open(video_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_BASE_URL}/video/detalles", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Metadatos extraídos correctamente")
            
            # Mostrar información relevante
            if 'format' in data:
                fmt = data['format']
                print(f"   Duración: {fmt.get('duration', 'N/A')} segundos")
                print(f"   Tamaño: {int(fmt.get('size', 0)) / 1024:.2f} KB")
                print(f"   Bitrate: {int(fmt.get('bit_rate', 0)) / 1000:.0f} kbps")
            
            if 'streams' in data:
                print(f"   Streams: {len(data['streams'])}")
                for stream in data['streams']:
                    codec_type = stream.get('codec_type', 'unknown')
                    codec_name = stream.get('codec_name', 'unknown')
                    print(f"     - {codec_type}: {codec_name}")
            
            return True
        else:
            print_error(f"Error: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_extract_audio(video_path):
    """Prueba la extracción de audio."""
    print_info("\n4. Probando Extracción de Audio...")
    try:
        with open(video_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_BASE_URL}/video/extraer-audio", files=files)
        
        if response.status_code == 200:
            output_path = os.path.join(TEST_FILES_DIR, "extracted_audio.mp3")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(output_path) / 1024
            print_success(f"Audio extraído correctamente")
            print(f"   Guardado en: {output_path}")
            print(f"   Tamaño: {file_size:.2f} KB")
            return True
        else:
            print_error(f"Error: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_compress_video(video_path):
    """Prueba la compresión de video."""
    print_info("\n5. Probando Compresión de Video...")
    try:
        original_size = os.path.getsize(video_path) / 1024
        
        with open(video_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_BASE_URL}/video/comprimir", files=files)
        
        if response.status_code == 200:
            output_path = os.path.join(TEST_FILES_DIR, "compressed_video.mp4")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            compressed_size = os.path.getsize(output_path) / 1024
            reduction = ((original_size - compressed_size) / original_size) * 100
            
            print_success("Video comprimido correctamente")
            print(f"   Tamaño original: {original_size:.2f} KB")
            print(f"   Tamaño comprimido: {compressed_size:.2f} KB")
            print(f"   Reducción: {reduction:.1f}%")
            print(f"   Guardado en: {output_path}")
            return True
        else:
            print_error(f"Error: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_cut_audio(audio_path):
    """Prueba el corte de audio."""
    print_info("\n6. Probando Corte de Audio...")
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data = {
                'inicio': '00:00:01',
                'fin': '00:00:02'
            }
            response = requests.post(f"{API_BASE_URL}/audio/cortar", files=files, data=data)
        
        if response.status_code == 200:
            output_path = os.path.join(TEST_FILES_DIR, "cut_audio.mp3")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(output_path) / 1024
            print_success("Audio cortado correctamente")
            print(f"   Intervalo: 00:00:01 - 00:00:02")
            print(f"   Tamaño: {file_size:.2f} KB")
            print(f"   Guardado en: {output_path}")
            return True
        else:
            print_error(f"Error: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_join_audios(audio1_path, audio2_path):
    """Prueba la unión de audios."""
    print_info("\n7. Probando Unión de Audios...")
    try:
        with open(audio1_path, 'rb') as f1, open(audio2_path, 'rb') as f2:
            files = [
                ('files', ('audio1.mp3', f1, 'audio/mpeg')),
                ('files', ('audio2.mp3', f2, 'audio/mpeg'))
            ]
            response = requests.post(f"{API_BASE_URL}/audio/unir", files=files)
        
        if response.status_code == 200:
            output_path = os.path.join(TEST_FILES_DIR, "merged_audio.mp3")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(output_path) / 1024
            print_success("Audios unidos correctamente")
            print(f"   Archivos unidos: 2")
            print(f"   Tamaño: {file_size:.2f} KB")
            print(f"   Guardado en: {output_path}")
            return True
        else:
            print_error(f"Error: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def main():
    """Ejecuta todas las pruebas."""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("  PRUEBAS DE API DE PROCESAMIENTO MULTIMEDIA")
    print(f"{'='*60}{Colors.RESET}\n")
    
    results = []
    
    # Crear archivos de prueba
    try:
        video_path, audio1_path, audio2_path = create_test_files()
    except Exception as e:
        print_error(f"Error al crear archivos de prueba: {e}")
        print_warning("Asegúrate de tener FFmpeg instalado en tu sistema")
        return
    
    # Esperar un momento para que el contenedor esté listo
    print_info("\nEsperando que la API esté lista...")
    time.sleep(2)
    
    # Ejecutar pruebas
    results.append(("Health Check", test_health_check()))
    results.append(("Endpoint Raíz", test_root_endpoint()))
    results.append(("Extraer Metadatos", test_video_metadata(video_path)))
    results.append(("Extraer Audio", test_extract_audio(video_path)))
    results.append(("Comprimir Video", test_compress_video(video_path)))
    results.append(("Cortar Audio", test_cut_audio(audio1_path)))
    results.append(("Unir Audios", test_join_audios(audio1_path, audio2_path)))
    
    # Resumen
    print(f"\n{Colors.BLUE}{'='*60}")
    print("  RESUMEN DE PRUEBAS")
    print(f"{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✓ PASÓ{Colors.RESET}" if result else f"{Colors.RED}✗ FALLÓ{Colors.RESET}"
        print(f"  {name:.<30} {status}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    
    if passed == total:
        print_success(f"\n¡Todas las pruebas pasaron! ({passed}/{total})")
        sys.exit(0)
    else:
        print_warning(f"\nAlgunas pruebas fallaron ({passed}/{total})")
        sys.exit(1)


if __name__ == "__main__":
    main()
