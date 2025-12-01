# client.py (runs on your local laptop)
import gradio as gr
import requests
import base64

from MVP.utils.filtering import filter_text
from MVP.utils.database_management import SimpleMongoManager

# Your VM's address (use localhost:8000 if using SSH tunnel)
VM_URL = "http://38.80.123.152:8000"


manager = SimpleMongoManager(
    connection_string="mongodb://localhost:27017/",
    database_name="OCR",
    collection_name="OCR"
)

def image_to_base64(image_path):
    """Convert image file to base64 string"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def process_document(file, model_choice):
    try:
        # Convert uploaded file to base64
        image_b64 = image_to_base64(file.name)
        
        # Prepare JSON payload
        payload = {
            "image": image_b64,
            "model_name": model_choice
        }
        
        # Send request to remote server
        response = requests.post(f"{VM_URL}/ocr", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data['results']
            
            infos = []
            for res in results:
                info_extracted = filter_text(res, image_dims=res["image_dims"][:-1])
                infos.append(info_extracted)
                
            manager.save_batch(infos)
            return infos
        else:
            return f"Error: {response.status_code} - {response.text}", ""
    
    except Exception as e:
        return f"Error: {str(e)}", ""

def run_app():
    # Create Gradio interface
    with gr.Blocks(title="OCR Document Processor") as interface:
        gr.Markdown("# 📄 OCR Document Processor")
        gr.Markdown("Upload an image to extract text using PaddleOCR")
        
        with gr.Row():
            with gr.Column():
                file_input = gr.File(label="Upload Document Image", file_types=["image"])
                model_dropdown = gr.Dropdown(
                    choices=["PaddleOCR", "PaddleStructure"], 
                    value="PaddleOCR",
                    label="Model Selection"
                )
                submit_btn = gr.Button("Process Document", variant="primary")
            
            with gr.Column():
                # text_output = gr.Textbox(label="Extracted Text", lines=15)
                # raw_output = gr.Textbox(label="Raw Results (JSON)", lines=10)
                text_output = gr.JSON(label="Raw Results (JSON)")
        submit_btn.click(
            fn=process_document,
            inputs=[file_input, model_dropdown],
            outputs=[text_output]
        )

    interface.launch(share=False)