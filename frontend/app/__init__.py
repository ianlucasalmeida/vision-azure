# Ficheiro: frontend/app/__init__.py
import os
import logging
from flask import Flask
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient

def create_app():
    """Cria e configura uma instância da aplicação Flask."""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    app = Flask(__name__)
    logging.info("A iniciar a criação da aplicação Flask.")

    try:
        connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        logging.info("AZURE_STORAGE_CONNECTION_STRING carregada com sucesso.")

        app.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # --- LÓGICA ATUALIZADA: GARANTIR QUE A TABELA 'JOBS' EXISTE ---
        table_service_client = TableServiceClient.from_connection_string(connection_string)
        app.jobs_table_client = table_service_client.get_table_client("jobs")
        app.jobs_table_client.create_table_if_not_exists()
        logging.info("Tabela 'jobs' verificada e/ou criada com sucesso.")
        # ----------------------------------------------------------------

        logging.info("Clientes Blob e Table Storage inicializados com sucesso.")

    except KeyError:
        logging.error("ERRO CRÍTICO: A variável de ambiente AZURE_STORAGE_CONNECTION_STRING não foi encontrada!")
        app.blob_service_client = None
        app.jobs_table_client = None
    except Exception as e:
        logging.error(f"ERRO CRÍTICO ao inicializar clientes Azure: {e}")
        app.blob_service_client = None
        app.jobs_table_client = None

    with app.app_context():
        from . import routes
        app.register_blueprint(routes.bp)
        logging.info("Blueprint de rotas registado com sucesso.")

    return app