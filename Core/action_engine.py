import pyautogui
import pytesseract
from PIL import Image
import time
import os

pytesseract.pytesseract.tesseract_cmd = "/opt/local/bin/tesseract"

def type_text(text):
    try:
        pyautogui.write(text, interval=0.05)
        return True
    except Exception as e:
        print("[ACTION ERROR] Typing:", e)
        return False

def press_key(key):
    try:
        pyautogui.press(key)
        return True
    except Exception as e:
        print("[ACTION ERROR] Key press:", e)
        return False

def click_text(target_text, image_path):
    try:
        img = Image.open(image_path)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        target_text_lower = target_text.lower()
        
        screen_width, screen_height = pyautogui.size()
        scale = 1
        
        # Handle Retina displays on macOS where screenshot resolution is 2x logical screen size
        if img.width > screen_width * 1.5:
            scale = 2
        
        best_match = None
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if not text:
                continue
                
            if target_text_lower in text.lower():
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                # Center coordinates
                center_x = (x + (w // 2)) / scale
                center_y = (y + (h // 2)) / scale
                
                # Move to and click
                pyautogui.moveTo(center_x, center_y, duration=0.3)
                pyautogui.click()
                return True
                
        return False
    except Exception as e:
        print("[ACTION ERROR] Click text:", e)
        return False
