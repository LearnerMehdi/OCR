import json
import os
from PIL import Image

from MVP.utils.filtering import filter_text

def find_match(filename: str, files: str):

    for file in files:
        if filename[:-5] in file:
            return file


INPUT_PATH = "../data/OCR_output/COO_OCR"
IMAGE_PATH = "../data/all_documents/COO_OCR"

for folder in sorted(os.listdir(INPUT_PATH)):
    folder_path = os.path.join(INPUT_PATH, folder)
    image_path = os.path.join(IMAGE_PATH, folder)
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        output_path = os.path.join("../data/OCR_output/COO_output", filename)
        
        with open(file_path, "r") as fp:
            ocr_results = json.load(fp)[0]
            image_filename = find_match(filename, os.listdir(image_path))
            image_file_path = os.path.join(image_path, image_filename)

            image_dims = Image.open(image_file_path).size
            image_dims = image_dims[::-1]

            info_extracted = filter_text(ocr_results=ocr_results, image_dims=image_dims)
            
            results = {
                "path": file_path,
                "info": info_extracted
            }
        
        with open(output_path, "w") as fp:
            json.dump(results, fp)