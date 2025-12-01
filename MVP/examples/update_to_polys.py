import json
import os

INPUT_PATH = "../../../data/OCR_output/COO_OCR_updated/"

def convert_to_polys(dims):
    poly = [
        [dims[0], dims[1]],
        [dims[2], dims[1]],
        [dims[2], dims[3]],
        [dims[0], dims[3]],
    ]
    return poly

for folder in sorted(os.listdir(INPUT_PATH)):
    folder_path = os.path.join(INPUT_PATH, folder)
    filenames = os.listdir(folder_path)

    for filename in filenames:
        file_path = os.path.join(folder_path, filename)

        with open(file_path, "r") as fp:
            ocr_results = json.load(fp)[0]
            polys = []
            for dims in ocr_results["rec_boxes"]:
                poly = convert_to_polys(dims=dims)
                polys.append(poly)            
            ocr_results["dt_polys"] = polys
            ocr_results = [ocr_results]

        with open(file_path, "w") as fp:
            json.dump(ocr_results, fp)  
