# function_app/processors/pdf_processor.py
import logging
import os
import tempfile
import zipfile
from io import BytesIO
import fitz  # PyMuPDF
from pypdf import PdfMerger

from .image_processor import shorten_url

OUTPUT_CONTAINER = "output-files"

def handle(operation, blob_stream, blob_service_client, original_filename, output_container, params):
    """
    Função "gestora" que direciona para o processamento de PDF correto.
    """
    if operation == 'pdf_to_images':
        return convert_pdf_to_images(blob_stream, blob_service_client, original_filename, output_container)
    elif operation == 'merge_pdfs':
        return merge_pdfs_from_zip(blob_stream, blob_service_client, original_filename, output_container)
    else:
        raise ValueError(f"Operação de PDF desconhecida: {operation}")

def convert_pdf_to_images(blob_stream, blob_service_client, original_filename, output_container):
    """Converte cada página de um PDF em uma imagem PNG e retorna um ficheiro ZIP."""
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
    
    output_blob_client = blob_service_client.get_blob_client(container=output_container, blob=output_blob_name)
    output_blob_client.upload_blob(zip_buffer, overwrite=True)
    
    long_url = output_blob_client.url
    short_url = shorten_url(long_url)
    return {"outputUrl": long_url, "shortUrl": short_url}

def merge_pdfs_from_zip(blob_stream, blob_service_client, original_filename, output_container):
    """Junta múltiplos PDFs enviados num ficheiro ZIP num único PDF."""
    logging.info(f"Juntando PDFs de '{original_filename}'.")
    
    merger = PdfMerger()
    
    with zipfile.ZipFile(blob_stream, 'r') as zip_ref:
        # Filtra e ordena os ficheiros para garantir a ordem correta
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
    
    output_blob_client = blob_service_client.get_blob_client(container=output_container, blob=output_blob_name)
    output_blob_client.upload_blob(output_stream, overwrite=True)

    long_url = output_blob_client.url
    short_url = shorten_url(long_url)
    return {"outputUrl": long_url, "shortUrl": short_url}
