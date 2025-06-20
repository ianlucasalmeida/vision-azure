# Ficheiro: function_app/shared_code/processors/image_processor.py
# Contém toda a lógica para processamento de imagens.

import logging
from PIL import Image, ImageOps
import os
from io import BytesIO
import requests

# --- Função Utilitária para Encurtar URL ---
def shorten_url(long_url):
    """Encurta uma URL usando a API do tinyurl.com."""
    try:
        api_url = f"http://tinyurl.com/api-create.php?url={long_url}"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            logging.info(f"URL encurtada com sucesso: {response.text}")
            return response.text
    except Exception as e:
        logging.warning(f"Não foi possível encurtar a URL {long_url}: {e}")
    return None

# --- Função Principal do Processador ---
def handle(operation, blob_stream, blob_service_client, original_filename, output_container, params):
    """
    Função "gestora" que direciona para o processamento de imagem correto.
    Retorna um dicionário com 'outputUrl' e 'shortUrl'.
    """
    logging.info(f"PROCESSADOR DE IMAGEM: A manusear a operação '{operation}'.")
    if operation == 'img_to_bw':
        return convert_to_bw(blob_stream, blob_service_client, original_filename, output_container)
    elif operation == 'img_to_sepia':
        return convert_to_sepia(blob_stream, blob_service_client, original_filename, output_container)
    else:
        raise ValueError(f"Operação de imagem desconhecida: {operation}")

# --- Funções de Processamento Específicas ---
def convert_to_bw(blob_stream, blob_service_client, original_filename, output_container):
    """Converte uma imagem para preto e branco."""
    logging.info(f"Convertendo '{original_filename}' para preto e branco.")
    
    img = Image.open(blob_stream).convert('L') # 'L' é o modo para P&B
    
    output_stream = BytesIO()
    img.save(output_stream, format='PNG')
    output_stream.seek(0)
    
    base_name = os.path.splitext(original_filename)[0]
    output_blob_name = f"{base_name}_bw.png"
    
    return _upload_and_get_urls(output_stream, output_blob_name, output_container, blob_service_client)

def convert_to_sepia(blob_stream, blob_service_client, original_filename, output_container):
    """Aplica um filtro sépia a uma imagem."""
    logging.info(f"Aplicando filtro sépia em '{original_filename}'.")

    img = Image.open(blob_stream).convert('RGB')
    sepia_img = ImageOps.colorize(ImageOps.grayscale(img), '#704214', '#C0A080')

    output_stream = BytesIO()
    sepia_img.save(output_stream, format='JPEG')
    output_stream.seek(0)
    
    base_name = os.path.splitext(original_filename)[0]
    output_blob_name = f"{base_name}_sepia.jpg"
    
    return _upload_and_get_urls(output_stream, output_blob_name, output_container, blob_service_client)

# --- Função Auxiliar ---
def _upload_and_get_urls(stream, blob_name, container, blob_service_client):
    """Faz o upload de um stream para um blob e retorna as URLs."""
    output_blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)
    output_blob_client.upload_blob(stream, overwrite=True)
    logging.info(f"Ficheiro processado salvo em {container}/{blob_name}")
    
    long_url = output_blob_client.url
    short_url = shorten_url(long_url)
    
    return {
        "outputUrl": long_url,
        "shortUrl": short_url
    }
