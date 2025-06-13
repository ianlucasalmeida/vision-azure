# app/__init__.py

from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    
    # Lógica para carregar a connection string
    if os.environ.get("WEBSITE_HOSTNAME"):
        # Ambiente de produção no Azure App Service
        # A string de conexão deve ser configurada como uma variável de ambiente no App Service
        app.config["STORAGE_CONNECTION_STRING"] = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    else:
        # Ambiente de desenvolvimento local, usando um arquivo .env
        try:
            from dotenv import load_dotenv
            # O caminho aponta para a pasta raiz (frontend), um nível acima da pasta 'app'
            load_dotenv(dotenv_path='../.env') 
            app.config["STORAGE_CONNECTION_STRING"] = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        except ImportError:
            # dotenv não é uma dependência de produção, então pode não estar instalada.
            # No ambiente de produção, esperamos que a variável de ambiente já exista.
            pass

    # Importa as rotas (do arquivo routes.py) e registra o Blueprint na aplicação.
    # Esta é a linha crucial que conecta suas URLs ao Flask.
    from . import routes
    app.register_blueprint(routes.bp)

    return app
