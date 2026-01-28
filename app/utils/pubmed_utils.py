from Bio import Entrez
from typing import List, Dict, Any, Optional
import logging
import xml.etree.ElementTree as ET
import requests
import re
import os

logger = logging.getLogger(__name__)

# Set default email for Entrez (required by NCBI)
# This will be overridden by configure_entrez if credentials are provided
DEFAULT_EMAIL = "user@example.com"
Entrez.email = os.environ.get('NCBI_EMAIL', DEFAULT_EMAIL)
if os.environ.get('NCBI_API_KEY'):
    Entrez.api_key = os.environ.get('NCBI_API_KEY')

def configure_entrez(email: Optional[str] = None, api_key: Optional[str] = None) -> None:
    """Configure Entrez with email and API key"""
    if email:
        Entrez.email = email
    else:
        # Ensure email is set to at least the default
        if not Entrez.email or Entrez.email == "":
            Entrez.email = DEFAULT_EMAIL
    if api_key:
        Entrez.api_key = api_key

def get_pubmed_count(query: str) -> Optional[int]:
    """Get the total count of papers available in PubMed for a query."""
    try:
        with Entrez.esearch(db="pubmed", term=query, retmax=0) as handle:
            record = Entrez.read(handle)
        return int(record["Count"])
    except Exception as e:
        logger.error(f"Error getting PubMed count: {e}")
        return None

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

def fetch_full_text_from_pmc(pmid: str) -> Optional[str]:
    """
    Attempt to fetch full text from PubMed Central using the PMID.
    
    Args:
        pmid: PubMed ID
        
    Returns:
        Full text content if available, None otherwise
    """
    try:
        # First, check if the article has a PMC ID
        with Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid) as handle:
            link_results = Entrez.read(handle)
        
        if not link_results[0]["LinkSetDb"] or not link_results[0]["LinkSetDb"][0]["Link"]:
            return None
        
        # Get the PMC ID
        pmc_id = link_results[0]["LinkSetDb"][0]["Link"][0]["Id"]
        
        # Fetch the full text using the PMC ID
        with Entrez.efetch(db="pmc", id=pmc_id, rettype="xml") as handle:
            full_text_xml = handle.read()
        
        # Parse XML to extract PMID for cross-check
        try:
            root = ET.fromstring(full_text_xml)
            # Try to find the PMID in the XML (common tag: article-id pub-id-type="pmid")
            pmid_found = None
            for elem in root.iter():
                if elem.tag.endswith("article-id") and elem.attrib.get("pub-id-type") == "pmid":
                    pmid_found = elem.text.strip()
                    break
            
            # Strip whitespace and compare
            if pmid_found is not None and str(pmid_found).strip() != str(pmid).strip():
                logger.warning(f"PMC ID {pmc_id} PMID {pmid_found} does not match queried PMID {pmid}. Skipping.")
                return None
        except Exception as e:
            logger.warning(f"Warning: Could not parse PMC XML for PMID cross-check: {e}")
            # If parsing fails, skip for safety
            return None
        
        # Simple extraction of text from XML (could be improved with proper XML parsing)
        text = re.sub(r'<[^>]+>', ' ', full_text_xml.decode('utf-8'))
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        logger.error(f"Error fetching full text from PMC: {e}")
        return None

def fetch_full_text_from_doi(doi: str) -> Optional[str]:
    """
    Attempt to fetch full text using DOI through open access APIs.
    
    Args:
        doi: Digital Object Identifier
        
    Returns:
        Full text content if available, None otherwise
    """
    try:
        # Try Unpaywall API with timeout
        response = requests.get(
            f"https://api.unpaywall.org/v2/{doi}?email={Entrez.email}",
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("is_oa") and data.get("best_oa_location") and data.get("best_oa_location").get("url_for_pdf"):
                pdf_url = data["best_oa_location"]["url_for_pdf"]
                pdf_response = requests.get(pdf_url, timeout=30)
                if pdf_response.status_code == 200:
                    # Convert PDF to text (this would need PDF processing)
                    # For now, return a placeholder indicating PDF is available
                    return f"PDF available at: {pdf_url}"
        
        return None
    except Exception as e:
        logger.error(f"Error fetching from DOI: {e}")
        return None

def get_full_text_link(paper: Dict[str, Any]) -> Optional[str]:
    """
    Extract DOI or other full text links from paper metadata.
    
    Args:
        paper: Paper metadata dictionary
        
    Returns:
        DOI URL or other full text link if available
    """
    try:
        # Extract DOI from paper metadata
        if 'MedlineCitation' in paper and 'Article' in paper['MedlineCitation']:
            article = paper['MedlineCitation']['Article']
            
            # Look for DOI in various places
            if 'ELocationID' in article:
                for elocation in article['ELocationID']:
                    if elocation.attributes.get('EIdType') == 'doi':
                        doi = elocation
                        return f"https://doi.org/{doi}"
            
            # Look in ArticleIdList
            if 'ArticleIdList' in article:
                for article_id in article['ArticleIdList']:
                    if hasattr(article_id, 'attributes') and article_id.attributes.get('IdType') == 'doi':
                        return f"https://doi.org/{article_id}"
        
        return None
    except Exception as e:
        logger.error(f"Error extracting full text link: {e}")
        return None
