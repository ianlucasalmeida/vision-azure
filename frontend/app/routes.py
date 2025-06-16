# ficheiro: frontend/app/routes.py

import os
import uuid
import logging
from flask import Blueprint, current_app, render_template, request, jsonify
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError

bp = Blueprint('main', __name__)
INPUT_CONTAINER = "input-files"
JOBS_TABLE = "jobs"

@bp.route('/')
def home():
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_file():
    logging.info("Recebida uma nova requisição na rota /upload.")
    
    try:
        if 'file' not in request.files:
            logging.error("Falha no upload: 'file' não encontrado na requisição.")
            return jsonify({"error": "Nenhum ficheiro enviado."}), 400
        
        file = request.files['file']
        operation = request.form.get('operation')
        params = request.form.get('params', '')
        
        if file.filename == '' or not operation:
            logging.error(f"Falha no upload: Ficheiro sem nome ou operação em falta. Operação: {operation}")
            return jsonify({"error": "Ficheiro ou operação em falta."}), 400

        logging.info(f"Upload recebido. Ficheiro: '{file.filename}', Operação: '{operation}'.")

        connection_string = current_app.config.get("STORAGE_CONNECTION_STRING")
        if not connection_string:
            logging.error("Falha no upload: A string de conexão com o armazenamento não está configurada.")
            return jsonify({"error": "Configuração de armazenamento do servidor ausente."}), 500

        job_id = str(uuid.uuid4())
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1]
        blob_name = f"{job_id}{file_extension}"
        
        metadata = {"operation": operation, "params": params}

        logging.info(f"A criar BlobServiceClient para o job_id: {job_id}.")
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        logging.info(f"A obter cliente para o blob: container='{INPUT_CONTAINER}', blob_name='{blob_name}'.")
        blob_client = blob_service_client.get_blob_client(container=INPUT_CONTAINER, blob=blob_name)
        
        logging.info("A fazer upload do conteúdo do blob...")
        blob_client.upload_blob(file.read(), metadata=metadata)
        logging.info("Upload do blob concluído com sucesso.")
        
        return jsonify({"success": "Ficheiro enviado para a fila de processamento.", "jobId": job_id})

    except Exception as e:
        # Este log é crucial. Ele irá capturar qualquer erro inesperado.
        logging.error(f"Ocorreu uma exceção inesperada na rota /upload: {e}", exc_info=True)
        return jsonify({"error": "Ocorreu um erro interno no servidor durante o upload."}), 500

@bp.route('/status/<job_id>')
def get_status(job_id):
    try:
        connection_string = current_app.config.get("STORAGE_CONNECTION_STRING")
        if not connection_string:
            return jsonify({"error": "Configuração de armazenamento ausente."}), 500
        
        table_client = TableServiceClient.from_connection_string(connection_string).get_table_client(JOBS_TABLE)
        entity = table_client.get_entity(partition_key="jobs", row_key=job_id)
        return jsonify(entity)
        
    except ResourceNotFoundError:
        return jsonify({"status": "pending"})
    except Exception as e:
        logging.error(f"Erro ao obter o estado para o job_id {job_id}: {e}", exc_info=True)
        return jsonify({"error": "Erro ao verificar o estado do trabalho."}), 500
