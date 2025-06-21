# Ficheiro: backend/shared/main_handler.py

import logging
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
import azure.functions as func
from .processors import image_processor # Supondo que você tenha a lógica aqui

def process_event(blob_name: str, blob_stream: func.InputStream, blob_metadata: dict, blob_service_client: BlobServiceClient, table_client: TableServiceClient):
    """
    Contém a lógica de negócio real para processar o blob e ATUALIZAR O STATUS.
    """
    # O nome do blob AGORA É O NOSSO job_id!
    job_id = blob_name.split('.')[0] # Remove a extensão do arquivo para obter o UUID

    logging.info(f"[HANDLER] Iniciando processamento para o job_id: {job_id}")

    try:
        # 1. ATUALIZAR STATUS PARA "PROCESSING"
        logging.info(f"[HANDLER] Atualizando status para 'Processing' na tabela.")
        table_client.update_entity({
            'PartitionKey': 'image_processing',
            'RowKey': job_id,
            'status': 'Processing'
        })

        # 2. EXECUTAR A LÓGICA DE PROCESSAMENTO
        # (Exemplo: converter imagem para preto e branco)
        operation = blob_metadata.get('operation', 'unknown')
        
        # Simulação do processamento da imagem
        processed_content = image_processor.convert_to_bw(blob_stream.read())
        
        # 3. SALVAR O ARQUIVO PROCESSADO EM UM NOVO CONTAINER
        output_container_name = "output-files"
        output_blob_name = f"{job_id}.jpg" # Salva o resultado com o mesmo ID
        
        output_blob_client = blob_service_client.get_blob_client(container=output_container_name, blob=output_blob_name)
        
        logging.info(f"[HANDLER] Fazendo upload do arquivo processado para: {output_blob_client.url}")
        output_blob_client.upload_blob(processed_content, overwrite=True)

        # 4. ATUALIZAR STATUS PARA "COMPLETED" COM A URL DO RESULTADO
        logging.info(f"[HANDLER] Atualizando status para 'Completed' na tabela.")
        table_client.update_entity({
            'PartitionKey': 'image_processing',
            'RowKey': job_id,
            'status': 'Completed',
            'result_url': output_blob_client.url # A URL para o frontend usar!
        })

    except Exception as e:
        logging.error(f"[HANDLER] Falha ao processar o job {job_id}. Erro: {e}", exc_info=True)
        # 5. ATUALIZAR STATUS PARA "FAILED" EM CASO DE ERRO
        table_client.update_entity({
            'PartitionKey': 'image_processing',
            'RowKey': job_id,
            'status': 'Failed',
            'error_message': str(e)
        })
        raise