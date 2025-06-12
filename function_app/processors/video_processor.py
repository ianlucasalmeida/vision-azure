# /vision-azure/function_app/processors/video_processor.py
import moviepy.editor as mp
import os
import random
import tempfile

def extract_frame(input_path, second=None):
    """
    Extrai um único frame de um vídeo em um segundo específico ou aleatório.
    :param input_path: Caminho do arquivo de vídeo original.
    :param second: O segundo do qual extrair o frame. Se None, um tempo aleatório é escolhido.
    :return: Caminho da imagem do frame extraído.
    """
    base_name = os.path.basename(input_path).rsplit('.', 1)[0]
    output_path = os.path.join(tempfile.gettempdir(), f"{base_name}_frame.jpg")

    with mp.VideoFileClip(input_path) as video:
        duration = video.duration
        target_time = second if second is not None else random.uniform(0, duration)
        
        # Garante que o tempo alvo não ultrapasse a duração do vídeo
        if target_time > duration:
            target_time = duration
            
        video.save_frame(output_path, t=target_time)
        
    return output_path