# /vision-azure/function_app/processors/slideshow_creator.py
import moviepy.editor as mp
import os
import random
import tempfile

def create_slideshow(image_paths, interval, is_random=False, output_name="slideshow"):
    """
    Cria um vídeo de slideshow a partir de uma lista de imagens.
    :param image_paths: Uma lista de caminhos para os arquivos de imagem.
    :param interval: O tempo em segundos que cada imagem deve aparecer.
    :param is_random: Se True, a ordem das imagens será aleatória.
    :param output_name: O nome base para o arquivo de vídeo de saída.
    :return: Caminho do vídeo de slideshow criado.
    """
    output_path = os.path.join(tempfile.gettempdir(), f"{output_name}.mp4")

    if is_random:
        random.shuffle(image_paths)

    # Cria um clipe de imagem para cada imagem com a duração definida
    clips = [mp.ImageClip(path).set_duration(interval) for path in image_paths]
    
    # Concatena todos os clipes de imagem em um único clipe de vídeo
    video_clip = mp.concatenate_videoclips(clips, method="compose")
    
    # Escreve o resultado em um arquivo de vídeo
    video_clip.write_videofile(output_path, fps=24, codec="libx264")
    
    return output_path