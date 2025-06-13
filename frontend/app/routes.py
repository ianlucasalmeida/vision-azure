# app/routes.py

from flask import Blueprint, current_app, render_template, request, jsonify
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError
import uuid
import logging

# 1. Cria um Blueprint chamado 'main'
# A linha "from . import app" foi removida daqui para evitar a importação circular.
bp = Blueprint('main', __name__)

INPUT_CONTAINER = "input-files"
STATS_TABLE_NAME = "stats"

# 2. Usa o Blueprint para definir as rotas (usa @bp.route em vez de @app.route)
@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or not request.form.get('operation'):
        return jsonify({"error": "Requisição incompleta."}), 400

    file = request.files['file']
    operation = request.form.get('operation')
    params = request.form.get('params', '')
    
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado."}), 400

    connection_string = current_app.config.get("STORAGE_CONNECTION_STRING")
    if not connection_string:
        logging.error("ERRO CRÍTICO: A variável de ambiente STORAGE_CONNECTION_STRING não foi encontrada.")
        return jsonify({"error": "Configuração de armazenamento ausente."}), 500

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_name = f"{uuid.uuid4()}-{file.filename}"
    metadata = {"operation": operation, "params": params}

    try:
        blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_name)
        blob_client.upload_blob(file.read(), metadata=metadata)
        logging.info(f"Arquivo {blob_name} enviado para {INPUT_CONTAINER}.")
        return jsonify({"success": f"Arquivo enviado. Operação '{operation}' iniciada."})
    except Exception as e:
        logging.error(f"Erro no upload: {e}")
        return jsonify({"error": "Falha ao enviar arquivo."}), 500

@bp.route('/stats')
def get_stats():
    connection_string = current_app.config.get("STORAGE_CONNECTION_STRING")
    if not connection_string:
        logging.error("ERRO CRÍTICO: A variável de ambiente STORAGE_CONNECTION_STRING não foi encontrada.")
        return jsonify({"error": "Configuração de armazenamento ausente."}), 500
        
    try:
        table_service_client = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service_client.get_table_client(table_name=STATS_TABLE_NAME)
        entities = table_client.list_entities()
        stats = {entity["RowKey"]: entity["count"] for entity in entities}
        return jsonify(stats)
    except ResourceNotFoundError:
        return jsonify({}) # Tabela não existe ainda, retorna vazio
    except Exception as e:
        logging.error(f"Erro ao buscar estatísticas: {e}")
        return jsonify({"error": "Não foi possível buscar estatísticas."}), 500

@bp.route('/logs')
def get_logs():
    # Em produção, os logs devem ser vistos no Application Insights.
    # Esta é uma simulação para manter a UI funcional.
    return "Logs de produção estão disponíveis no Azure Application Insights."
