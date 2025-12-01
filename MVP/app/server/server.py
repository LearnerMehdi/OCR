# server.py (runs on VM)
from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from paddleocr import PaddleOCR
import uvicorn
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import cv2

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Example: Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model ONCE at startup with your specific configuration
print("Loading PaddleOCR model...")
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)
print("Model loaded and ready!")

# Define request schema
class OCRRequest(BaseModel):
    image: str  # base64 encoded image
    model_name: str = "default"  # for future model selection

# Define response schema
class OCRResponse(BaseModel):
    results: list
    status: str

@app.post("/ocr", response_model=OCRResponse)
async def perform_ocr(request: OCRRequest):
    try:
        # Decode base64 image to numpy array
        image_bytes = base64.b64decode(request.image)
        image = Image.open(BytesIO(image_bytes))
        image = np.asarray(image)

        if image.ndim !=3:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

        # Run OCR inference using your syntax
        result = ocr.predict(input=image)
        response = [
            {
            "rec_texts": item["rec_texts"],
            "rec_boxes": item["rec_boxes"].tolist(),
            "rec_scores": item["rec_scores"],
            "dt_polys": np.array(item["dt_polys"]).tolist(),
            "image_dims": image.shape
        } for item in result
        ]

        return {
            "results": response,
            "status": "success"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "Model loaded and ready",
        "model_config": {
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
