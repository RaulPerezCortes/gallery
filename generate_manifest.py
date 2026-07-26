#!/usr/bin/env python3
"""
Escanea la carpeta `media/`, genera versiones altamente optimizadas para la web
en `media_web/` (incluyendo miniaturas para vídeos) y construye el archivo `manifest.js`.

Soporta fotos de iPhone (.heic) automáticamente.

Requisitos:
  pip install Pillow pillow-heif
  ffmpeg instalado y accesible en el PATH
"""

import json
import subprocess
from pathlib import Path

try:
    from PIL import Image
    from pillow_heif import register_heif_opener
    # Esto le enseña a Pillow a leer archivos .heic automáticamente
    register_heif_opener()
except ImportError:
    print("Faltan librerías. Instálalas con: pip install Pillow pillow-heif")
    raise SystemExit(1)

# Carpetas de origen y destino
MEDIA_DIR = Path("media")
WEB_DIR = Path("media_web")
THUMBS_DIR = WEB_DIR / ".thumbs"

# Añadimos .heic a la lista de imágenes permitidas
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".avi"}

# Ajustes de optimización extrema
MAX_IMAGE_DIMENSION = 1080
IMAGE_QUALITY = 70
VIDEO_CRF = "30"


def optimize_image(src_path: Path, dest_path: Path):
    """Redimensiona y optimiza una imagen (incluyendo HEIC) asegurando compatibilidad RGB."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as img:
        # Convertir a RGB (evita que las fotos salgan en negro si tenían transparencias o perfil CMYK)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")
        
        # Redimensionar si supera el tamaño máximo permitido
        w, h = img.size
        if max(w, h) > MAX_IMAGE_DIMENSION:
            img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            
        # Siempre lo guardamos como JPEG para que todos los navegadores lo puedan leer
        img.save(dest_path, format="JPEG", quality=IMAGE_QUALITY, optimize=True)


def optimize_video(src_path: Path, dest_path: Path):
    """Comprime el vídeo a formato MP4 listo para web, forzando altura máxima de 720p."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src_path),
            "-vcodec", "libx264", "-crf", VIDEO_CRF, "-preset", "faster",
            "-vf", "scale=-2:720",
            "-acodec", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", str(dest_path),
        ],
        capture_output=True,
    )


def make_thumbnail(src_video_path: Path, thumb_path: Path):
    """Extrae una miniatura de fotograma del vídeo."""
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", "00:00:01", "-i", str(src_video_path),
            "-frames:v", "1", "-q:v", "3", str(thumb_path),
        ],
        capture_output=True,
    )


def get_image_dimensions(image_path: Path):
    """Lee el alto y ancho de cualquier imagen usando Pillow."""
    with Image.open(image_path) as img:
        return img.size


def main():
    if not MEDIA_DIR.exists():
        print("No existe la carpeta 'media/' junto a este script.")
        return

    WEB_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        (f for f in MEDIA_DIR.iterdir() if f.is_file() and not f.name.startswith(".")),
        key=lambda f: f.name.lower()
    )

    items = []
    print("Iniciando procesamiento de archivos...\n")

    for f in files:
        ext = f.suffix.lower()

        if ext in IMAGE_EXTS:
            dest_file = WEB_DIR / f"{f.stem}.jpg"
            try:
                optimize_image(f, dest_file)
                w, h = get_image_dimensions(dest_file)
                items.append({"file": dest_file.name, "type": "photo", "width": w, "height": h})
                print(f"  + Foto optimizada:  {dest_file.name} ({w}x{h})")
            except Exception as e:
                print(f"  ! Error procesando foto {f.name}: {e}")

        elif ext in VIDEO_EXTS:
            dest_video = WEB_DIR / f"{f.stem}.mp4"
            thumb_name = f"{f.stem}.jpg"
            thumb_path = THUMBS_DIR / thumb_name

            try:
                optimize_video(f, dest_video)
                make_thumbnail(f, thumb_path)
                w, h = get_image_dimensions(thumb_path)

                items.append({
                    "file": dest_video.name,
                    "type": "video",
                    "width": w,
                    "height": h,
                    "thumb": f".thumbs/{thumb_name}",
                })
                print(f"  + Vídeo optimizado: {dest_video.name} (Miniatura: {w}x{h})")
            except Exception as e:
                print(f"  ! Error procesando vídeo {f.name}: {e}")

        else:
            print(f"  · Omitido (extensión no válida): {f.name}")

    with open("manifest.js", "w", encoding="utf-8") as out:
        out.write("// Generado automáticamente por generate_manifest.py — no editar a mano\n")
        out.write("const GALLERY_ITEMS = ")
        json.dump(items, out, ensure_ascii=False, indent=2)
        out.write(";\n")

    print(f"\nProceso completado con éxito: {len(items)} elementos listos en 'media_web/'.")


if __name__ == "__main__":
    main()