# Ficheiro: backend/functions/ProcessUploadedFile/__init__.py
# Este é o ponto de entrada para o Azure.

import logging
import os
import azure.functions as func

# O ficheiro de deploy (.yml) que você usa já configura o PYTHONPATH.
# No entanto, para garantir que funcione, podemos adicionar o caminho manualmente.
# Se o seu .yml já o faz, esta linha é uma segurança extra.
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared')))

# Importa o gestor principal a partir da pasta 'shared'.
from main_handler import process_event
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient

def main(myblob: func.InputStream):
    """
    Ponto de entrada do Azure. A sua única tarefa é chamar o gestor principal.
    """
    logging.info(f"AZURE TRIGGER: Função acionada por blob: {myblob.name}")
    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        table_client = TableServiceClient.from_connection_string(connection_string).get_table_client("jobs")
        
        process_event(
            blob_name=os.path.basename(myblob.name),
            blob_stream=myblob,
            blob_metadata=myblob.metadata,
            blob_service_client=blob_service_client,
            table_client=table_client
        )
    except Exception as e:
        logging.error(f"AZURE TRIGGER: Erro crítico ao inicializar. {e}", exc_info=True)
