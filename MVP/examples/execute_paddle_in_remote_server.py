import json
import requests
import base64
import re
import os

INPUT_PATH = "../data/all_documents/COO_OCR"
OUTPUT_PATH = "../data/OCR_output/COO_OCR"

VM_URL = "http://185.216.21.129:8000"


def image_to_base64(image_path):
    """Convert image file to base64 string"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def process_document(image_path):
    try:
        # Convert uploaded file to base64
        image_b64 = image_to_base64(image_path)

        # Prepare JSON payload
        payload = {
            "image": image_b64,
            "model_name": "PaddleOCR"
        }
        # Send request to remote server
        response = requests.post(f"{VM_URL}/ocr", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data['results']
            return results, True
            
        else:
            return f"Error: {response.status_code} - {response.text}", False
    
    except Exception as e:
        return f"Error: {str(e)}", ""

def main():
    hierarchy = os.walk(INPUT_PATH)
    _ = next(hierarchy)

    i = 1
    for path, _, filenames in hierarchy:

        folder = os.path.basename(path)
        folder_path = os.path.join(OUTPUT_PATH, folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        for filename in filenames:
            file_path = os.path.join(path, filename)
            new_filename = re.sub(r"^(.+)\.[^.]+$", r"\1" + ".json", filename)
            output_path = os.path.join(folder_path, new_filename)

            print(f"Processing the document {i}: {file_path}")
            results, is_ok = process_document(image_path=file_path)
            
            if not is_ok:
                results = []

            print(f"Status: {is_ok}")
            print(f"Saving results: {output_path}")
            
            with open(output_path, "w") as fp:  
                json.dump(results, fp)
            
            print()

            i += 1
            
main()