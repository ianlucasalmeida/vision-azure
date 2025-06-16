import os
from backend.shared.services import blob_storage

def test_upload():
    blob_service = blob_storage.get_blob_service()
    container_client = blob_service.get_container_client("input-files")
    
    with open("test_image.jpg", "rb") as data:
        container_client.upload_blob(name="test_image.jpg", data=data)
        print("Test blob uploaded successfully")

if __name__ == "__main__":
    # Configurar variáveis de ambiente temporárias
    os.environ["AzureWebJobsStorage"] = "<SUA_CONNECTION_STRING>"
    test_upload()