from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    
    if os.environ.get("WEBSITE_HOSTNAME"):
        # Ambiente de produção no Azure App Service
        app.config["STORAGE_CONNECTION_STRING"] = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    else:
        # Ambiente de desenvolvimento local
        from dotenv import load_dotenv
        load_dotenv(dotenv_path='../.env') # Procura o .env na pasta raiz do frontend
        app.config["STORAGE_CONNECTION_STRING"] = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

    with app.app_context():
        from . import routes

    return app