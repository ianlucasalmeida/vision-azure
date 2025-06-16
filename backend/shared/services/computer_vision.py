from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
import os

def get_vision_client():
    endpoint = os.getenv("VISION_ENDPOINT")
    key = os.getenv("VISION_KEY")
    return ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))

def analyze_image(image_stream):
    client = get_vision_client()
    features = [VisualFeatureTypes.tags, VisualFeatureTypes.description]
    analysis = client.analyze_image_in_stream(image_stream, visual_features=features)
    
    return {
        "tags": [tag.name for tag in analysis.tags],
        "description": analysis.description.captions[0].text if analysis.description.captions else ""
    }