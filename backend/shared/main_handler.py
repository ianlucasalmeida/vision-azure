# Ficheiro: backend/shared/main_handler.py

import logging
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
import azure.functions as func

def process_event(blob_name: str, blob_stream: func.InputStream, blob_metadata: dict, blob_service_client: BlobServiceClient, table_client: TableServiceClient):
    """
    Contém a lógica de negócio real para processar o blob.
    Esta função é chamada pelo __init__.py do gatilho.
    """
    logging.info(f"[HANDLER]: Iniciando o processamento para o blob: {blob_name}")
    logging.info(f"[HANDLER]: Metadados recebidos: {blob_metadata}")

    try:
        # --- INÍCIO DA SUA LÓGICA DE NEGÓCIO ---

        # Exemplo: Ler o conteúdo do blob
        content = blob_stream.read()
        logging.info(f"[HANDLER]: {len(content)} bytes lidos do blob.")

        # Exemplo: Usar o cliente de tabela para atualizar um status
        # Supondo que o nome do blob seja a RowKey na sua tabela de jobs
        job_entity = {
            'PartitionKey': 'blob-processing',
            'RowKey': blob_name,
            'status': 'Processing',
            'file_size': len(content)
        }
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"[HANDLER]: Entidade da tabela para '{blob_name}' atualizada para 'Processing'.")

        # ==========================================================
        # ||                                                      ||
        # ||  SUA LÓGICA PRINCIPAL DE PROCESSAMENTO VAI AQUI...   ||
        # ||  (ex: analisar imagem, extrair dados, etc.)          ||
        # ||                                                      ||
        # ==========================================================

        # Exemplo: Atualizar a tabela ao final do processamento
        job_entity['status'] = 'Completed'
        table_client.upsert_entity(entity=job_entity)
        logging.info(f"[HANDLER]: Entidade da tabela para '{blob_name}' atualizada para 'Completed'.")

        # --- FIM DA SUA LÓGICA DE NEGÓCIO ---

    except Exception as e:
        logging.error(f"[HANDLER]: Falha ao processar o blob {blob_name}. Erro: {e}", exc_info=True)
        # Em caso de erro, atualiza a tabela com o status de falha
        try:
            failed_entity = {
                'PartitionKey': 'blob-processing',
                'RowKey': blob_name,
                'status': 'Failed',
                'error_message': str(e)
            }
            table_client.upsert_entity(entity=failed_entity)
        except Exception as table_e:
            logging.error(f"[HANDLER]: Falha ao registrar o erro na tabela. Erro: {table_e}")
        
        # Propaga o erro para que o Azure saiba que a função falhou
        raise