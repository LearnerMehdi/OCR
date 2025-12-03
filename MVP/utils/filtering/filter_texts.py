from typing import Dict, Tuple
import re

from MVP.config import CATEGORY_TO_BBOX

# Reference headlines in different languages for item descriptions
# These are the standard headers that should be filtered out
ITEM_HEADLINES = {
    'turkish': [
        'Sıra No; kolilerin marka ve işaretleri, sayı ve türleri; eşyanın tanımı',
        'Sıra No kolilerin marka ve işaretleri sayı ve türleri eşyanın tanımı',
        'Item number marks numbers number and kind of packages description of goods',
        'Item number; marks, numbers, number and kind of packages; description of goods',
    ],
    'english': [
        'Item number; marks, numbers, number and kind of packages; description of goods',
        'Item number marks numbers number and kind of packages description of goods',
        'Item number; marks numbers number and kind of packages; description of goods',
    ],
    'french': [
        "Numéro d'ordre – Marques, numéros, nombre et nature des colis – Désignation des marchandises",
        "Numero d'ordre Marques numeros nombre et nature des colis Designation des marchandises",
        "Numéro d'ordre - Marques, numéros, nombre et nature des colis - Désignation des marchandises",
    ],
    'italian': [
        'Numero d\'ordine - Marchi, numeri, numero e tipo di colli - Designazione delle merci',
        'Numero ordine Marchi numeri numero tipo colli Designazione merci',
    ],
    'polish': [
        'Numer pozycji - Znaki, numery, liczba i rodzaj opakowań - Oznaczenie towarów',
        'Numer pozycji Znaki numery liczba rodzaj opakowan Oznaczenie towarow',
    ],
    'german': [
        'Laufende Nummer - Zeichen und Nummern, Anzahl und Art der Packstücke - Warenbezeichnung',
        'Laufende Nummer Zeichen Nummern Anzahl Art Packstucke Warenbezeichnung',
    ],
    'spanish': [
        'Número de orden - Marcas, números, cantidad y tipo de bultos - Designación de mercancías',
        'Numero orden Marcas numeros cantidad tipo bultos Designacion mercancias',
    ]
}

# Map countries to their primary languages
COUNTRY_TO_LANGUAGE = {
    'TURKEY': 'turkish',
    'FRANCE': 'french',
    'ITALY': 'italian',
    'POLAND': 'polish',
    'GERMANY': 'german',
    'SPAIN': 'spanish',
    'PORTUGAL': 'spanish',  # Similar enough
    'NETHERLANDS': 'english',  # Often use English
    'BELGIUM': 'french',  # French or Dutch, use French
    'AUSTRIA': 'german',
    'SWITZERLAND': 'german',  # Or French, use German
    'CZECH REPUBLIC': 'english',
    'HUNGARY': 'english',
    'ROMANIA': 'english',
    'BULGARIA': 'english',
    'GREECE': 'english',
    'CROATIA': 'english',
    'SERBIA': 'english',
    'UKRAINE': 'english',
    'RUSSIA': 'english',
    # Add more as needed
}

# Country code mapping
COUNTRY_CODES = {
    'PL': 'POLAND', 'TH': 'THAILAND', 'CN': 'CHINA', 'TR': 'TURKEY',
    'FR': 'FRANCE', 'IT': 'ITALY', 'DE': 'GERMANY', 'ES': 'SPAIN',
    'US': 'USA', 'GB': 'UK', 'JP': 'JAPAN', 'KR': 'SOUTH KOREA',
    'IN': 'INDIA', 'BR': 'BRAZIL', 'MX': 'MEXICO', 'CA': 'CANADA',
    'AU': 'AUSTRALIA', 'RU': 'RUSSIA', 'NL': 'NETHERLANDS', 'BE': 'BELGIUM',
    'AT': 'AUSTRIA', 'CH': 'SWITZERLAND', 'SE': 'SWEDEN', 'NO': 'NORWAY',
    'DK': 'DENMARK', 'FI': 'FINLAND', 'PT': 'PORTUGAL', 'GR': 'GREECE',
    'IE': 'IRELAND', 'CZ': 'CZECH REPUBLIC', 'HU': 'HUNGARY', 'RO': 'ROMANIA',
    'VN': 'VIETNAM', 'TW': 'TAIWAN', 'SG': 'SINGAPORE', 'MY': 'MALAYSIA',
    'PH': 'PHILIPPINES', 'ID': 'INDONESIA', 'AE': 'UAE', 'SA': 'SAUDI ARABIA',
}

# Labels to remove for countries
COUNTRY_LABELS = [
    'menşe ülkesi', 'mense', 'ulkesi', 'country of origin', "pays d'origine",
    'menşe', 'ülkesi', 'origin', 'country', 'pays', "d'origine",
    'made in', 'from', 'source'
]

# Labels to remove for weights
WEIGHT_LABELS = [
    'miktar', 'quantity', 'quantité', 'ilość', 'weight', 'ağırlık'
]


def filter_text(ocr_results: Dict, image_dims: Tuple):
    """
    The whole pipeline to filter the outputs from Paddle OCR.
    
    Args:
        ocr_results: Dictinoary of texts and bboxes.
        image_dims: a tuple of width and height - image dimensions

    """
    height, width = image_dims
    for key, values in CATEGORY_TO_BBOX.items():
        # print(key.upper())
        x1, y1, w, h = values
        x2 = x1 + w
        y2 = y1 + h


        x1 = int(x1 * width)
        x2 = int(x2 * width)

        y1 = int(y1 * height)
        y2 = int(y2 * height)

        query_bbox = [x1, y1, x2, y2]
        key_bboxes = query_ocr_region(query_bbox=query_bbox, ocr_results=ocr_results, iok_threshold=0.7)
        if key == "country":
            countries = extract_countries(ocr_results=key_bboxes)
        
        elif key == "weight":
            weights = extract_weights(ocr_results=key_bboxes)

        elif key == "items":
            items = extract_items(ocr_results=key_bboxes)

    info_extracted = {
        "country": countries,
        "weight": weights,
        "item": items,    
    }
    return info_extracted

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
    scores = ocr_results["rec_scores"]
    for bbox, text, score in zip(bboxes, texts, scores):
        iok = calculate_iok(query_bbox, bbox)
        
        if iok >= iok_threshold:
            matches.append({
                "bbox": bbox,
                "text": text,
                "score": score,
                "iok": iok
            })
    
    # Sort by position: top-to-bottom, then left-to-right
    matches.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
    
    return matches


def extract_countries(ocr_results: Dict):
    """
    Extract country names from a list of text strings.
    
    Args:
        ocr_results: Dictionary of texts and bboxes.
    
    Returns:
        List of country names (uppercase)
    """
    countries = []
    score = None

    for res in ocr_results:
        text = res["text"]
        score = res["score"]

        if not text or len(text.strip()) < 2:
            continue
        
        text = text.strip()
        
        # Remove numbering like "7." only if followed by space or end
        text = re.sub(r'^\d+\.\s+', '', text)
        text = re.sub(r'^\d+\.$', '', text)
        
        # Remove country labels
        for label in COUNTRY_LABELS:
            text = re.sub(label, '', text, flags=re.IGNORECASE)
        
        # Remove colons and forward slashes
        text = re.sub(r'[:/]', ' ', text)
        
        # Split by delimiters
        parts = re.split(r'[,;\-|]', text)
        
        for part in parts:
            part = part.strip().upper()
            
            if not part or len(part) < 2:
                continue
            
            # Convert 2-letter codes
            if len(part) == 2 and part.isalpha():
                if part in COUNTRY_CODES:
                    countries.append(COUNTRY_CODES[part])
                else:
                    countries.append(part)
            else:
                countries.append(part)
    
    return {
        "country": countries,
        "score": score
        }


def extract_weights(ocr_results: Dict):
    """
    Extract weight values from a list of text strings.
    
    Args:
        ocr_results: Dictionary of texts and bboxes.
    
    Returns:
        List of tuples (value, unit) e.g. [('5236.00', 'KG'), ('850.00', 'KG')]
    """
    weights = []
    score = None

    for res in ocr_results:
        text = res["text"]
        score = res["score"]
        if not text or len(text.strip()) < 2:
            continue
        
        text = text.strip()
        
        # Remove numbering like "7." only if followed by space or end
        text = re.sub(r'^\d+\.\s+', '', text)
        text = re.sub(r'^\d+\.$', '', text)
        
        # Remove weight labels
        for label in WEIGHT_LABELS:
            text = re.sub(r'\b' + label + r'\b', '', text, flags=re.IGNORECASE)
        
        # Find all weight patterns
        pattern = r'([\d]+[.,\d]*)\s*(KG[S]?|G[S]?|LB[S]?|T[S]?|TON[S]?)\b'
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        
        for number_str, unit in matches:
            # Normalize the number format
            num_dots = number_str.count('.')
            num_commas = number_str.count(',')
            
            if num_commas > 0 and num_dots > 0:
                # Both present - determine which is decimal
                last_dot_pos = number_str.rfind('.')
                last_comma_pos = number_str.rfind(',')
                
                if last_comma_pos > last_dot_pos:
                    # European: 5.236,00 -> remove dots, replace comma with dot
                    number_str = number_str.replace('.', '').replace(',', '.')
                else:
                    # US: 5,236.00 -> remove commas
                    number_str = number_str.replace(',', '')
            elif num_commas > 0:
                # Only comma: European decimal separator
                number_str = number_str.replace(',', '.')
            # If only dots or neither, use as-is
            
            # Convert and store
            try:
                value = float(number_str)
                weights.append((f"{value:.2f}", unit.upper()))
            except ValueError:
                pass  # Skip if can't convert
    
    return {
        "weight": weights,
        "score": score
        }

def edit_distance(s1, s2):
    """
    Calculate Levenshtein distance between two strings.
    Simple implementation without external dependencies.
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        int: Edit distance between the strings
    """
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def normalize_text(text):
    """
    Normalize text for comparison: lowercase, remove extra spaces, punctuation.
    
    Args:
        text: Input text
    
    Returns:
        Normalized text
    """
    # Lowercase
    text = text.lower()
    # Remove special characters but keep letters, numbers, and spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_headline(text, threshold=0.3, languages=None):
    """
    Check if a text line is likely a headline/header using edit distance.
    
    Args:
        text: Text to check
        threshold: Similarity threshold (0-1). Lower = more strict.
                   0.3 means allow 30% difference
        languages: List of languages to check. If None, checks all languages.
                   Always includes 'english' regardless.
    
    Returns:
        bool: True if text matches a known headline pattern
    """
    if not text or len(text.strip()) < 10:
        return False
    
    normalized = normalize_text(text)
    
    # Determine which languages to check
    if languages is None:
        # Check all languages
        languages_to_check = ITEM_HEADLINES.keys()
    else:
        # Always include English + specified languages
        languages_to_check = set(languages)
        languages_to_check.add('english')
    
    # Check against headlines in the selected languages
    for language in languages_to_check:
        if language not in ITEM_HEADLINES:
            continue
            
        for headline in ITEM_HEADLINES[language]:
            normalized_headline = normalize_text(headline)
            
            # Calculate similarity
            distance = edit_distance(normalized, normalized_headline)
            max_len = max(len(normalized), len(normalized_headline))
            
            if max_len == 0:
                continue
            
            similarity = 1 - (distance / max_len)
            
            # If similarity is above threshold, it's a headline
            if similarity >= (1 - threshold):
                return True
    
    return False


def extract_items(ocr_results: Dict, countries=None, threshold=0.3):
    """
    Extract item descriptions by filtering out headlines/headers.
    
    Args:
        ocr_results: Dictionary of texts and bboxes.
        countries: Optional list of countries to determine which language headers to expect.
                   Always checks English regardless of countries.
        threshold: Similarity threshold for headline matching (0-1)
    
    Returns:
        List of item description strings (headlines filtered out)
    """
    # Determine which languages to check based on countries
    languages = None
    if countries:
        languages = set()
        for country in countries:
            # Normalize country name
            country_upper = country.upper()
            
            # Map country to language
            if country_upper in COUNTRY_TO_LANGUAGE:
                languages.add(COUNTRY_TO_LANGUAGE[country_upper])
            # If country not in mapping, it will still check English by default
        
        # Convert to list for passing to is_headline
        languages = list(languages) if languages else None
    
    items = []
    score = None
    
    for res in ocr_results:
        text = res["text"]
        score = res["score"]
        if not text or len(text.strip()) < 2:
            continue
        
        text = text.strip()
        
        # Skip if it's a headline (now using language filtering)
        if is_headline(text, threshold=threshold, languages=languages):
            continue
        
        # Skip if it's just a number (like "6." or "1")
        if re.match(r'^\d+\.?\s*$', text):
            continue
        
        # Skip if it's too short (likely not an item description)
        if len(text) < 3:
            continue
        
        # Keep this line as an item
        items.append(text)
    
    return {
        "item": items,
        "score": score
        }

