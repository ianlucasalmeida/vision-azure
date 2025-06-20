# function_app/shared_code/processors/slideshow_creator.py
import logging
import os
import tempfile
import zipfile
import glob
import shutil
from moviepy.editor import ImageClip, concatenate_videoclips

from .image_processor import shorten_url 

OUTPUT_CONTAINER = "output-files"

def handle(operation, blob_stream, blob_service_client, original_filename, output_container, params):
    logging.info(f"PROCESSADOR DE SLIDESHOW: A manusear a operação '{operation}'.")
    if operation == 'create_slideshow':
        duration_per_slide = int(params) if params and params.isdigit() else 3
        return create_slideshow_from_zip(blob_stream, blob_service_client, output_container, duration_per_slide)
    else:
        raise ValueError(f"Operação de slideshow desconhecida: {operation}")

def create_slideshow_from_zip(blob_stream, blob_service_client, output_container, duration_per_slide):
    logging.info(f"Criando slideshow com duração de {duration_per_slide}s por imagem.")
    temp_dir = tempfile.mkdtemp()
    output_path = tempfile.mktemp(suffix=".mp4")
    try:
        with zipfile.ZipFile(blob_stream, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        image_files = sorted(
            glob.glob(os.path.join(temp_dir, '*.jpg')) +
            glob.glob(os.path.join(temp_dir, '*.jpeg')) +
            glob.glob(os.path.join(temp_dir, '*.png'))
        )
        if not image_files:
            raise ValueError("Nenhum ficheiro de imagem (.jpg, .png) encontrado no ZIP.")
            
        logging.info(f"Encontradas {len(image_files)} imagens para o slideshow.")

        clips = [ImageClip(m).set_duration(duration_per_slide) for m in image_files]
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
        
        output_blob_name = "slideshow_final.mp4"
        output_blob_client = blob_service_client.get_blob_client(container=output_container, blob=output_blob_name)
        with open(output_path, "rb") as data:
            output_blob_client.upload_blob(data, overwrite=True)

        long_url = output_blob_client.url
        short_url = shorten_url(long_url)
        return {"outputUrl": long_url, "shortUrl": short_url}

    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        if os.path.exists(output_path): os.remove(output_path)
