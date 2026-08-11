import logging
from pathlib import Path

import pdfplumber
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


class OcrService:
    def extract_text(self, file_path: Path, content_type: str) -> str:
        if content_type == "application/pdf":
            text = self._extract_pdf_text(file_path)
            if text:
                return text
            return self._ocr_scanned_pdf(file_path)
        return self._ocr_image(file_path)

    def _extract_pdf_text(self, file_path: Path) -> str:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
        return text

    def _ocr_image(self, file_path: Path) -> str:
        try:
            import pytesseract

            image = Image.open(file_path)
            image = self._preprocess_image(image)
            return pytesseract.image_to_string(image).strip()
        except Exception as exc:
            logger.info("Image OCR unavailable, falling back to byte decoding: %s", exc)
            return file_path.read_bytes().decode("utf-8", errors="ignore").strip()

    def _ocr_scanned_pdf(self, file_path: Path) -> str:
        try:
            import pypdfium2 as pdfium
            import pytesseract

            pdf = pdfium.PdfDocument(file_path)
            pages: list[str] = []
            for page_index in range(min(len(pdf), 5)):
                page = pdf[page_index]
                bitmap = page.render(scale=2).to_pil()
                pages.append(pytesseract.image_to_string(self._preprocess_image(bitmap)))
            return "\n".join(page.strip() for page in pages if page.strip()).strip()
        except Exception as exc:
            logger.info("Scanned PDF OCR unavailable: %s", exc)
            return ""

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("L")
        if image.width < 1400:
            ratio = 1400 / image.width
            image = image.resize((1400, int(image.height * ratio)))
        return ImageOps.autocontrast(image)
