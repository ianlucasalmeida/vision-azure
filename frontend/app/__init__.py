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

    # --- CORREÇÃO PRINCIPAL: CENTRALIZAR INICIALIZAÇÃO AQUI ---
    try:
        # Padronizando o nome da variável de ambiente
        connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        logging.info("AZURE_STORAGE_CONNECTION_STRING carregada com sucesso.")

        # Inicializa os clientes e os anexa ao objeto da aplicação.
        # As rotas irão aceder a estes clientes através do 'current_app'.
        app.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        app.jobs_table_client = TableServiceClient.from_connection_string(connection_string).get_table_client("jobs")
        
        logging.info("Clientes Blob e Table Storage inicializados com sucesso.")

    except KeyError:
        logging.error("ERRO CRÍTICO: A variável de ambiente AZURE_STORAGE_CONNECTION_STRING não foi encontrada!")
        # Em caso de erro, definimos como None para evitar que a app trave na inicialização.
        app.blob_service_client = None
        app.jobs_table_client = None
    except Exception as e:
        logging.error(f"ERRO CRÍTICO ao inicializar clientes Azure: {e}")
        app.blob_service_client = None
        app.jobs_table_client = None


    # Regista o blueprint das rotas.
    # O Flask é inteligente o suficiente para lidar com o contexto da aplicação aqui.
    with app.app_context():
        from . import routes
        app.register_blueprint(routes.bp)
        logging.info("Blueprint de rotas registado com sucesso.")

    return app