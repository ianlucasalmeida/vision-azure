# /vision-azure/function_app/processors/image_processor.py
from PIL import Image
import os
import tempfile

def change_format(input_path, new_format="jpeg"):
    """
    Converte o formato de uma imagem.
    :param input_path: Caminho do arquivo de imagem original.
    :param new_format: Novo formato desejado (ex: 'jpeg', 'png').
    :return: Caminho do arquivo convertido.
    """
    base_name = os.path.basename(input_path).rsplit('.', 1)[0]
    output_path = os.path.join(tempfile.gettempdir(), f"{base_name}.{new_format.lower()}")
    
    with Image.open(input_path) as img:
        # Garante que a imagem não tem canal alfa para formatos como JPEG
        if new_format.lower() == 'jpeg':
            img = img.convert("RGB")
        img.save(output_path, format=new_format.upper())
        
    return output_path

def convert_to_bw(input_path):
    """
    Converte uma imagem para preto e branco (escala de cinza).
    :param input_path: Caminho do arquivo de imagem original.
    :return: Caminho do arquivo convertido.
    """
    base_name = os.path.basename(input_path).rsplit('.', 1)[0]
    output_path = os.path.join(tempfile.gettempdir(), f"{base_name}_bw.jpg")
    
    with Image.open(input_path) as img:
        img.convert("L").save(output_path)
        
    return output_path