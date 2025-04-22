# claude connection with prompts
import json
from anthropic import Anthropic
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def create_claude_client(api_key: str) -> Anthropic:
    """Create and return an Anthropic client"""
    return Anthropic(api_key=api_key)

def get_analysis_prompt(is_pdf: bool = False) -> str:
    """Get the system prompt for paper analysis"""
    system_prompt = """
    You are a bot speaking with another program that takes JSON formatted text as an input. Only return results in JSON format, with NO PREAMBLE.
    The user will input the results from a PubMed search or a full-text clinical trial PDF. Your job is to extract the exact information to return:
      'Title': The complete article title
      'PMID': The Pubmed ID of the article (if available, otherwise 'NA')
      'Full Text Link' : If available, the DOI URL, otherwise, NA
      'Subject of Study': The type of subject in the study. Human, Animal, In-Vitro, Other
      'Disease State': Disease state studied, if any, or if the study is done on a healthy population. leave blank if disease state or healthy patients is not mentioned explicitly. "Healthy patients" if patients are explicitly mentioned to be healthy.
      'Number of Subjects Studied': If human, the total study population. Otherwise, leave blank. This field needs to be an integer or empty.
      'Type of Study': Type of study done. 'RCT' for randomized controlled trial, '1. Meta-analysis','2. Systematic Review','3. Cohort Study', or '4. Other'. If it is '5. Other', append a short description
      'Study Design': Brief and succinct details about study design, if applicable
      'Intervention': Intervention(s) studied, if any. Intervention is the treatment applied to the group.
      'Intervention Dose': Go in detail here about the intervention's doses and treatment duration if available.
      'Intervention Dosage Form': A brief description of the dosage form - ie. oral, topical, intranasal, if available.
      'Control': Control or comarators, if any
      'Primary Endpoint': What the primary endpoint of the study was, if available. Include how it was measured too if available.
      'Primary Endpoint Result': The measurement for the primary endpoints
      'Secondary Endpoints' If available
      'Safety Endpoints' If available
      'Results Available': Yes or No
      'Primary Endpoint Met': Summarize from results whether or not the primary endpoint(s) was met: Yes or No or NA if results unavailable
      'Statistical Significance': alpha-level and p-value for primary endpoint(s), if available
      'Clinical Significance': Effect size, and Number needed to treat (NNT)/Number needed to harm (NNH), if available
      'Conclusion': Brief summary of the conclusions of the paper
      'Main Author': Last name, First initials
      'Other Authors': Last name, First initials; Last name First initials; ...
      'Journal Name': Full journal name
      'Date of Publication': YYYY-MM-DD
      'Error': Error description, if any. Otherwise, leave emtpy
    """

    if is_pdf:
        system_prompt += """
        Note: This is a full-text PDF of a clinical trial. Extract as much detail as possible from the full text.
        """

    return system_prompt

def analyze_paper_with_claude(
    client: Anthropic, 
    paper_content: Any, 
    is_pdf: bool = False, 
    model: str = "claude-3-sonnet-20240229"
) -> Dict[str, Any]:
    """
    Analyze a paper using Claude
    
    Args:
        client: Anthropic client
        paper_content: Content to analyze
        is_pdf: Whether the content is from a PDF
        model: Claude model to use
        
    Returns:
        Analyzed paper data as dictionary
    """
    try:
        system_prompt = get_analysis_prompt(is_pdf)
        
        message = client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": str(paper_content)
                }
            ]
        )

        cleaned_str = message.content[0].text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_str)
    except Exception as e:
        logger.error(f"Error analyzing paper with Claude: {e}")
        raise
