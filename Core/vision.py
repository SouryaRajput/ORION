import pytesseract
from PIL import Image
import base64
import requests
import os

pytesseract.pytesseract.tesseract_cmd = "/opt/local/bin/tesseract"

import re

def extract_text(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        
        # Aggressive cleanup of OCR garbage
        text = re.sub(r'[^a-zA-Z0-9.,?!\'\"\n\-\$ ]+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        if len(text) < 3:
            return "No readable text detected on screen."
            
        return text

    except Exception as e:
        print("[OCR ERROR]", e)
        return "I could not extract any text from the screen."

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_screen_with_llm(image_path, prompt="Summarize the main content of this screen in ONE extremely short sentence. Do NOT list items. Do NOT repeat yourself. Be concise."):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "I cannot analyze the screen because my API key is missing."
        
    base64_image = encode_image(image_path)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 50
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("[VISION API ERROR]", e)
        return "I am having trouble seeing the screen right now."