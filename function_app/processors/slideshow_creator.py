# function_app/processors/slideshow_creator.py
import logging
import os
import tempfile
import zipfile
import glob
import shutil
from moviepy.editor import ImageClip, concatenate_videoclips

# Importamos a função utilitária do outro módulo para evitar duplicação
from .image_processor import shorten_url 

OUTPUT_CONTAINER = "output-files"

def handle(operation, blob_stream, blob_service_client, original_filename, output_container, params):
    """
    Função "gestora" que direciona para o processamento de slideshow.
    """
    if operation == 'create_slideshow':
        # O 'params' aqui será a duração de cada slide, vindo do formulário.
        duration_per_slide = int(params) if params and params.isdigit() else 3
        return create_slideshow_from_zip(blob_stream, blob_service_client, output_container, duration_per_slide)
    else:
        raise ValueError(f"Operação de slideshow desconhecida: {operation}")

def create_slideshow_from_zip(blob_stream, blob_service_client, output_container, duration_per_slide):
    """
    Cria um vídeo de slideshow a partir de um ficheiro ZIP que contém imagens.
    """
    logging.info(f"Criando slideshow com duração de {duration_per_slide}s por imagem.")
    
    # Cria um diretório temporário para extrair as imagens
    temp_dir = tempfile.mkdtemp()
    output_path = tempfile.mktemp(suffix=".mp4")

    try:
        # Extrai o ficheiro ZIP para o diretório temporário
        with zipfile.ZipFile(blob_stream, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Encontra todos os ficheiros de imagem (jpg, jpeg, png) e ordena-os alfabeticamente
        image_files = sorted(
            glob.glob(os.path.join(temp_dir, '*.jpg')) +
            glob.glob(os.path.join(temp_dir, '*.jpeg')) +
            glob.glob(os.path.join(temp_dir, '*.png'))
        )
        
        if not image_files:
            raise ValueError("Nenhum ficheiro de imagem (.jpg, .png) encontrado no ZIP.")
            
        logging.info(f"Encontradas {len(image_files)} imagens para o slideshow.")

        # Cria os clipes de vídeo a partir de cada imagem, com a duração definida
        clips = [ImageClip(m).set_duration(duration_per_slide) for m in image_files]
        
        # Junta todos os clipes de imagem num único clipe de vídeo
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Escreve o ficheiro de vídeo final, especificando codecs compatíveis com a web
        final_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
        
        # Define o nome do ficheiro de saída
        output_blob_name = "slideshow_final.mp4"

        # Faz o upload do resultado para o contêiner de saída
        output_blob_client = blob_service_client.get_blob_client(container=output_container, blob=output_blob_name)
        with open(output_path, "rb") as data:
            output_blob_client.upload_blob(data, overwrite=True)

        # Retorna as URLs, incluindo a curta
        long_url = output_blob_client.url
        short_url = shorten_url(long_url)
        return {"outputUrl": long_url, "shortUrl": short_url}

    finally:
        # Garante que o diretório temporário e os seus conteúdos são sempre limpos
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if os.path.exists(output_path):
            os.remove(output_path)
