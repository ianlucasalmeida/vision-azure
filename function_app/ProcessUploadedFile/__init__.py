# Ficheiro: function_app/ProcessUploadedFile/__init__.py
# Versão final e consolidada. Toda a lógica de processamento está neste único
# ficheiro para garantir a máxima compatibilidade com o ambiente Azure.

import logging
import os
import azure.functions as func
from io import BytesIO
import tempfile
import shutil
import zipfile
import glob
import requests

# Dependências de processamento
from PIL import Image, ImageOps
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips
import fitz  # PyMuPDF
from pypdf import PdfMerger

# SDKs do Azure
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient

# --- Constantes da Aplicação ---
JOBS_TABLE = "jobs"
INPUT_CONTAINER = "input-files"
OUTPUT_CONTAINER = "output-files"

#================================================================================
# FUNÇÕES UTILITÁRIAS
#================================================================================

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

def _upload_and_get_urls(stream, blob_name, container, blob_service_client):
    """Faz o upload de um stream para um blob e retorna as URLs."""
    output_blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)
    output_blob_client.upload_blob(stream, overwrite=True)
    logging.info(f"Ficheiro processado salvo em {container}/{blob_name}")
    
    long_url = output_blob_client.url
    short_url = shorten_url(long_url)
    
    return {"outputUrl": long_url, "shortUrl": short_url}

#================================================================================
# PROCESSADORES DE IMAGEM
#================================================================================

def convert_to_bw(blob_stream, blob_service_client, original_filename, output_container):
    logging.info(f"Convertendo '{original_filename}' para preto e branco.")
    img = Image.open(blob_stream).convert('L')
    output_stream = BytesIO()
    img.save(output_stream, format='PNG')
    output_stream.seek(0)
    base_name = os.path.splitext(original_filename)[0]
    output_blob_name = f"{base_name}_bw.png"
    return _upload_and_get_urls(output_stream, output_blob_name, output_container, blob_service_client)

def convert_to_sepia(blob_stream, blob_service_client, original_filename, output_container):
    logging.info(f"Aplicando filtro sépia em '{original_filename}'.")
    img = Image.open(blob_stream).convert('RGB')
    sepia_img = ImageOps.colorize(ImageOps.grayscale(img), '#704214', '#C0A080')
    output_stream = BytesIO()
    sepia_img.save(output_stream, format='JPEG')
    output_stream.seek(0)
    base_name = os.path.splitext(original_filename)[0]
    output_blob_name = f"{base_name}_sepia.jpg"
    return _upload_and_get_urls(output_stream, output_blob_name, output_container, blob_service_client)

#================================================================================
# PROCESSADORES DE VÍDEO E SLIDESHOW
#================================================================================

def convert_to_mp4(blob_stream, blob_service_client, original_filename, output_container):
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
        with open(output_path, "rb") as data:
            return _upload_and_get_urls(data, output_blob_name, output_container, blob_service_client)
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

def generate_thumbnail(blob_stream, blob_service_client, original_filename, output_container):
    logging.info(f"Gerando thumbnail para '{original_filename}'.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(original_filename)[1]) as temp_input_file:
        temp_input_file.write(blob_stream.read())
        input_path = temp_input_file.name
    output_path = tempfile.mktemp(suffix=".jpg")
    try:
        clip = VideoFileClip(input_path)
        clip.save_frame(output_path, t=2.00)
        base_name = os.path.splitext(original_filename)[0]
        output_blob_name = f"thumb_{base_name}.jpg"
        with open(output_path, "rb") as data:
            return _upload_and_get_urls(data, output_blob_name, output_container, blob_service_client)
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

def create_slideshow_from_zip(blob_stream, blob_service_client, output_container, params):
    duration_per_slide = int(params) if params and params.isdigit() else 3
    logging.info(f"Criando slideshow com duração de {duration_per_slide}s por imagem.")
    temp_dir = tempfile.mkdtemp()
    output_path = tempfile.mktemp(suffix=".mp4")
    try:
        with zipfile.ZipFile(blob_stream, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        image_files = sorted(glob.glob(os.path.join(temp_dir, '*.*')))
        if not image_files:
            raise ValueError("Nenhum ficheiro de imagem encontrado no ZIP.")
        clips = [ImageClip(m).set_duration(duration_per_slide) for m in image_files]
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
        output_blob_name = "slideshow_final.mp4"
        with open(output_path, "rb") as data:
            return _upload_and_get_urls(data, output_blob_name, output_container, blob_service_client)
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        if os.path.exists(output_path): os.remove(output_path)
        
#================================================================================
# PROCESSADORES DE PDF
#================================================================================

def convert_pdf_to_images(blob_stream, blob_service_client, original_filename, output_container):
    logging.info(f"Convertendo '{original_filename}' para imagens.")
    pdf_document = fitz.open(stream=blob_stream.read(), filetype="pdf")
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            zip_file.writestr(f"pagina_{page_num + 1}.png", img_bytes)
    zip_buffer.seek(0)
    base_name = os.path.splitext(original_filename)[0]
    output_blob_name = f"{base_name}_images.zip"
    return _upload_and_get_urls(zip_buffer, output_blob_name, output_container, blob_service_client)

def merge_pdfs_from_zip(blob_stream, blob_service_client, output_container):
    logging.info("Juntando PDFs de um ficheiro ZIP.")
    merger = PdfMerger()
    with zipfile.ZipFile(blob_stream, 'r') as zip_ref:
        pdf_files = sorted([f for f in zip_ref.namelist() if f.lower().endswith('.pdf')])
        if not pdf_files:
            raise ValueError("Nenhum ficheiro PDF encontrado no ZIP.")
        for pdf_file in pdf_files:
            with zip_ref.open(pdf_file) as pf:
                merger.append(pf)
    output_stream = BytesIO()
    merger.write(output_stream)
    merger.close()
    output_stream.seek(0)
    output_blob_name = "merged_document.pdf"
    return _upload_and_get_urls(output_stream, output_blob_name, output_container, blob_service_client)

#================================================================================
# FUNÇÃO PRINCIPAL (PONTO DE ENTRADA DO AZURE)
#================================================================================

def main(myblob: func.InputStream):
    connection_string = ""
    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        table_client = TableServiceClient.from_connection_string(connection_string).get_table_client(JOBS_TABLE)
        
        blob_filename = os.path.basename(myblob.name)
        job_id = os.path.splitext(blob_filename)[0]
        logging.info(f"FUNÇÃO ACIONADA: Processando job_id: {job_id}, ficheiro: {blob_filename}")
    except Exception as e:
        logging.error(f"Erro Crítico na Inicialização: {e}", exc_info=True)
        return

    job_entity = {"PartitionKey": "jobs", "RowKey": job_id}
    try:
        job_entity["status"] = "processing"
        table_client.upsert_entity(entity=job_entity)
    except Exception as e:
        logging.error(f"Erro ao atualizar o estado para 'processing': {e}")
    
    try:
        operation = myblob.metadata.get('operation')
        params = myblob.metadata.get('params')
        result_data = None
        logging.info(f"Roteando para a operação: '{operation}'")
        
        # --- Roteamento para as funções de processamento ---
        if operation == 'img_to_bw':
            result_data = convert_to_bw(myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER)
        elif operation == 'img_to_sepia':
            result_data = convert_to_sepia(myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER)
        elif operation == 'video_to_mp4':
            result_data = convert_to_mp4(myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER)
        elif operation == 'generate_thumbnail':
            result_data = generate_thumbnail(myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER)
        elif operation == 'create_slideshow':
            result_data = create_slideshow_from_zip(myblob, blob_service_client, OUTPUT_CONTAINER, params)
        elif operation == 'pdf_to_images':
            result_data = convert_pdf_to_images(myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER)
        elif operation == 'merge_pdfs':
            result_data = merge_pdfs_from_zip(myblob, blob_service_client, OUTPUT_CONTAINER)
        else:
            raise ValueError(f"Operação desconhecida: {operation}")
        
        if not result_data or 'outputUrl' not in result_data:
            raise Exception("Processamento não retornou uma URL de saída válida.")

        job_entity["status"] = "completed"
        job_entity["outputUrl"] = result_data.get('outputUrl')
        if result_data.get('shortUrl'):
            job_entity["shortUrl"] = result_data.get('shortUrl')
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"Job {job_id} concluído com sucesso.")

        input_blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_filename)
        input_blob_client.delete_blob()
        logging.info(f"Ficheiro de entrada '{blob_filename}' excluído.")
    except Exception as e:
        logging.error(f"Falha no processamento do job {job_id}: {e}", exc_info=True)
        job_entity["status"] = "failed"
        job_entity["errorMessage"] = str(e)
        table_client.upsert_entity(entity=job_entity)