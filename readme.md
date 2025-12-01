# Introduction

The repository presents a gradio-based application to upload a document in image formats (JPEG, JPG, PNG, etc.) and send it to the remote server (current ip: http://38.80.123.152:8000) running on 80GB GPU with a Paddle OCR pipeline. 


* MVP -> [MVP](#MVP)
* Server -> [Server](#Server)
* More details about the fastapi-based server application -> [server](#Server). 



# MVP

The current MVP only accepts a single file and does not support PDFs or other formats. It converts images to base64 and send them as payloads to the remote server. A response from the server typically contains a dictionary of rectangle texts, rectangle boxes, rectangle scores, and detection polygons. The following is a schema of the successful response payload:
~~~{
    "results": [
            {
        "rec_texts": List[
                str, ...
            ],
        "rec_boxes": List[
                List[
                    int, ...
                ], ...
            ],
        "rec_scores": List[
                    float, ...
            ],
        "dt_polys": List[
                List[
                    int, ...
                ]
            ],
        },
    ]
    "status": "success"
}
~~~





# Server

## Note

Ip address of the server is assumed to be http://38.80.123.152:8000. Please, ensure that correct ip address is applied in case of a change.


## Firewall rules

By the time I left, the server has accepted the incoming connections from NAIC (Landmark) and DLP offices. Please, double-check the inbounding rules of the virtual machine on hyperstack.cloud and ensure that the server welcomes your current ip-address. Use the following command to see your own ip address.

~~~curl icanhazip.com
~~~

You are free to update inbounding rules with a new ip address. You are strongly advised to use ip address from the office for security reasons.


If the server is on, please do health-check applying this command on terminal.

~~~curl http://38.80.123.152:8000:/health
~~~

You should see an output like this.

~~~{"status": "Model loaded and ready", "model_config": { "use_doc_orientation_classify": False, "use_doc_unwarping": False, "use_textline_orientation": False}}
~~~

If no response for a certain period or timeout issue occurs, make sure you have a stable connection, first. If it is not the issue with internet, check out Firewall rules again and see if it does not intervene building connections with your current ip address. Finally, ensure that the fastapi-based application runs on the remote server with no strict firewall settings. 


## Script

The backbone of the remote server is happening here. It accepts a payload with image64 and processes it through an OCR pipeline. The method returns a dictionary with rectangle texts, rectangle boxes, rectangle scores, and detection polygons.

~~~@app.post("/ocr", response_model=OCRResponse)
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
        raise HTTPException(status_code=500, detail=str(e))~~~

The gradio-based application sends a request to http://38.80.123.152:8000:/ocr. 

The modified script from the line 36 at MVP/app/app.py:

~~~response = requests.post(http://38.80.123.152:8000:/ocr, json=payload)~~~