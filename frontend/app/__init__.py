# ficheiro: frontend/app/__init__.py

import os
import logging
from flask import Flask

def create_app():
    # Configura o logging básico para que as mensagens apareçam nos logs do Azure
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    app = Flask(__name__)
    
    logging.info("A iniciar a criação da aplicação Flask.")

    # Lógica para carregar a connection string
    storage_connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

    if storage_connection_string:
        app.config["STORAGE_CONNECTION_STRING"] = storage_connection_string
        logging.info("STORAGE_CONNECTION_STRING carregada com sucesso a partir das variáveis de ambiente.")
    else:
        logging.error("ERRO CRÍTICO: A variável de ambiente AZURE_STORAGE_CONNECTION_STRING não foi encontrada!")
        # Mesmo com o erro, continuamos para que a aplicação não trave, mas as operações falharão.
        app.config["STORAGE_CONNECTION_STRING"] = None

    # Regista o blueprint das rotas
    from . import routes
    app.register_blueprint(routes.bp)
    logging.info("Blueprint de rotas registado.")

    return app