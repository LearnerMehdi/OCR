import json
import os

from MVP.utils.filtering import filter_text

INPUT_PATH = "../data/OCR_output/COO_OCR"

for folder in sorted(os.listdir(INPUT_PATH)):
    folder_path = os.path.join(INPUT_PATH, folder)
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        with open(file_path, "r") as fp:
            data = json.load(fp)
            
            