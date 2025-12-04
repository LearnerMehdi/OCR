## Overview

**This repository contains a local Gradio-based MVP that calls a remote FastAPI + PaddleOCR server to extract text from images and then applies rule-based Key Information Extraction (KIE) tailored for Certificates of Origin (COO).**  
The local app does **not** run the OCR model itself; it only sends image payloads to the remote OCR server, processes the OCR response, and finally saves cleaned key information to MongoDB.

- **MVP UI**: `MVP/app/app.py` (runs locally with Gradio)
- **Remote OCR server**: `MVP/app/server/server.py` (runs on a remote VM only)
- **KIE / filtering utilities**: `MVP/utils/filtering/filter_texts.py`
- **MongoDB helper**: `MVP/utils/database_management/mongo.py`
- **COO layout configuration**: `MVP/config/config.py` (`CATEGORY_TO_BBOX`)

---

## Example use cases

- **Local MVP run**: execute `python main.py` to launch the Gradio UI, upload a COO image, and receive filtered results that eventually persist to MongoDB.
- **Remote OCR server**: on the VM (path `~/server/server.py`), activate the appropriate virtual environment and start the service with `python server.py`; the local MVP must point to this endpoint (default `http://38.80.123.152:8000`).
- **Supplementary viewer**: `MVP/examples/viewer.py` visualizes PaddleOCR JSON output for a single document. Run `python viewer.py --image /path/to/image.png --json /path/to/result.json`. The JSON file must already exist (downloaded from the remote server) so the script can overlay recognized text, show pop-up translations, and display machine-readable strings on hover.

---

## Installation guide

### Local environment

1. Create or activate a Python virtual environment of your choice (Python 3.10+ recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the Gradio MVP:

```bash
python main.py
```

### Remote environment

- The VM already contains a virtual environment named `venv_paddle` (located at `~/venv_paddle`). Activate it:

```bash
source ~/venv_paddle/bin/activate
```

- Navigate to the server directory (e.g., `~/server/`) and start the OCR API:

```bash
python server.py
```

---

## MongoDB setup

- Use the `SimpleMongoManager` in `MVP/utils/database_management/mongo.py` to configure your connection.
- Decide whether to target:
  - A **local MongoDB instance** (default URI `mongodb://localhost:27017/`), or
  - A **remote MongoDB deployment** (provide full connection URI, credentials, and networking access).
- Choose or create the database (e.g., `OCR`) and collection (e.g., `OCR_results`). Update the connection string, `database_name`, and `collection_name` accordingly before running the MVP.
- Ensure the Mongo server is running before saving data. Example Docker command for local testing:

```bash
docker run -d -p 27017:27017 --name mongo mongo
```

---

## End-to-end workflow

- **1. Image upload (local MVP)**
  - The user uploads a **single image file** (JPEG, JPG, PNG, etc.) via the Gradio UI.
  - The MVP currently supports **only one image at a time** and does **not** support PDFs or multi-page documents.

- **2. Send image to remote OCR server**
  - The local app converts the image to **base64** and sends it as JSON payload to the remote server:
    - Default base URL (at the time of writing): `http://38.80.123.152:8000`
    - Endpoint: `/ocr`
  - The remote server in `server.py` runs a **lightweight PaddleOCR model** on a GPU-backed VM.

- **3. OCR response schema**
  - The FastAPI endpoint returns a JSON response of the form:

```text
{
  "results": [
    {
      "rec_texts": List[str, ...],
      "rec_boxes": List[List[int, ...], ...],
      "rec_scores": List[float, ...],
      "dt_polys": List[List[int, ...], ...],
      "image_dims": [H, W, C]
    }
  ],
  "status": "success"
}
```

  - Where:
    - **`rec_texts`**: recognized text strings per detected region.
    - **`rec_boxes`**: bounding boxes for each recognized text (as integer coordinates).
    - **`rec_scores`**: confidence scores from PaddleOCR for each recognized text.
    - **`dt_polys`**: detection polygons.
    - **`image_dims`**: image dimensions used during inference.

    **`rec_texts`**, **`rec_boxes`**, **`rec_scores`**, and **`dt_polys`** contain information for all detections as lists. They should have the same size - the number of elements in the list.


- **4. COO-specific KIE (local rule-based filtering)**
  - For the MVP, **only Certificates of Origin (COO)** documents are supported.
  - The KIE logic uses **positional search** based on normalized bounding boxes stored in `CATEGORY_TO_BBOX` inside `MVP/config/config.py`:
    - Each entry is of the form:  
      `x, y, width, height` in the range \([0.0, 1.0]\).
    - Example:

      ```text
      CATEGORY_TO_BBOX = {
        "country": [0.5158, 0.2448, 0.4060, 0.0700],
        "items":   [0.0656, 0.4990, 0.6134, 0.2150],
        "weight":  [0.6824, 0.4658, 0.2382, 0.2482]
      }
      ```

  - Depending on the **image shape** and OCR layout, the code maps these normalized coordinates back to pixel coordinates to locate the approximate regions where:
    - **Country of origin** (e.g., “Turkey", "Italy", "France") is expected.
    - **Items / description of goods** are listed.
    - **Weights / quantities** are printed.

- **5. Text cleaning and rule-based extraction**
  - Within the region for each category, rule-based logic (mostly in `filter_texts.py`) uses:
    - **Regular expressions** to:
      - Normalize numbers and decimal separators.
      - Detect weight values and units (e.g., `KG`, `KGS`).
      - Clean noisy OCR outputs.
    - **Heuristics and language-aware rules** to:
      - Extract and normalize country names.
      - Identify individual item descriptions.
      - Resolve multiple candidate hits where possible.

- **6. Saving results to MongoDB**
  - Cleaned results (e.g., countries, items, weights, source metadata) are saved into a **MongoDB** collection using `SimpleMongoManager` in `mongo.py`.
  - By default, this assumes a **local MongoDB** instance (see example in `mongo.py`) and stores:
    - The extracted fields (countries, items, weights, etc.).
    - A `created_at` timestamp.
    - Optional additional metadata such as source file name.

---

## Remote OCR server (FastAPI + PaddleOCR)

The OCR service that runs the Paddle model is implemented in `MVP/app/server/server.py` and is intended to run **only on a remote VM** (not as part of the local app).

- **Core endpoint**:

```text
POST /ocr
```

- **Request body** (`OCRRequest`):
  - `image`: base64-encoded image.
  - `model_name`: optional string for future model selection (default `"default"`).

  Currently the parameter `model_name` does nothing. For the future, it is intended to give the user few options to select a model from a dropdown menu in the gradio-based application. 

- **Response** (`OCRResponse`):
  - `results`: list of OCR results, each containing `rec_texts`, `rec_boxes`, `rec_scores`, `dt_polys`, and `image_dims`.
  - `status`: `"success"` when inference completes without error.

The server also exposes a **health-check** endpoint:

```text
GET /health
```

which returns a JSON payload similar to:

```text
{
  "status": "Model loaded and ready",
  "model_config": {
    "use_doc_orientation_classify": false,
    "use_doc_unwarping": false,
    "use_textline_orientation": false
  }
}
```

---

## Network and firewall notes

- The remote server was configured to accept incoming connections from **NAIC (Landmark)** and **DLP** offices.
- Before using the MVP:
  - Ensure the VM’s firewall / security rules allow inbound traffic from your **current IP address**.
  - You can check your public IP with:

```bash
curl icanhazip.com
```

- To verify that the OCR server is alive and reachable:

```bash
curl http://38.80.123.152:8000/health
```

- If you get timeouts or no response:
  - First verify your internet connectivity.
  - Then confirm that the VM firewall allows your IP.
  - Finally, ensure the FastAPI application in `server.py` is running on the remote machine and not blocked by additional firewall rules.

> **Important**: If the IP address of the OCR server changes, you must update the URL used in the Gradio app (`MVP/app/app.py`) accordingly.

---

## Running the MVP locally (high-level)

At a high level, running the MVP requires:

- **Local environment**
  - Python environment with dependencies for:
    - Gradio
    - `requests`
    - `pymongo`
    - Any utility libraries used in `filter_texts.py` and `mongo.py`
  - A reachable **MongoDB instance**, usually on `mongodb://localhost:27017/` for development.

- **Remote environment**
  - A VM with GPU resources and the following installed:
    - Python, `fastapi`, `uvicorn`, `paddleocr`, `pydantic`, and dependencies in `server.py`.
  - `server.py` must be started on the VM, e.g.:

```bash
python MVP/app/server/server.py
```

The local Gradio app is then started (e.g. via `main.py` or `MVP/app/app.py`), and it communicates with the remote `/ocr` endpoint.

---

## Scope and limitations

- **Designed for Certificates of Origin (COO) only** in this MVP.
- **Positional rules (`CATEGORY_TO_BBOX`) are tuned** for the specific COO layout used during development.
- **No PDF or multi-page support** at this stage.

---

## Known limitation

The Gradio JSON output currently shows **one confidence score per key (country, items, weight)** even when multiple text snippets exist under that key. PaddleOCR actually returns confidence per detected text, so the UI hides the per-text granularity and may misrepresent reliability until this bug is fixed.

![Screenshot of current Gradio response showing a single confidence value per key](images/response.png)

---

## Future approaches

- We plan to replace rule-based positional search and regex filters with **Semantic Entity Recognition (SER)** powered by PaddleNLP/PaddleOCR’s KIE stack, following the approach documented in PaddleOCR’s KIE guide.[^1]
- This should improve robustness when extracting country, items, and weight, especially across varied COO templates.

### Compatibility challenges

- PaddleNLP SER pipelines require **PaddleNLP < 2.6**. So, I have attempted with `paddlenlp==2.5.2`, `paddlepaddle-gpu==2.4.2.post117`, and `paddleocr==2.7.2`. But not guaranteed if they work 100% properly.
- The remote server’s default Python 3.12 is incompatible with those versions, so:
  1. Use `pyenv` to switch to Python 3.10.0:

     ```bash
     pyenv shell 3.10.0
     ```

  2. Activate the SER-specific virtual environment:

     ```bash
     source ~/venv_310/bin/activate
     ```

  3. Follow the PaddleKIE instructions for inference. Example (this will currently raise errors until dependencies are finalized, but serves as a template):

     ```bash
     # go inside PaddleOCR repo on VM
     cd PaddleOCR
     
     # run inference
     python3 tools/infer_kie_token_ser.py \
       -c configs/kie/vi_layoutxlm/ser_vi_layoutxlm_xfund_zh.yml \
       -o Architecture.Backbone.checkpoints=./pretrained_model/ser_vi_layoutxlm_xfund_pretrained/best_accuracy \
       Global.infer_img=~/images/image.png
     ```

- A sample COO image is stored on the VM for experimentation, but expect runtime issues until the dependency constraints above are fully resolved.

[^1]: PaddleOCR KIE documentation – <https://github.com/PaddlePaddle/PaddleOCR/blob/main/ppstructure/kie/README.md>

- Check out Paddle versions:

  ```bash
  (venv_310) ubuntu@ambitious-bohr:~$ pip freeze | grep paddle
  paddle-bfloat==0.1.7
  paddle2onnx==2.0.1
  paddlefsl==1.1.0
  paddlenlp==2.5.2
  paddleocr==2.7.2
  paddlepaddle-gpu==2.4.2.post117
  ```

- Current error occurs:

  ```bash
  (venv_310) ubuntu@ambitious-bohr:~/PaddleOCR$ python3 tools/infer_kie_token_ser.py \
    -c configs/kie/vi_layoutxlm/ser_vi_layoutxlm_xfund_zh.yml \
    -o Architecture.Backbone.checkpoints=./pretrained_model/ser_vi_layoutxlm_xfund_pretrained/best_accuracy \
    Global.infer_img=../images/image.png
  W1203 09:46:38.052230  8109 init.cc:182] Compiled with WITH_GPU, but no GPU found in runtime.
  /home/ubuntu/venv_310/lib/python3.10/site-packages/paddle/fluid/framework.py:634: UserWarning: You are using GPU version Paddle, but your CUDA device is not set properly. CPU device will be used by default.
    warnings.warn(
  Skipping import of the encryption module.
  Traceback (most recent call last):
    File "/home/ubuntu/PaddleOCR/tools/infer_kie_token_ser.py", line 126, in <module>
      config, device, logger, vdl_writer = program.preprocess()
    File "/home/ubuntu/PaddleOCR/tools/program.py", line 913, in preprocess
      device = paddle.set_device(device)
    File "/home/ubuntu/venv_310/lib/python3.10/site-packages/paddle/device/__init__.py", line 316, in set_device
      place = _convert_to_place(device)
    File "/home/ubuntu/venv_310/lib/python3.10/site-packages/paddle/device/__init__.py", line 263, in _convert_to_place
      place = core.CUDAPlace(device_id)
  OSError: (External) CUDA error(100), no CUDA-capable device is detected. 
    [Hint: Please search for the error code(100) on website (https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__TYPES.html#group__CUDART__TYPES_1g3f51e3575c2178246db0a94a430e0038) to get Nvidia's official solution and advice about CUDA Error.] (at /paddle/paddle/phi/backends/gpu/cuda/cuda_info.cc:66)
  ```

- The reason for this error is the missing CUDA drivers. 
  ```bash
    source venv_ubuntu@ambitious-bohr:~$ source venv_310/bin/activate
    (venv_310) ubuntu@ambitious-bohr:~$ pip3 freeze | grep nvidia
    (venv_310) ubuntu@ambitious-bohr:~$ 
  ```
  
- Which is not the case with latest releases:

  ```bash
    ubuntu@ambitious-bohr:~$ source venv_paddle/bin/activate
    (venv_paddle) ubuntu@ambitious-bohr:~$ pip freeze | grep nvidia
    nvidia-cublas-cu12==12.6.4.1
    nvidia-cuda-cccl-cu12==12.6.77
    nvidia-cuda-cupti-cu12==12.6.80
    nvidia-cuda-nvrtc-cu12==12.6.77
    nvidia-cuda-runtime-cu12==12.6.77
    nvidia-cudnn-cu12==9.5.1.17
    nvidia-cufft-cu12==11.3.0.4
    nvidia-cufile-cu12==1.11.1.6
    nvidia-curand-cu12==10.3.7.77
    nvidia-cusolver-cu12==11.7.1.2
    nvidia-cusparse-cu12==12.5.4.2
    nvidia-cusparselt-cu12==0.6.3
    nvidia-nccl-cu12==2.25.1
    nvidia-nvjitlink-cu12==12.6.85
    nvidia-nvtx-cu12==12.6.77
  ```
