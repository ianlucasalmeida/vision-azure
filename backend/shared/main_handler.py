# Ficheiro: backend/shared/main_handler.py
import logging
import os

# Importa os seus subprogramas a partir da pasta 'processors'
from processors import image_processor, video_processor, pdf_processor, slideshow_creator

JOBS_TABLE = "jobs"
INPUT_CONTAINER = "input-files"
OUTPUT_CONTAINER = "output-files"

def process_event(blob_name, blob_stream, blob_metadata, blob_service_client, table_client):
    job_id = os.path.splitext(blob_name)[0]
    logging.info(f"HANDLER: Processando job_id: {job_id}")
    job_entity = {"PartitionKey": "jobs", "RowKey": job_id}
    try:
        job_entity["status"] = "processing"
        table_client.upsert_entity(entity=job_entity)

        operation = blob_metadata.get('operation')
        params = blob_metadata.get('params')
        result_data = None
        logging.info(f"HANDLER: Roteando para a operação: '{operation}'")

        # Roteamento para o processador correto
        if operation.startswith('img_'):
            result_data = image_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation.startswith('video_'):
            result_data = video_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation.startswith('pdf_'):
            result_data = pdf_processor.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        elif operation == 'create_slideshow':
            result_data = slideshow_creator.handle(operation, blob_stream, blob_service_client, blob_name, OUTPUT_CONTAINER, params)
        else:
            raise ValueError(f"Operação desconhecida: {operation}")
        
        if not result_data or 'outputUrl' not in result_data:
            raise Exception("Processamento não retornou uma URL de saída.")

        job_entity["status"] = "completed"
        job_entity["outputUrl"] = result_data.get('outputUrl')
        if result_data.get('shortUrl'):
            job_entity["shortUrl"] = result_data.get('shortUrl')
        
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"HANDLER: Job {job_id} concluído.")

        input_blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_name)
        input_blob_client.delete_blob()
        logging.info(f"HANDLER: Ficheiro de entrada {blob_name} excluído.")
    except Exception as e:
        logging.error(f"HANDLER: Falha no job {job_id}: {e}", exc_info=True)
        job_entity["status"] = "failed"
        job_entity["errorMessage"] = str(e)
        table_client.upsert_entity(entity=job_entity)
