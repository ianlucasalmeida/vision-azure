# function_app/function_app.py
import logging
import azure.functions as func
import os
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient

# Importa todos os seus módulos de processamento
from .processors import image_processor, video_processor, pdf_processor, slideshow_creator

JOBS_TABLE = "jobs"
INPUT_CONTAINER = "input-files"
OUTPUT_CONTAINER = "output-files"

def main(myblob: func.InputStream):
    # --- Bloco de Inicialização ---
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        logging.error("Variável de ambiente AZURE_STORAGE_CONNECTION_STRING não encontrada.")
        # Em caso de falha de configuração, a função termina aqui para evitar mais erros.
        return

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    table_client = TableServiceClient.from_connection_string(connection_string).get_table_client(JOBS_TABLE)
    
    blob_filename = os.path.basename(myblob.name)
    job_id = os.path.splitext(blob_filename)[0]
    logging.info(f"Processando job_id: {job_id}, ficheiro: {blob_filename}")
    
    job_entity = {"PartitionKey": "jobs", "RowKey": job_id}

    try:
        # 1. Atualiza o estado para "processando" na tabela de jobs
        job_entity["status"] = "processing"
        table_client.upsert_entity(entity=job_entity)

        operation = myblob.metadata.get('operation')
        params = myblob.metadata.get('params')
        result_data = None

        # --- Lógica de Roteamento para o Processador Correto ---
        logging.info(f"Roteando para a operação: {operation}")
        
        if operation.startswith('img_'):
            result_data = image_processor.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        elif operation.startswith('video_'):
            result_data = video_processor.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        elif operation.startswith('pdf_'):
            result_data = pdf_processor.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        elif operation == 'create_slideshow':
            # Chama o novo processador de slideshow
            result_data = slideshow_creator.handle(operation, myblob, blob_service_client, blob_filename, OUTPUT_CONTAINER, params)
        else:
            raise ValueError(f"Operação desconhecida recebida: {operation}")

        # 2. Verifica se o processamento retornou um resultado válido
        if not result_data or 'outputUrl' not in result_data:
            raise Exception("O processamento não gerou um ficheiro de saída ou não retornou uma URL.")

        # 3. Se teve sucesso, atualiza o estado com o resultado
        job_entity["status"] = "completed"
        job_entity["outputUrl"] = result_data.get('outputUrl')
        if result_data.get('shortUrl'): # Adiciona a URL curta se existir
            job_entity["shortUrl"] = result_data.get('shortUrl')
            
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"Job {job_id} concluído com sucesso.")

        # 4. Exclui o ficheiro de entrada após o sucesso
        input_blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_filename)
        input_blob_client.delete_blob()
        logging.info(f"Ficheiro de entrada {blob_filename} excluído com sucesso.")

    except Exception as e:
        # 5. Em caso de erro, regista a falha de forma detalhada
        logging.error(f"Falha no job {job_id}: {e}", exc_info=True)
        job_entity["status"] = "failed"
        job_entity["errorMessage"] = str(e)
        table_client.upsert_entity(entity=job_entity)
