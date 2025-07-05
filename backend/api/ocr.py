import cv2, pytesseract, tempfile, re
from PIL import Image
from typing import List, Dict

# ratios à ajuster si vous changez de résolution
CROP = dict(y1=0.12, y2=0.68, x1=0.40, x2=1.00)
WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#_ "

_line_re = re.compile(r"(.+?)\s+(\d+)\s+(\d+)\s+\d+")

def _preprocess(src: str) -> str:
    img = cv2.imread(src)
    h, w, _ = img.shape
    crop = img[int(CROP['y1']*h):int(CROP['y2']*h),
               int(CROP['x1']*w):int(CROP['x2']*w)]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    thr = cv2.adaptiveThreshold(gray, 255,
                                cv2.ADAPTIVE_THRESH_MEAN_C,
                                cv2.THRESH_BINARY_INV, 25, 15)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    cv2.imwrite(tmp.name, thr)
    return tmp.name

def _parse(text: str) -> List[Dict]:
    out = []
    for raw in text.splitlines():
        clean = " ".join(raw.strip().split())
        m = _line_re.match(clean)
        if m:
            name, kills, revs = m.groups()
            out.append({"gamertag": name,
                        "kills": int(kills),
                        "revives": int(revs)})
    return out

def extract(path: str) -> List[Dict]:
    prep = _preprocess(path)
    cfg = f"--psm 6 --oem 3 -c tessedit_char_whitelist={WHITELIST}"
    txt = pytesseract.image_to_string(Image.open(prep), config=cfg)
    return _parse(txt)
