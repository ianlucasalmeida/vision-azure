# function_app/shared_code/processors/video_processor.py
import logging
from moviepy.editor import VideoFileClip
import os
import tempfile
import shutil

# Importa a função utilitária do módulo de imagem para evitar duplicação
from .image_processor import shorten_url 

OUTPUT_CONTAINER = "output-files"

def handle(operation, blob_stream, blob_service_client, original_filename, output_container, params):
    """Função "gestora" que direciona para o processamento de vídeo correto."""
    logging.info(f"PROCESSADOR DE VÍDEO: A manusear a operação '{operation}'.")
    if operation == 'video_to_mp4':
        return convert_to_mp4(blob_stream, blob_service_client, original_filename, output_container)
    elif operation == 'generate_thumbnail':
        return generate_thumbnail(blob_stream, blob_service_client, original_filename, output_container)
    else:
        raise ValueError(f"Operação de vídeo desconhecida: {operation}")

def convert_to_mp4(blob_stream, blob_service_client, original_filename, output_container):
    """Converte um vídeo para o formato MP4."""
    logging.info(f"Convertendo '{original_filename}' para MP4.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(original_filename)[1]) as temp_input_file:
        temp_input_file.write(blob_stream.read())
        input_path = temp_input_file.name

    output_path = tempfile.mktemp(suffix=".mp4")

    try:
        clip = VideoFileClip(input_path)
        clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        base_name = os.path.splitext(original_filename)[0]
        output_blob_name = f"{base_name}_converted.mp4"

        output_blob_client = blob_service_client.get_blob_client(container=output_container, blob=output_blob_name)
        with open(output_path, "rb") as data:
            output_blob_client.upload_blob(data, overwrite=True)
            
        long_url = output_blob_client.url
        short_url = shorten_url(long_url)
        return {"outputUrl": long_url, "shortUrl": short_url}

    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

def generate_thumbnail(blob_stream, blob_service_client, original_filename, output_container):
    """Extrai um único frame (thumbnail) de um vídeo."""
    logging.info(f"Gerando thumbnail para '{original_filename}'.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(original_filename)[1]) as temp_input_file:
        temp_input_file.write(blob_stream.read())
        input_path = temp_input_file.name

    output_path = tempfile.mktemp(suffix=".jpg")
    
    try:
        clip = VideoFileClip(input_path)
        clip.save_frame(output_path, t=2.00) # Salva o frame do segundo 2
        
        base_name = os.path.splitext(original_filename)[0]
        output_blob_name = f"thumb_{base_name}.jpg"

        output_blob_client = blob_service_client.get_blob_client(container=output_container, blob=output_blob_name)
        with open(output_path, "rb") as data:
            output_blob_client.upload_blob(data, overwrite=True)

        long_url = output_blob_client.url
        short_url = shorten_url(long_url)
        return {"outputUrl": long_url, "shortUrl": short_url}

    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
