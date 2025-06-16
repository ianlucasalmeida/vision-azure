from PIL import Image, ImageOps
import os
import logging

logger = logging.getLogger(__name__)

def generate_thumbnail(input_path, output_dir, size=(200, 200), quality=85):
    try:
        # Garantir que o diretório de saída existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Carregar a imagem
        img = Image.open(input_path)
        
        # Criar miniatura mantendo a proporção
        img.thumbnail(size)
        
        # Criar nome do arquivo de saída
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_thumbnail.jpg"
        output_path = os.path.join(output_dir, output_filename)
        
        # Salvar em formato JPEG
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(output_path, "JPEG", quality=quality)
        
        logger.info(f"Thumbnail generated: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating thumbnail: {str(e)}")
        raise

def optimize_image(input_path, output_dir, quality=90):
    try:
        # Garantir que o diretório de saída existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Carregar a imagem
        img = Image.open(input_path)
        
        # Criar nome do arquivo de saída
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_optimized.jpg"
        output_path = os.path.join(output_dir, output_filename)
        
        # Otimizar e salvar
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(output_path, "JPEG", optimize=True, quality=quality)
        
        logger.info(f"Optimized image saved: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        raise