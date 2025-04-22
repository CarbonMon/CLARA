from typing import List, Dict, Any, Optional, Union, BinaryIO
import logging
from openai import OpenAI
from anthropic import Anthropic
from app.utils.openai_utils import analyze_paper_with_openai
from app.utils.claude_utils import analyze_paper_with_claude
from app.utils.pubmed_utils import search_and_fetch_pubmed
from app.utils.pdf_utils import process_file

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for analyzing papers from PubMed or PDFs"""
    
    def __init__(self, client: Union[OpenAI, Anthropic], provider: str = "openai", model: str = None):
        self.client = client
        self.provider = provider.lower()
        self.model = model
    
    def analyze_pubmed_papers(self, query: str, max_results: int, action: str = "new") -> List[Dict[str, Any]]:
        """
        Search PubMed and analyze papers
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results
            action: "new" to start fresh or "append" to existing results
            
        Returns:
            List of analyzed papers
        """
        papers = search_and_fetch_pubmed(query, max_results)
        if 'PubmedArticle' not in papers or not papers['PubmedArticle']:
            logger.warning("No papers found for query: %s", query)
            return []

        results = []
        for paper in papers['PubmedArticle']:
            try:
                if self.provider == "openai":
                    result = analyze_paper_with_openai(
                        self.client, 
                        paper, 
                        is_pdf=False,
                        model=self.model
                    )
                else:  # anthropic
                    result = analyze_paper_with_claude(
                        self.client, 
                        paper, 
                        is_pdf=False,
                        model=self.model
                    )
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing paper: {e}")
                # Add error record
                results.append({
                    "Title": "Error analyzing paper",
                    "Error": str(e)
                })

        return results
    
    def analyze_pdf_files(
        self, 
        pdf_files: List[Any], 
        use_ocr: bool = False, 
        language: str = "eng", 
        action: str = "new"
    ) -> List[Dict[str, Any]]:
        """
        Process and analyze PDF files
        
        Args:
            pdf_files: List of PDF file objects
            use_ocr: Whether to use OCR
            language: Language code for OCR
            action: "new" to start fresh or "append" to existing results
            
        Returns:
            List of analyzed papers
        """
        results = []
        pdf_texts = []
        
        for pdf_file in pdf_files:
            try:
                # Process the file
                processed_file = process_file(pdf_file, use_ocr, language)
                
                # Store extracted text
                pdf_texts.append({
                    'filename': processed_file['filename'],
                    'content': processed_file['content']
                })
                
                # Analyze the PDF content
                if self.provider == "openai":
                    result = analyze_paper_with_openai(
                        self.client, 
                        processed_file['content'], 
                        is_pdf=True,
                        model=self.model
                    )
                else:  # anthropic
                    result = analyze_paper_with_claude(
                        self.client, 
                        processed_file['content'], 
                        is_pdf=True,
                        model=self.model
                    )
                # Add filename to result
                result['Filename'] = pdf_file.name
                results.append(result)
            
            except Exception as e:
                logger.error(f"Error processing PDF: {e}")
                # Add error record
                results.append({
                    "Title": f"Error processing {pdf_file.name}",
                    "Filename": pdf_file.name,
                    "Error": str(e)
                })
        
        return results
