import io
import PyPDF2
import pdf2image
import pytesseract
from PIL import Image
from typing import Tuple, List, Dict, Any, BinaryIO
import logging

logger = logging.getLogger(__name__)

def convert_pdf_to_txt_file(pdf_file: BinaryIO) -> Tuple[str, int]:
    """
    Convert PDF to a single text file
    
    Args:
        pdf_file: PDF file object
        
    Returns:
        Tuple of (extracted_text, page_count)
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n\n"
        return text, len(pdf_reader.pages)
    except Exception as e:
        logger.error(f"Error converting PDF to text: {e}")
        raise

def images_to_txt(pdf_file: bytes, lang: str = 'eng') -> Tuple[List[str], int]:
    """
    Convert PDF to text using OCR
    
    Args:
        pdf_file: PDF file as bytes
        lang: Language code for OCR
        
    Returns:
        Tuple of (list_of_page_texts, page_count)
    """
    try:
        images = pdf2image.convert_from_bytes(pdf_file)
        texts = []
        for image in images:
            text = pytesseract.image_to_string(image, lang=lang)
            texts.append(text)
        return texts, len(images)
    except Exception as e:
        logger.error(f"Error performing OCR on PDF: {e}")
        raise

def process_file(file: Any, use_ocr: bool = False, language: str = 'eng') -> Dict[str, Any]:
    """
    Process a file (PDF or image) and extract text
    
    Args:
        file: File object
        use_ocr: Whether to use OCR
        language: Language code for OCR
        
    Returns:
        Dictionary with filename and extracted content
    """
    try:
        file_extension = file.name.split(".")[-1].lower()
        
        if hasattr(file, 'read'):
            file_content = file.read()
        else:
            # Handle the case where the file is already read
            with open(file, 'rb') as f:
                file_content = f.read()
        
        if file_extension == "pdf":
            if use_ocr:
                texts, page_count = images_to_txt(file_content, language)
                text_content = "\n\n".join(texts)
            else:
                text_content, page_count = convert_pdf_to_txt_file(io.BytesIO(file_content))
        elif file_extension in ["png", "jpg", "jpeg"]:
            pil_image = Image.open(io.BytesIO(file_content))
            text_content = pytesseract.image_to_string(pil_image, lang=language)
            page_count = 1
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
            
        return {
            'filename': file.name if hasattr(file, 'name') else file,
            'content': text_content,
            'page_count': page_count
        }
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise
