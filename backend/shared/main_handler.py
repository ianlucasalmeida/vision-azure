# Ficheiro: function_app/shared_code/main_handler.py
import logging
import os
from io import BytesIO

# Importa os processadores
from .processors import image_processor, video_processor, pdf_processor

JOBS_TABLE = "jobs"
INPUT_CONTAINER = "input-files"
OUTPUT_CONTAINER = "output-files"

def process_event(blob_name, blob_stream, blob_metadata, blob_service_client, table_client):
    """
    Esta é a função central que orquestra todo o processamento.
    Ela pode ser chamada por qualquer gatilho (Azure Function, servidor local, etc.).
    """
    job_id = os.path.splitext(blob_name)[0]
    logging.info(f"HANDLER: Processando job_id: {job_id}, ficheiro: {blob_name}")
    
    job_entity = {"PartitionKey": "jobs", "RowKey": job_id}

    try:
        # 1. Atualiza o estado para "processando"
        job_entity["status"] = "processing"
        if table_client: table_client.upsert_entity(entity=job_entity)
        else: logging.info("Modo local: Estado 'processing'")

        operation = blob_metadata.get('operation')
        params = blob_metadata.get('params')
        result_data = None

        logging.info(f"HANDLER: Roteando para a operação: '{operation}'")
        
        # 2. Roteamento para o processador correto
        if operation.startswith('img_'):
            result_data = image_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation.startswith('video_'):
            result_data = video_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation.startswith('pdf_'):
            result_data = pdf_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        # Adicione outros processadores aqui
        else:
            raise ValueError(f"Operação desconhecida: {operation}")
        
        if not result_data or 'outputUrl' not in result_data:
            raise Exception("Processamento não retornou uma URL de saída válida.")

        # 3. Atualiza o estado para "concluído"
        job_entity["status"] = "completed"
        job_entity["outputUrl"] = result_data.get('outputUrl')
        if result_data.get('shortUrl'):
            job_entity["shortUrl"] = result_data.get('shortUrl')
        
        if table_client: table_client.upsert_entity(entity=job_entity)
        else: logging.info(f"Modo local: Concluído! URL: {result_data.get('outputUrl')}")

        # 4. Exclui o ficheiro de entrada
        input_blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_name)
        input_blob_client.delete_blob()
        logging.info(f"HANDLER: Ficheiro de entrada {blob_name} excluído.")

    except Exception as e:
        # 5. Em caso de erro, regista a falha
        logging.error(f"HANDLER: Falha no job {job_id}: {e}", exc_info=True)
        job_entity["status"] = "failed"
        job_entity["errorMessage"] = str(e)
        if table_client: table_client.upsert_entity(entity=job_entity)
        else: logging.error(f"Modo local: Falhou! Erro: {str(e)}")