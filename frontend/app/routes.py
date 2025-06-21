# Ficheiro: frontend/app/routes.py

import os
import uuid
from flask import Blueprint, render_template, request, jsonify
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
from datetime import datetime

# Blueprint da aplicação
main_routes = Blueprint('main', __name__)

# Inicialização dos clientes Azure a partir das variáveis de ambiente
connection_string = os.environ.get("STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
table_service_client = TableServiceClient.from_connection_string(connection_string)
jobs_table_client = table_service_client.get_table_client("jobs")

@main_routes.route('/')
def index():
    return render_template('index.html', title='Upload de Ficheiro')

@main_routes.route('/upload', methods=['POST'])
def upload_file():
    """
    Recebe o arquivo, cria a entrada na tabela e envia para o blob de input.
    Retorna o ID do trabalho (job_id).
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro selecionado'}), 400
    
    file = request.files['file']
    operation = request.form.get('operation', 'unknown')

    if file.filename == '':
        return jsonify({'error': 'Nome do ficheiro vazio'}), 400

    try:
        # 1. GERAR UM ID ÚNICO PARA O TRABALHO
        job_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        blob_name = f"{job_id}{file_extension}"

        # 2. CRIAR A ENTRADA INICIAL NA TABELA DE JOBS
        job_entity = {
            'PartitionKey': 'image_processing',
            'RowKey': job_id,
            'status': 'Pending',
            'original_filename': file.filename,
            'operation': operation,
            'timestamp': datetime.utcnow().isoformat()
        }
        jobs_table_client.create_entity(entity=job_entity)

        # 3. FAZER UPLOAD DO ARQUIVO PARA O CONTAINER 'input-files'
        input_container_name = "input-files"
        blob_client = blob_service_client.get_blob_client(container=input_container_name, blob=blob_name)
        
        # Adiciona metadados que a Azure Function pode usar
        metadata = {'operation': operation, 'original_filename': file.filename}
        blob_client.upload_blob(file.read(), metadata=metadata, overwrite=True)

        # 4. RETORNAR O JOB_ID PARA O FRONTEND
        return jsonify({'job_id': job_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_routes.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """
    Nova rota para consultar o status de um trabalho específico.
    """
    try:
        # CONSULTA A TABELA USANDO O JOB_ID (ROWKEY)
        entity = jobs_table_client.get_entity(partition_key="image_processing", row_key=job_id)
        
        response = {'status': entity.get('status')}
        
        # Se o trabalho estiver completo, também envia a URL do resultado
        if response['status'] == 'Completed':
            response['result_url'] = entity.get('result_url')
            
        return jsonify(response)
        
    except Exception as e:
        # Pode dar erro se o job_id não for encontrado
        return jsonify({'status': 'Not Found', 'error': str(e)}), 404