# Ficheiro: frontend/app/__init__.py
# Este ficheiro é a fábrica da sua aplicação Flask. Ele cria a aplicação,
# configura-a e regista as rotas.

import os
import logging
from flask import Flask

def create_app():
    """Cria e configura uma instância da aplicação Flask."""
    
    # Configura o logging básico para que as mensagens apareçam nos logs do Azure
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    app = Flask(__name__)
    
    logging.info("A iniciar a criação da aplicação Flask.")

    # Lógica para carregar a string de conexão
    storage_connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

    if storage_connection_string:
        app.config["STORAGE_CONNECTION_STRING"] = storage_connection_string
        logging.info("STORAGE_CONNECTION_STRING carregada com sucesso a partir das variáveis de ambiente.")
    else:
        # Em produção, isto seria um erro crítico.
        logging.error("ERRO CRÍTICO: A variável de ambiente AZURE_STORAGE_CONNECTION_STRING não foi encontrada!")
        # Definimos como None para evitar que a app trave, mas as operações de armazenamento falharão.
        app.config["STORAGE_CONNECTION_STRING"] = None

    # Importa e regista o blueprint das rotas a partir do ficheiro routes.py
    from . import routes
    app.register_blueprint(routes.bp)
    logging.info("Blueprint de rotas registado com sucesso.")

    return app
