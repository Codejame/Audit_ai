"""OCR and document rendering service for native and scanned documents."""
import io
import os
from typing import List, Tuple
from PIL import Image
import fitz  # PyMuPDF
from backend.app.core.logging import logger

class OCRService:
    @staticmethod
    def extract_text_and_images(file_path_or_bytes: bytes, filename: str) -> Tuple[str, List[Image.Image], bool]:
        """
        Parses document to extract:
        1. Any native text present.
        2. A list of PIL Images (one per page) for multimodal analysis.
        3. Flag indicating whether OCR/vision processing was required.
        """
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        images: List[Image.Image] = []
        extracted_text_chunks: List[str] = []
        ocr_used = False

        if ext == "pdf":
            doc = fitz.open(stream=file_path_or_bytes, filetype="pdf")
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_text = page.get_text()
                if page_text and len(page_text.strip()) > 20:
                    extracted_text_chunks.append(f"--- Page {page_idx + 1} ---\n" + page_text)
                
                # Render high-resolution page image for vision model
                # 150 DPI provides great clarity with reasonable payload size
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images.append(img)
            doc.close()

            # If no native text extracted, OCR/vision is strictly required
            if not "".join(extracted_text_chunks).strip():
                ocr_used = True
            else:
                ocr_used = False

        elif ext in ("jpg", "jpeg", "png"):
            img = Image.open(io.BytesIO(file_path_or_bytes)).convert("RGB")
            images.append(img)
            ocr_used = True

        combined_text = "\n\n".join(extracted_text_chunks)
        logger.info(f"Document {filename} parsed: {len(images)} pages rendered, native text len: {len(combined_text)}, ocr_used: {ocr_used}")
        return combined_text, images, ocr_used
