import logging
import azure.functions as func
from backend.shared.services import computer_vision, blob_storage
from backend.shared.processors import image_processor  # Importando o módulo de processamento
import os
import json
import uuid
from datetime import datetime
import mimetypes

# Configuração avançada de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(myblob: func.InputStream):
    logger.info(f"Processing blob: {myblob.name}")
    process_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    
    try:
        # Extrair informações do blob
        full_path = myblob.name
        blob_name = os.path.basename(full_path)
        container_name = full_path.split('/')[0]
        
        logger.info(f"Container: {container_name}, Blob: {blob_name}")
        logger.info(f"Process ID: {process_id}, Size: {myblob.length} bytes")
        
        # Verificar se o blob já foi processado
        if blob_storage.is_blob_processed(container_name, blob_name):
            logger.info(f"Blob {blob_name} already processed. Skipping.")
            return
        
        # Criar diretório temporário para download
        temp_dir = f"/tmp/processed/{process_id}"
        os.makedirs(temp_dir, exist_ok=True)
        download_path = os.path.join(temp_dir, blob_name)
        
        # 1. Baixar o arquivo para processamento local
        logger.info(f"Downloading blob to: {download_path}")
        blob_storage.download_blob(
            container_name=container_name,
            blob_name=blob_name,
            destination_path=download_path
        )
        
        # 2. Processar imagem usando o serviço de visão computacional
        logger.info(f"Analyzing image: {blob_name}")
        
        # Abrir o arquivo baixado
        with open(download_path, "rb") as file:
            analysis_results = computer_vision.analyze_image(file)
        
        # Registrar resultados
        logger.info(f"Analysis completed for {blob_name}")
        logger.info(f"Results: {json.dumps(analysis_results, indent=2)}")
        
        # 3. Processamento adicional
        # ================================================================
        # SEÇÃO DE PROCESSAMENTO ADICIONAL - IMPLEMENTAÇÃO COMPLETA
        # ================================================================
        
        # Determinar tipo MIME do arquivo
        mime_type, _ = mimetypes.guess_type(blob_name)
        file_type = mime_type.split('/')[0] if mime_type else 'unknown'
        
        processed_files = []
        
        if file_type == 'image':
            # Processamento para imagens
            logger.info("Detected image file. Starting additional processing...")
            
            # a. Gerar miniatura
            thumbnail_path = image_processor.generate_thumbnail(
                input_path=download_path,
                output_dir=temp_dir,
                size=(300, 300),
                quality=85
            )
            
            # b. Converter para formato otimizado
            optimized_path = image_processor.optimize_image(
                input_path=download_path,
                output_dir=temp_dir,
                quality=90
            )
            
            processed_files.extend([thumbnail_path, optimized_path])
            
            # c. Extrair texto (OCR) se aplicável
            ocr_results = computer_vision.extract_text(download_path)
            if ocr_results:
                logger.info(f"Extracted text: {ocr_results[:100]}...")
                text_path = os.path.join(temp_dir, f"{os.path.splitext(blob_name)[0]}_extracted.txt")
                with open(text_path, 'w') as text_file:
                    text_file.write(ocr_results)
                processed_files.append(text_path)
        
        elif file_type == 'video':
            # Processamento para vídeos
            logger.info("Detected video file. Starting additional processing...")
            
            # a. Extrair quadros-chave
            keyframes_dir = os.path.join(temp_dir, "keyframes")
            os.makedirs(keyframes_dir, exist_ok=True)
            video_processor.extract_keyframes(
                input_path=download_path,
                output_dir=keyframes_dir,
                interval=5  # Extrair frame a cada 5 segundos
            )
            
            # b. Gerar miniatura do vídeo
            thumbnail_path = video_processor.generate_video_thumbnail(
                input_path=download_path,
                output_dir=temp_dir,
                time='00:00:05'  # Thumbnail no 5º segundo
            )
            
            # Listar todos os quadros extraídos
            keyframes = [os.path.join(keyframes_dir, f) for f in os.listdir(keyframes_dir)]
            processed_files.extend(keyframes)
            processed_files.append(thumbnail_path)
        
        elif file_type == 'application' and 'pdf' in blob_name.lower():
            # Processamento para PDFs
            logger.info("Detected PDF file. Starting additional processing...")
            
            # a. Extrair todas as páginas como imagens
            pdf_images_dir = os.path.join(temp_dir, "pdf_pages")
            os.makedirs(pdf_images_dir, exist_ok=True)
            pdf_processor.extract_pages_as_images(
                input_path=download_path,
                output_dir=pdf_images_dir,
                dpi=150
            )
            
            # b. Extrair texto
            pdf_text = pdf_processor.extract_text(
                input_path=download_path
            )
            
            text_path = os.path.join(temp_dir, f"{os.path.splitext(blob_name)[0]}_extracted.txt")
            with open(text_path, 'w') as text_file:
                text_file.write(pdf_text)
            
            # Listar todas as páginas extraídas
            pdf_pages = [os.path.join(pdf_images_dir, f) for f in os.listdir(pdf_images_dir)]
            processed_files.extend(pdf_pages)
            processed_files.append(text_path)
        
        else:
            logger.warning(f"Unsupported file type: {file_type}. Skipping additional processing.")
        
        # 4. Fazer upload dos arquivos processados
        for file_path in processed_files:
            if os.path.exists(file_path):
                # Determinar nome do blob de saída
                rel_path = os.path.relpath(file_path, temp_dir)
                output_blob_name = f"processed/{blob_name}/{rel_path}"
                
                # Fazer upload
                blob_storage.upload_blob(
                    container_name="processed-files",
                    blob_name=output_blob_name,
                    file_path=file_path
                )
                logger.info(f"Uploaded processed file: {output_blob_name}")
        
        # 5. Atualizar metadados para evitar reprocessamento
        blob_storage.update_blob_metadata(
            container_name=container_name,
            blob_name=blob_name,
            metadata={
                "processed": "true",
                "process_id": process_id,
                "processed_at": datetime.utcnow().isoformat(),
                "description": analysis_results.get("description", "")[:250],
                "tags": ",".join(analysis_results.get("tags", []))[:250],
                "processed_files": str(len(processed_files))
            }
        )
        
        # 6. Limpeza: remover arquivos temporários
        shutil.rmtree(temp_dir)
        logger.info(f"Temporary directory deleted: {temp_dir}")
        
        # Calcular tempo de processamento
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Successfully processed {blob_name} in {processing_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error processing blob {blob_name}: {str(e)}", exc_info=True)
        
        # Registrar erro nos metadados
        blob_storage.update_blob_metadata(
            container_name=container_name,
            blob_name=blob_name,
            metadata={
                "processed": "error",
                "process_id": process_id,
                "error": str(e)[:250],
                "failed_at": datetime.utcnow().isoformat()
            }
        )
        
        # Relançar exceção para possibilitar retentativas
        raise