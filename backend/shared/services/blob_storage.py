# backend/shared/services/blob_storage.py
from azure.storage.blob import BlobServiceClient
import os
import logging
import shutil

logger = logging.getLogger(__name__)

def get_blob_service():
    conn_str = os.getenv("AzureWebJobsStorage")
    return BlobServiceClient.from_connection_string(conn_str)

def get_blob_client(container_name, blob_name):
    service = get_blob_service()
    return service.get_blob_client(container=container_name, blob=blob_name)

def get_blob_metadata(container_name, blob_name):
    try:
        blob_client = get_blob_client(container_name, blob_name)
        properties = blob_client.get_blob_properties()
        return properties.metadata
    except Exception as e:
        logger.error(f"Error getting metadata for {blob_name}: {str(e)}")
        return None

def is_blob_processed(container_name, blob_name):
    metadata = get_blob_metadata(container_name, blob_name)
    return metadata and metadata.get("processed") in ["true", "error"]

def update_blob_metadata(container_name, blob_name, metadata):
    try:
        blob_client = get_blob_client(container_name, blob_name)
        
        # Obter metadados existentes
        existing_metadata = blob_client.get_blob_properties().metadata or {}
        
        # Atualizar com novos valores
        existing_metadata.update(metadata)
        
        # Aplicar alterações
        blob_client.set_blob_metadata(existing_metadata)
        logger.info(f"Metadata updated for {blob_name}: {metadata}")
        return True
    except Exception as e:
        logger.error(f"Error updating metadata for {blob_name}: {str(e)}")
        return False

def download_blob(container_name, blob_name, destination_path):
    try:
        blob_client = get_blob_client(container_name, blob_name)
        
        # Garantir que o diretório de destino existe
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Baixar o blob
        with open(destination_path, "wb") as file:
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())
        
        logger.info(f"Downloaded {blob_name} to {destination_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading blob {blob_name}: {str(e)}")
        return False

def upload_blob(container_name, blob_name, file_path):
    try:
        blob_client = get_blob_client(container_name, blob_name)
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        
        logger.info(f"Uploaded {file_path} as {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Error uploading blob {blob_name}: {str(e)}")
        return False