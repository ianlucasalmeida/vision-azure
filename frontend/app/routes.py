import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime
import logging

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html', title='Upload de Ficheiro')

@bp.route('/upload', methods=['POST'])
def upload_file():
    logging.info("Recebida uma nova requisição na rota /upload.")
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro selecionado'}), 400

    file = request.files['file']
    operation = request.form.get('operation', 'unknown')

    if file.filename == '':
        return jsonify({'error': 'Nome do ficheiro vazio'}), 400

    try:
        jobs_table_client = current_app.jobs_table_client
        blob_service_client = current_app.blob_service_client

        if not jobs_table_client or not blob_service_client:
            raise ConnectionError("Os serviços de armazenamento não foram inicializados.")

        job_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        blob_name = f"{job_id}{file_extension}"

        job_entity = {
            'PartitionKey': 'image_processing', 'RowKey': job_id,
            'status': 'Pending', 'original_filename': file.filename,
            'operation': operation, 'timestamp': datetime.utcnow().isoformat()
        }
        jobs_table_client.create_entity(entity=job_entity)
        logging.info(f"Job {job_id} criado na tabela com status 'Pending'.")

        input_container_name = "input-files"
        blob_client = blob_service_client.get_blob_client(container=input_container_name, blob=blob_name)

        metadata = {'operation': operation, 'original_filename': file.filename}
        blob_client.upload_blob(file.read(), metadata=metadata, overwrite=True)
        logging.info(f"Ficheiro para o job {job_id} enviado para o container '{input_container_name}'.")

        return jsonify({'job_id': job_id})

    except Exception as e:
        logging.error(f"Erro na rota /upload: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    try:
        jobs_table_client = current_app.jobs_table_client
        if not jobs_table_client:
            raise ConnectionError("O serviço de tabela não foi inicializado.")

        entity = jobs_table_client.get_entity(partition_key="image_processing", row_key=job_id)

        response = {'status': entity.get('status')}
        if response['status'] == 'Completed':
            response['result_url'] = entity.get('result_url')
        return jsonify(response)

    except Exception as e:
        logging.warning(f"Não foi possível obter o status para o job {job_id}. Erro: {e}")
        return jsonify({'status': 'Not Found', 'error': str(e)}), 404