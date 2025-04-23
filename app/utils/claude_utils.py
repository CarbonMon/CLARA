# claude connection with prompts
import json
import re
from anthropic import Anthropic
from typing import Dict, Any, Optional
import logging
from app.utils.prompts import get_base_analysis_prompt, get_pdf_prompt_addition, get_claude_specific_instructions

logger = logging.getLogger(__name__)

def create_claude_client(api_key: str) -> Anthropic:
    """Create and return an Anthropic client"""
    return Anthropic(api_key=api_key)

def get_analysis_prompt(is_pdf: bool = False) -> str:
    """Get the system prompt for paper analysis"""
    system_prompt = get_base_analysis_prompt() + get_claude_specific_instructions()
    
    if is_pdf:
        system_prompt += get_pdf_prompt_addition()

    return system_prompt

def extract_json_from_text(text: str) -> str:
    """
    Extract JSON object from text, handling various formatting issues
    """
    # If text is empty, return a minimal valid JSON
    if not text or text.isspace():
        return '{}'
        
    # Try to find JSON between triple backticks
    json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text, re.MULTILINE)
    if json_match:
        return json_match.group(1).strip()
        
    # Try to find anything that looks like a JSON object (starts with { and ends with })
    json_match = re.search(r'({[\s\S]*?})', text, re.MULTILINE)
    if json_match:
        return json_match.group(1).strip()
    
    # If no JSON found, return the text itself if it might be JSON
    if text.strip().startswith('{') and text.strip().endswith('}'):
        return text.strip()
    
    # As a last resort, create a minimal JSON with error
    return '{"Error": "Could not extract valid JSON from model response", "Title": "Error Processing Document"}'

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
        
        # Add explicit JSON instructions to the user content
        user_content = str(paper_content)
        if len(user_content) > 100000:  # If content is very long, truncate it
            user_content = user_content[:100000] + "\n\n[Content truncated due to length]"
        
        message = client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        )

        # Extract response text
        response_text = message.content[0].text if message.content else ""
        
        # Process and clean the response to extract JSON
        cleaned_str = extract_json_from_text(response_text)
        
        try:
            # Try to parse the JSON
            result = json.loads(cleaned_str)
            return result
        except json.JSONDecodeError as e:
            # If parsing fails, return an error object
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            
            return {
                "Title": "Error parsing model response",
                "Error": f"Could not parse response as JSON: {str(e)}",
                "Raw Response": response_text[:500] + "..." if len(response_text) > 500 else response_text
            }
            
    except Exception as e:
        logger.error(f"Error analyzing paper with Claude: {e}")
        return {
            "Title": "Error analyzing document",
            "Error": str(e)
        }