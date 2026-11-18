
import shutil
import re
import numpy as np
import cv2

from PIL import Image, ImageDraw, ImageFont

print("=== VERSIONS ===")

import PIL
print("OpenCV:", cv2.__version__)
print("Pillow:", PIL.__version__)

print("\n=== SYNTHETIC DOCUMENT ===")

image = Image.new("RGB", (1000, 300), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.load_default(size=64)

draw.text((50, 70), "AI PLATFORM 123", fill="black", font=font)
draw.text((50, 170), "INVOICE 2026", fill="black", font=font)

image_np = np.array(image)

assert image_np.shape == (300, 1000, 3)
print("Document:", image_np.shape)

print("\n=== OPENCV PREPROCESSING ===")

gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

denoised = cv2.GaussianBlur(gray, (3, 3), 0)

threshold = cv2.adaptiveThreshold(
    denoised,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    31,
    11,
)

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
morph = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)

assert gray.shape == (300, 1000)
assert threshold.shape == gray.shape
assert morph.shape == gray.shape

print("Grayscale, denoising, thresholding, morphology: PASSED")

print("\n=== OCR ENGINE ===")

tesseract_path = shutil.which("tesseract")

try:
    import pytesseract
    pytesseract_available = True
except ImportError:
    pytesseract_available = False

if tesseract_path and pytesseract_available:
    print("Tesseract:", tesseract_path)
    print("pytesseract:", pytesseract.get_tesseract_version())

    config = "--oem 3 --psm 6"

    recognized = pytesseract.image_to_string(
        morph,
        config=config,
    )

    print("Recognized text:")
    print(recognized)

    normalized = re.sub(
        r"[^A-Z0-9 ]",
        " ",
        recognized.upper(),
    )
    normalized = " ".join(normalized.split())

    assert "PLATFORM" in normalized
    assert "123" in normalized

    data = pytesseract.image_to_data(
        morph,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    words = [
        word for word in data["text"]
        if word.strip()
    ]

    boxes = [
        (
            data["left"][i],
            data["top"][i],
            data["width"][i],
            data["height"][i],
        )
        for i, word in enumerate(data["text"])
        if word.strip()
    ]

    assert len(words) > 0
    assert len(boxes) == len(words)

    print("Recognized words:", words)
    print("Bounding boxes:", len(boxes))

    print("OCR ENGINE TEST PASSED")

else:
    print("Tesseract executable:", tesseract_path)
    print("pytesseract available:", pytesseract_available)
    print("OCR ENGINE NOT AVAILABLE - OCR inference skipped")

print("\n=== DOCUMENT GEOMETRY ===")

contours, _ = cv2.findContours(
    255 - threshold,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE,
)

rectangles = [
    cv2.boundingRect(contour)
    for contour in contours
    if cv2.contourArea(contour) > 10
]

assert len(rectangles) > 0
print("Text candidate regions:", len(rectangles))

print("\nOCR PREPROCESSING TEST PASSED")

