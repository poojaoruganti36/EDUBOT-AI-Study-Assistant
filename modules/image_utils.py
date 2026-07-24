from PIL import Image
import pytesseract


def extract_text_from_image(image_file) -> str:
    image = Image.open(image_file)
    try:
        return pytesseract.image_to_string(image).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("OCR is unavailable because Tesseract is not installed or not on PATH.") from exc
