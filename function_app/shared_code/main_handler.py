# Ficheiro: function_app/shared_code/main_handler.py
# Este é o "cérebro" da sua aplicação. Ele orquestra todo o processamento.

import logging
import os
from io import BytesIO

# Importa os seus "subprogramas" de processamento.
# O 'sys.path.append' no __init__.py garante que o Python os encontre.
from .processors import image_processor, video_processor, pdf_processor, slideshow_creator

# --- Constantes da Aplicação ---
JOBS_TABLE = "jobs"
INPUT_CONTAINER = "input-files"
OUTPUT_CONTAINER = "output-files"

def process_event(blob_name, blob_stream, blob_metadata, blob_service_client, table_client):
    """
    Esta é a função central que orquestra todo o processamento.
    Ela pode ser chamada por qualquer gatilho (Azure Function, servidor local, etc.).
    """
    # O ID do trabalho é o nome do ficheiro sem a extensão.
    job_id = os.path.splitext(blob_name)[0]
    logging.info(f"HANDLER: Processando job_id: {job_id}, ficheiro: {blob_name}")
    
    job_entity = {"PartitionKey": "jobs", "RowKey": job_id}

    try:
        # 1. Atualiza o estado para "processando" na tabela de jobs
        job_entity["status"] = "processing"
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"HANDLER: Estado do Job {job_id} atualizado para 'processing'.")

        operation = blob_metadata.get('operation')
        params = blob_metadata.get('params')
        result_data = None

        logging.info(f"HANDLER: Roteando para a operação: '{operation}'")
        
        # 2. Roteamento para o processador correto com base no nome da operação
        if operation.startswith('img_'):
            result_data = image_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation.startswith('video_'):
            result_data = video_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation.startswith('pdf_'):
            result_data = pdf_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation == 'create_slideshow':
            result_data = slideshow_creator.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        else:
            raise ValueError(f"Operação desconhecida recebida: {operation}")
        
        # 3. Verifica se o processamento retornou um resultado válido
        if not result_data or 'outputUrl' not in result_data:
            raise Exception("O processamento não gerou um ficheiro de saída ou não retornou uma URL.")

        # 4. Se teve sucesso, atualiza o estado com o resultado
        job_entity["status"] = "completed"
        job_entity["outputUrl"] = result_data.get('outputUrl')
        if result_data.get('shortUrl'): # Adiciona a URL curta se existir
            job_entity["shortUrl"] = result_data.get('shortUrl')
            
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"HANDLER: Job {job_id} concluído com sucesso.")

        # 5. Exclui o ficheiro de entrada após o sucesso
        input_blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_name)
        input_blob_client.delete_blob()
        logging.info(f"HANDLER: Ficheiro de entrada '{blob_name}' excluído com sucesso.")

    except Exception as e:
        # 6. Em caso de erro, regista a falha de forma detalhada
        logging.error(f"HANDLER: Falha no processamento do job {job_id}: {e}", exc_info=True)
        job_entity["status"] = "failed"
        job_entity["errorMessage"] = str(e)
        table_client.upsert_entity(entity=job_entity)

