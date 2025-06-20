# Ficheiro: function_app/ProcessUploadedFile/__init__.py
# Versão final e simplificada. Toda a lógica está contida ou é importada
# a partir desta pasta para garantir que o Azure a encontre.

import logging
import os
import azure.functions as func

# Importa os processadores diretamente da mesma pasta
from . import image_processor
from . import video_processor
from . import pdf_processor
from . import slideshow_creator

from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient

# --- Constantes da Aplicação ---
JOBS_TABLE = "jobs"
INPUT_CONTAINER = "input-files"
OUTPUT_CONTAINER = "output-files"

def main(myblob: func.InputStream):
    """
    Esta é a função principal que é acionada sempre que um novo ficheiro
    chega ao contêiner 'input-files'.
    """
    
    # --- 1. Bloco de Inicialização ---
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

    # --- 2. Atualiza o Estado do Trabalho para 'Processing' ---
    job_entity = {"PartitionKey": "jobs", "RowKey": job_id}
    try:
        job_entity["status"] = "processing"
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"Estado do Job {job_id} atualizado para 'processing'.")
    except Exception as e:
        logging.error(f"Erro ao atualizar o estado para 'processing' para o job {job_id}: {e}")
    
    # --- 3. Executa a Operação ---
    try:
        operation = myblob.metadata.get('operation')
        params = myblob.metadata.get('params')
        result_data = None

        logging.info(f"Roteando para a operação: '{operation}'")
        
        # --- Lógica de Roteamento para o Processador Correto ---
        if operation.startswith('img_'):
            result_data = image_processor.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        elif operation.startswith('video_'):
            result_data = video_processor.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        elif operation.startswith('pdf_'):
            result_data = pdf_processor.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        elif operation == 'create_slideshow':
            result_data = slideshow_creator.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        else:
            raise ValueError(f"Operação desconhecida recebida: {operation}")
        
        if not result_data or 'outputUrl' not in result_data:
            raise Exception("Processamento não retornou uma URL de saída válida.")

        # --- 4. Atualiza o Estado para 'Completed' ---
        job_entity["status"] = "completed"
        job_entity["outputUrl"] = result_data.get('outputUrl')
        if result_data.get('shortUrl'):
            job_entity["shortUrl"] = result_data.get('shortUrl')
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"Job {job_id} concluído com sucesso.")

        # --- 5. Limpeza ---
        input_blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_filename)
        input_blob_client.delete_blob()
        logging.info(f"Ficheiro de entrada '{blob_filename}' excluído.")

    except Exception as e:
        # --- Bloco de Erro ---
        logging.error(f"Falha no processamento do job {job_id}: {e}", exc_info=True)
        job_entity["status"] = "failed"
        job_entity["errorMessage"] = str(e)
        table_client.upsert_entity(entity=job_entity)
