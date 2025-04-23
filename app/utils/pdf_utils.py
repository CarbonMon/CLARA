import io
import PyPDF2
import pdf2image
import pytesseract
from PIL import Image
from typing import Tuple, List, Dict, Any, BinaryIO, Union
import logging
import os

logger = logging.getLogger(__name__)

def convert_pdf_to_txt_file(pdf_file: Union[BinaryIO, str]) -> Tuple[str, int]:
    """
    Convert PDF to a single text file
    
    Args:
        pdf_file: PDF file object or path to file
        
    Returns:
        Tuple of (extracted_text, page_count)
    """
    try:
        # If pdf_file is a string (filepath), open it
        if isinstance(pdf_file, str):
            with open(pdf_file, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n\n"
                return text, len(pdf_reader.pages)
        else:
            # Otherwise, assume it's already a file-like object
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"
            return text, len(pdf_reader.pages)
    except Exception as e:
        logger.error(f"Error converting PDF to text: {e}")
        raise

def images_to_txt(pdf_file: Union[bytes, str], lang: str = 'eng') -> Tuple[List[str], int]:
    """
    Convert PDF to text using OCR
    
    Args:
        pdf_file: PDF file as bytes or path to file
        lang: Language code for OCR
        
    Returns:
        Tuple of (list_of_page_texts, page_count)
    """
    try:
        # If pdf_file is a string (filepath), read it
        if isinstance(pdf_file, str):
            with open(pdf_file, 'rb') as f:
                pdf_content = f.read()
                images = pdf2image.convert_from_bytes(pdf_content)
        else:
            # Otherwise, assume it's already bytes
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
        file: File object or path to file
        use_ocr: Whether to use OCR
        language: Language code for OCR
        
    Returns:
        Dictionary with filename and extracted content
    """
    try:
        # Handle different file input types
        if isinstance(file, dict) and 'path' in file and 'name' in file:
            # This is a dict with path and name
            filepath = file['path']
            filename = file['name']
            file_extension = filename.split(".")[-1].lower()
            
            if file_extension == "pdf":
                if use_ocr:
                    texts, page_count = images_to_txt(filepath, language)
                    text_content = "\n\n".join(texts)
                else:
                    text_content, page_count = convert_pdf_to_txt_file(filepath)
            elif file_extension in ["png", "jpg", "jpeg"]:
                # For image files, we need to open them first
                with open(filepath, 'rb') as f:
                    pil_image = Image.open(f)
                    text_content = pytesseract.image_to_string(pil_image, lang=language)
                    page_count = 1
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
            return {
                'filename': filename,
                'content': text_content,
                'page_count': page_count
            }
            
        elif hasattr(file, 'read') and hasattr(file, 'name'):
            # This is a file-like object
            filename = os.path.basename(file.name)
            file_extension = filename.split(".")[-1].lower()
            
            # Store the file content so we don't lose it after reading
            file_content = file.read()
            
            if file_extension == "pdf":
                if use_ocr:
                    texts, page_count = images_to_txt(file_content, language)
                    text_content = "\n\n".join(texts)
                else:
                    # Create a new file-like object from the content
                    pdf_file = io.BytesIO(file_content)
                    text_content, page_count = convert_pdf_to_txt_file(pdf_file)
            elif file_extension in ["png", "jpg", "jpeg"]:
                pil_image = Image.open(io.BytesIO(file_content))
                text_content = pytesseract.image_to_string(pil_image, lang=language)
                page_count = 1
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
            return {
                'filename': filename,
                'content': text_content,
                'page_count': page_count
            }
            
        else:
            raise ValueError(f"Unsupported file object type: {type(file)}")
            
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise