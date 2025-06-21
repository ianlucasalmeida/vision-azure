# Ficheiro: backend/functions/ProcessUploadedFile/__init__.py
# Este é o ponto de entrada para o Azure.

import logging
import os
import azure.functions as func

# Importa o gestor principal a partir do pacote 'shared'.
# Esta é a correção principal, que trata 'shared' como um pacote.
from shared.main_handler import process_event

from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient

def main(myblob: func.InputStream):
    """
    Ponto de entrada do Azure. A sua única tarefa é chamar o gestor principal.
    """
    logging.info(f"AZURE TRIGGER: Função acionada por blob: {myblob.name}")
    try:
        # Pega a connection string das configurações do ambiente
        connection_string = os.environ["AzureWebJobsStorage"]
        
        # Inicializa os clientes de serviço que serão passados para a lógica principal
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        table_client = TableServiceClient.from_connection_string(connection_string).get_table_client("jobs")
        
        # Chama a função de lógica de negócio, passando todos os parâmetros necessários
        process_event(
            blob_name=os.path.basename(myblob.name),
            blob_stream=myblob,
            blob_metadata=myblob.metadata,
            blob_service_client=blob_service_client,
            table_client=table_client
        )
        logging.info(f"AZURE TRIGGER: Chamada para process_event concluída para o blob {myblob.name}.")

    except Exception as e:
        # Captura e loga qualquer erro durante a inicialização ou execução
        logging.error(f"AZURE TRIGGER: Erro crítico. {e}", exc_info=True)
        # Lançar a exceção garante que a execução seja marcada como "Falha" no Azure.
        raise