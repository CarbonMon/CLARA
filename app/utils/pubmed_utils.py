from Bio import Entrez
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def configure_entrez(email: Optional[str] = None, api_key: Optional[str] = None) -> None:
    """Configure Entrez with email and API key"""
    if email:
        Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

def search_and_fetch_pubmed(query: str, max_results: int) -> Dict[str, Any]:
    """
    Search PubMed and fetch details in one function.
    
    Args:
        query: PubMed search query
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing PubMed article records
    """
    try:
        with Entrez.esearch(db="pubmed", term=query, retmax=max_results) as handle:
            record = Entrez.read(handle)

        id_list = record["IdList"]
        if not id_list:
            return {"PubmedArticle": []}

        ids = ','.join(id_list)
        with Entrez.efetch(db="pubmed", id=ids, retmode="xml") as handle:
            records = Entrez.read(handle)

        return records
    except Exception as e:
        logger.error(f"Error searching PubMed: {e}")
        raise
