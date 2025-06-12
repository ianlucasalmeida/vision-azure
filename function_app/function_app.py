import azure.functions as func
import logging
import os
import tempfile
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableClient

# Importa seus processadores
from processors import image_processor, video_processor

# Define o aplicativo de função
app = func.FunctionApp()

# Define as variáveis de conexão e nomes de recursos
# A connection string principal vem da configuração "AzureWebJobsStorage"
CONNECTION_STRING = os.environ["AzureWebJobsStorage"]
OUTPUT_CONTAINER = "output-files"
STATS_TABLE_NAME = "stats"
STATS_PARTITION_KEY = "stats"

@app.blob_trigger(arg_name="inputblob",
                  path="input-files/{name}",
                  connection="AzureWebJobsStorage")
def vision_processor(inputblob: func.InputStream):
    logging.info(f"Gatilho de Blob acionado para o arquivo: {inputblob.name}")

    try:
        # 1. Obtém metadados do blob de entrada
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container="input-files", blob=inputblob.name)
        metadata = blob_client.get_blob_properties().metadata
        
        operation = metadata.get("operation", "unknown")
        params = metadata.get("params", "")

        # 2. Processa o arquivo
        with tempfile.TemporaryDirectory() as temp_dir:
            file_name = os.path.basename(inputblob.name)
            input_path = os.path.join(temp_dir, file_name)
            
            with open(input_path, "wb") as f:
                f.write(inputblob.read())

            logging.info(f"Arquivo baixado. Operação: '{operation}'")
            output_path = None

            if operation == 'img_to_bw':
                output_path = image_processor.convert_to_bw(input_path)
            elif operation == 'img_change_format':
                output_path = image_processor.change_format(input_path, params)
            elif operation == 'extract_frame':
                second = int(params) if params and params.isdigit() else None
                output_path = video_processor.extract_frame(input_path, second)
            else:
                logging.error(f"Operação desconhecida: {operation}")
                return

            # 3. Faz upload do resultado
            if output_path and os.path.exists(output_path):
                output_blob_name = f"processed-{os.path.basename(output_path)}"
                output_blob_client = blob_service_client.get_blob_client(container=OUTPUT_CONTAINER, blob=output_blob_name)
                with open(output_path, "rb") as data:
                    output_blob_client.upload_blob(data, overwrite=True)
                logging.info(f"Resultado salvo em {OUTPUT_CONTAINER}/{output_blob_name}")
            else:
                logging.warning("Nenhum arquivo de saída foi gerado.")

        # 4. Atualiza as estatísticas na Azure Table Storage
        update_stats(operation)

    except Exception as e:
        logging.error(f"Erro fatal no processamento da função: {e}")


def update_stats(operation_name):
    """Função auxiliar para ler, incrementar e salvar estatísticas."""
    try:
        table_client = TableClient.from_connection_string(CONNECTION_STRING, table_name=STATS_TABLE_NAME)
        
        try:
            # Tenta ler a entidade existente
            entity = table_client.get_entity(partition_key=STATS_PARTITION_KEY, row_key=operation_name)
            current_count = int(entity["count"])
        except Exception:
            # Se não existe, o contador começa em 0
            current_count = 0
            
        # Cria ou atualiza a entidade com o novo valor
        new_entity = {
            "PartitionKey": STATS_PARTITION_KEY,
            "RowKey": operation_name,
            "count": current_count + 1
        }
        table_client.upsert_entity(entity=new_entity)
        logging.info(f"Estatística para '{operation_name}' atualizada para {new_entity['count']}.")

    except Exception as e:
        logging.error(f"Não foi possível atualizar as estatísticas: {e}")