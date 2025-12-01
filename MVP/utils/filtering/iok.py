import cv2
import numpy as np
from PIL import Image

def calculate_intersection(box1, box2):
    """Calculate intersection area between two boxes [x, y, w, h]"""
    box1_x1, box1_y1, box1_x2, box1_y2 = box1
    box2_x1, box2_y1, box2_x2, box2_y2 = box2
    
    # Find intersection boundaries
    x_left = max(box1_x1, box2_x1)
    y_top = max(box1_y1, box2_y1)
    x_right = min(box1_x2, box2_x2)
    y_bottom = min(box1_y2, box2_y2)
    
    # Check if there's an intersection
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    return (x_right - x_left) * (y_bottom - y_top)


def calculate_iok(query_box, ocr_box):
    """Calculate Intersection over Key (IoK)"""
    intersection = calculate_intersection(query_box, ocr_box)
    x1, y1, x2, y2 = ocr_box
    key_area = (x2 - x1) * (y2 - y1)
    
    if key_area == 0:
        return 0.0
    
    return intersection / key_area


def query_ocr_region(query_bbox, ocr_results, iok_threshold=0.5):
    """
    Query OCR results by bounding box region.
    
    Args:
        query_bbox: [x, y, w, h] - region of interest
        ocr_results: List[Dict["bbox": [x, y, w, h], "text": str]]
        iok_threshold: Minimum IoK to include result (default: 0.5)
    
    Returns:
        bboxes that highly inersect with query
    """
    matches = []

    bboxes = ocr_results["rec_boxes"]
    texts = ocr_results["rec_texts"]

    for bbox, text in zip(bboxes, texts):
        iok = calculate_iok(query_bbox, bbox)
        
        if iok >= iok_threshold:
            matches.append({
                "bbox": bbox,
                "text": text,
                "iok": iok
            })
    
    # Sort by position: top-to-bottom, then left-to-right
    matches.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
    
    return matches


def draw_and_show_boxes(pil_image, bboxes, window_name="Bounding Boxes"):
    """
    Draw bounding boxes on PIL image and display.
    
    Args:
        pil_image: PIL Image object
        bboxes: List of [x, y, w, h] or List of dicts with "bbox" key
        window_name: Window title for display
    """
    # Convert PIL to OpenCV format (RGB -> BGR)
    img_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    # Handle both formats: raw lists or dicts
    for bbox in bboxes:
        if isinstance(bbox, dict):
            x1, y1, x2, y2 = bbox["bbox"]
        else:
            x1, y1, x2, y2 = bbox
        
        # Draw rectangle (green color, thickness 2)
        cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Create resizable window (fits to screen automatically)
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # Display
    cv2.imshow(window_name, img_cv)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# Example usage
if __name__ == "__main__":

    import json
    # file = "Menshe"
    file = "ONCE _KLIMA_Mense"
    # file = "COO"
    # ROI = "items"
    ROI = "country"
    ROI = "weight"

    json_path = f"../paddle_ocr/{file}_page_1/{file}_page_1_res.json"
    image_path = f"../../../all_documents/pngs/{file}/{file}_page_1.png"

    data = json.load(open(json_path))
    image = Image.open(image_path)    

    # [x1, y1, x2, y2]

    # bbox_query = [875, 629, 1520, 815]
    image_width, image_height = image.size

    
    map_to_bboxes = {
        "country": [0.5158, 0.2448, 0.406, 0.07],
        "items": [0.0656, 0.499, 0.6134, 0.215],
        "weight": [0.6824, 0.4658, 0.2382, 0.2482]
    }

    x1, y1, width, height = map_to_bboxes[ROI]
    
    x2 = x1 + width
    y2 = y1 + height

    x1 = int(image_width * x1)
    x2 = int(image_width * x2)
    y1 = int(image_height * y1)
    y2 = int(image_height * y2)

    bbox_query = [x1, y1, x2, y2]
    bbox_keys = query_ocr_region(bbox_query, data, iok_threshold=0.7)

    draw_and_show_boxes(image, bbox_keys)