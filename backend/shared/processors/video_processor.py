import cv2
import os
import logging
from .image_processor import generate_thumbnail

logger = logging.getLogger(__name__)

def extract_keyframes(input_path, output_dir, interval=5):
    try:
        # Garantir que o diretório de saída existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Abrir o vídeo
        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * interval)
        count = 0
        frame_count = 0
        keyframes = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Salvar frame a cada intervalo especificado
            if count % frame_interval == 0:
                frame_filename = f"frame_{frame_count:04d}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                cv2.imwrite(frame_path, frame)
                keyframes.append(frame_path)
                frame_count += 1
            
            count += 1
        
        cap.release()
        logger.info(f"Extracted {len(keyframes)} keyframes from video")
        return keyframes
    except Exception as e:
        logger.error(f"Error extracting keyframes: {str(e)}")
        raise

def generate_video_thumbnail(input_path, output_dir, time='00:00:05'):
    try:
        # Garantir que o diretório de saída existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Extrair frame no tempo especificado
        cap = cv2.VideoCapture(input_path)
        
        # Converter tempo HH:MM:SS para segundos
        h, m, s = time.split(':')
        target_sec = int(h)*3600 + int(m)*60 + int(s)
        
        # Calcular frame alvo
        fps = cap.get(cv2.CAP_PROP_FPS)
        target_frame = int(target_sec * fps)
        
        # Posicionar no frame desejado
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError(f"Could not capture frame at {time}")
        
        # Salvar frame temporário
        temp_frame = os.path.join(output_dir, "temp_frame.jpg")
        cv2.imwrite(temp_frame, frame)
        
        # Gerar miniatura a partir do frame
        filename = os.path.basename(input_path)
        name, _ = os.path.splitext(filename)
        thumbnail_path = generate_thumbnail(
            input_path=temp_frame,
            output_dir=output_dir,
            size=(400, 400),
            quality=90
        )
        
        # Remover frame temporário
        os.remove(temp_frame)
        
        logger.info(f"Video thumbnail generated: {thumbnail_path}")
        return thumbnail_path
    except Exception as e:
        logger.error(f"Error generating video thumbnail: {str(e)}")
        raise