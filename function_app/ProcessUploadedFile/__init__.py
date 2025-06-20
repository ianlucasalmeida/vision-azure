# Ficheiro: function_app/ProcessUploadedFile/__init__.py
# Este é o ponto de entrada principal para a sua Azure Function.
# Ele é acionado quando um novo ficheiro é detetado no armazenamento.

import logging
import os
import sys
import azure.functions as func

# --- Configuração de Caminho ---
# Adiciona a pasta 'shared_code' ao caminho do sistema.
# Isto é crucial para que os 'imports' dos seus processadores funcionem
# corretamente tanto no Azure quanto no seu ambiente de teste local.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Importações Principais ---
# Importa o gestor central que contém toda a lógica de negócio.
from shared_code.main_handler import process_event
# Importa os clientes do Azure SDK para interagir com o armazenamento.
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient

def main(myblob: func.InputStream):
    """
    Esta é a função principal que o Azure executa.
    A sua única responsabilidade é inicializar os serviços do Azure e
    passar o controlo para o gestor principal (process_event).
    """
    logging.info(f"AZURE TRIGGER: Função acionada por blob: {myblob.name}")

    try:
        # Lê a string de conexão a partir das variáveis de ambiente da Azure Function.
        # A variável "AzureWebJobsStorage" é configurada automaticamente pelo Azure.
        connection_string = os.environ["AzureWebJobsStorage"]
        
        # Inicializa os clientes para interagir com o Blob Storage e o Table Storage.
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        table_client = TableServiceClient.from_connection_string(connection_string).get_table_client("jobs")
        
        # Chama a lógica principal, passando o ficheiro e os clientes do Azure.
        process_event(
            blob_name=os.path.basename(myblob.name),
            blob_stream=myblob,
            blob_metadata=myblob.metadata,
            blob_service_client=blob_service_client,
            table_client=table_client
        )
        logging.info(f"AZURE TRIGGER: Chamada para process_event concluída para o blob: {myblob.name}")

    except Exception as e:
        # Captura qualquer erro crítico que possa acontecer durante a inicialização
        # e regista-o para depuração.
        logging.error(f"AZURE TRIGGER: Erro crítico ao inicializar ou chamar o gestor para o blob {myblob.name}. Erro: {e}", exc_info=True)

