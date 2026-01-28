"""
Analysis Service - Core Analysis Logic
======================================

This service handles the analysis of papers from PubMed or PDFs.

Flow:
1. analyze_pubmed_papers() - Search PubMed and analyze each paper
2. analyze_pdf_files() - Process PDFs and analyze their content

Each analysis:
1. Gets paper content (abstract/full text)
2. Sends to AI (OpenAI or Claude) for structured extraction
3. Returns standardized result dictionary
"""

from typing import List, Dict, Any, Optional, Union
import logging
from openai import OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for analyzing papers from PubMed or PDFs"""
    
    def __init__(self, client: Union[OpenAI, Anthropic], provider: str = "openai", model: str = None):
        """
        Initialize the analysis service.
        
        Args:
            client: AI client (OpenAI or Anthropic)
            provider: 'openai' or 'anthropic'
            model: Model name to use
        """
        self.client = client
        self.provider = provider.lower()
        self.model = model
        logger.info(f"AnalysisService initialized: provider={provider}, model={model}")
    
    def analyze_pubmed_papers(
        self, 
        query: str, 
        max_results: int, 
        action: str = "new", 
        use_full_text: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed and analyze papers.
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results
            action: "new" to start fresh (reserved for future use)
            use_full_text: Whether to attempt full text retrieval
            
        Returns:
            List of analyzed paper dictionaries
        """
        logger.info(f"Starting PubMed analysis: query='{query}', max_results={max_results}")
        
        # Step 1: Search PubMed
        from app.utils.pubmed_utils import search_and_fetch_pubmed
        papers = search_and_fetch_pubmed(query, max_results)
        
        if 'PubmedArticle' not in papers or not papers['PubmedArticle']:
            logger.warning(f"No papers found for query: {query}")
            return []
        
        total_papers = len(papers['PubmedArticle'])
        logger.info(f"Found {total_papers} papers to analyze")
        
        # Step 2: Update progress tracking
        self._init_progress(total_papers)
        
        # Step 3: Analyze each paper
        results = []
        for i, paper in enumerate(papers['PubmedArticle'], 1):
            self._update_progress(i, total_papers, f"Analyzing paper {i}/{total_papers}")
            
            result = self._analyze_single_paper(paper, use_full_text)
            if result:
                results.append(result)
                logger.info(f"Completed paper {i}/{total_papers}: {result.get('Title', 'Unknown')[:50]}...")
        
        logger.info(f"Analysis complete: {len(results)} papers analyzed successfully")
        return results
    
    def _analyze_single_paper(self, paper: Dict, use_full_text: bool) -> Optional[Dict[str, Any]]:
        """
        Analyze a single paper.
        
        Args:
            paper: PubMed paper record
            use_full_text: Whether to try fetching full text
            
        Returns:
            Analysis result dictionary or None on error
        """
        try:
            # First, analyze with abstract
            result = self._call_ai_analyzer(paper, is_pdf=False)
            result['Analysis Source'] = "Abstract"
            
            # Try to get full text if requested
            if use_full_text:
                full_text_result = self._try_full_text_analysis(paper, result)
                if full_text_result:
                    result = full_text_result
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing paper: {e}")
            return {
                "Title": "Error analyzing paper",
                "Error": str(e),
                "Analysis Source": "Failed"
            }
    
    def _try_full_text_analysis(self, paper: Dict, abstract_result: Dict) -> Optional[Dict[str, Any]]:
        """
        Try to fetch and analyze full text.
        
        Args:
            paper: PubMed paper record
            abstract_result: Result from abstract analysis (for PMID/DOI)
            
        Returns:
            Full text analysis result or None if not available
        """
        from app.utils.pubmed_utils import fetch_full_text_from_pmc, fetch_full_text_from_doi
        
        pmid = abstract_result.get('PMID', 'NA')
        doi_link = abstract_result.get('Full Text Link', 'NA')
        
        # Extract DOI from link
        doi = None
        if doi_link and 'doi.org' in doi_link:
            parts = doi_link.split('/')
            if len(parts) >= 2:
                doi = '/'.join(parts[-2:])
        
        full_text = None
        source = None
        
        # Try PMC first
        if pmid and pmid not in ('NA', 'N/A'):
            try:
                full_text = fetch_full_text_from_pmc(pmid)
                if full_text:
                    source = "PMC"
            except Exception as e:
                logger.debug(f"PMC fetch failed for PMID {pmid}: {e}")
        
        # Try DOI if PMC failed
        if not full_text and doi:
            try:
                full_text = fetch_full_text_from_doi(doi)
                if full_text:
                    source = "DOI"
            except Exception as e:
                logger.debug(f"DOI fetch failed for {doi}: {e}")
        
        if not full_text:
            return None
        
        # Analyze full text
        try:
            logger.info(f"Analyzing full text for PMID {pmid} from {source}")
            result = self._call_ai_analyzer(full_text, is_pdf=False)
            result['PMID'] = pmid
            result['Full Text Link'] = doi_link
            result['Analysis Source'] = f"Full Text ({source})"
            return result
        except Exception as e:
            logger.warning(f"Full text analysis failed for PMID {pmid}: {e}")
            return None
    
    def analyze_pdf_files(
        self, 
        pdf_files: List[Dict], 
        use_ocr: bool = False, 
        language: str = "eng", 
        action: str = "new"
    ) -> List[Dict[str, Any]]:
        """
        Process and analyze PDF files.
        
        Args:
            pdf_files: List of PDF file dictionaries with 'path' and 'name'
            use_ocr: Whether to use OCR for scanned PDFs
            language: Language code for OCR
            action: "new" to start fresh (reserved for future use)
            
        Returns:
            List of analyzed paper dictionaries
        """
        logger.info(f"Starting PDF analysis: {len(pdf_files)} files, OCR={use_ocr}")
        
        from app.utils.pdf_utils import process_file
        
        total_files = len(pdf_files)
        self._init_progress(total_files)
        
        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            self._update_progress(i, total_files, f"Processing {pdf_file.get('name', 'file')}")
            
            try:
                # Extract text from PDF
                processed = process_file(pdf_file, use_ocr, language)
                
                # Analyze the extracted text
                result = self._call_ai_analyzer(processed['content'], is_pdf=True)
                result['Filename'] = pdf_file.get('name', 'Unknown')
                results.append(result)
                
                logger.info(f"Completed PDF {i}/{total_files}: {pdf_file.get('name')}")
                
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_file.get('name')}: {e}")
                results.append({
                    "Title": f"Error processing {pdf_file.get('name', 'document')}",
                    "Filename": pdf_file.get('name', 'Unknown'),
                    "Error": str(e)
                })
        
        logger.info(f"PDF analysis complete: {len(results)} files processed")
        return results
    
    def _call_ai_analyzer(self, content: Any, is_pdf: bool) -> Dict[str, Any]:
        """
        Call the appropriate AI analyzer based on provider.
        
        Args:
            content: Paper content (dict for PubMed, string for PDF)
            is_pdf: Whether the content is from a PDF
            
        Returns:
            Analysis result dictionary
        """
        if self.provider == "openai":
            from app.utils.openai_utils import analyze_paper_with_openai
            return analyze_paper_with_openai(self.client, content, is_pdf=is_pdf, model=self.model)
        else:
            from app.utils.claude_utils import analyze_paper_with_claude
            return analyze_paper_with_claude(self.client, content, is_pdf=is_pdf, model=self.model)
    
    def _init_progress(self, total: int) -> None:
        """Initialize progress tracking in Flask session."""
        try:
            import flask
            import time
            flask.session['total_papers'] = total
            flask.session['progress'] = 0
            flask.session['start_time'] = time.time()
            flask.session['analysis_status'] = 'running'
        except RuntimeError:
            # Not in request context (e.g., during testing)
            pass
    
    def _update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress tracking in Flask session."""
        try:
            import flask
            flask.session['progress'] = current
            flask.session['current_paper'] = message
        except RuntimeError:
            # Not in request context
            pass
