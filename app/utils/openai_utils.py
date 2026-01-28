# openai calls and prompting
import json
import re
import openai
from typing import Dict, Any, Optional
import logging
from app.utils.prompts import get_base_analysis_prompt, get_pdf_prompt_addition, get_openai_specific_instructions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'max_retries': 5,
    'min_wait_time': 30,  # seconds
    'max_wait_time': 60,  # seconds
    'exponential_multiplier': 1,
    'extra_rate_limit_delay': 2  # additional seconds for rate limit errors
}

def create_openai_client(api_key: str) -> openai.OpenAI:
    """Create and return an OpenAI client"""
    return openai.OpenAI(api_key=api_key)

def get_analysis_prompt(is_pdf: bool = False) -> str:
    """Get the system prompt for paper analysis"""
    system_prompt = get_base_analysis_prompt() + get_openai_specific_instructions()
    
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

def analyze_paper_with_openai(
    client: openai.OpenAI, 
    paper_content: Any, 
    is_pdf: bool = False, 
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Analyze a paper using OpenAI with rate limiting and retry logic
    
    Args:
        client: OpenAI client
        paper_content: Content to analyze
        is_pdf: Whether the content is from a PDF
        model: OpenAI model to use
        
    Returns:
        Analyzed paper data as dictionary
    """
    return call_openai_with_retry(client, paper_content, is_pdf, model)

@retry(
    retry=retry_if_exception_type((
        Exception,  # Catch all exceptions initially, then filter
    )),
    stop=stop_after_attempt(RATE_LIMIT_CONFIG['max_retries']),
    wait=wait_exponential(
        multiplier=RATE_LIMIT_CONFIG['exponential_multiplier'], 
        min=RATE_LIMIT_CONFIG['min_wait_time'], 
        max=RATE_LIMIT_CONFIG['max_wait_time']
    ),
    reraise=True
)
def call_openai_with_retry(client: openai.OpenAI, paper_content: Any, is_pdf: bool = False, model: str = "gpt-4o") -> Dict[str, Any]:
    """
    Make OpenAI API calls with automatic retry and rate limit handling.
    
    Args:
        client: OpenAI client instance
        paper_content: Content to analyze
        is_pdf: Whether the content is from a PDF
        model: OpenAI model to use
    
    Returns:
        OpenAI completion response
    
    Raises:
        Exception: After all retry attempts are exhausted
    """
    try:
        system_prompt = get_analysis_prompt(is_pdf)
        
        # Add explicit JSON instructions to the user content
        user_content = str(paper_content)
        if len(user_content) > 100000:  # If content is very long, truncate it
            user_content = user_content[:100000] + "\n\n[Content truncated due to length]"
        
        conversation = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            response_format={"type": "json_object"}  # Explicitly request JSON format for supported models
        )

        # Extract response text
        response_text = conversation.choices[0].message.content

        # Process and clean the response to extract JSON
        cleaned_str = extract_json_from_text(response_text)
        
        try:
            # Try to parse the JSON
            result = json.loads(cleaned_str)
            return result
        except json.JSONDecodeError as e:
            # If parsing fails, return an error object
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            
            return {
                "Title": "Error parsing model response",
                "Error": f"Could not parse response as JSON: {str(e)}",
                "Raw Response": response_text[:500] + "..." if len(response_text) > 500 else response_text
            }
            
    except Exception as e:
        error_message = str(e).lower()
        
        # Check for rate limit errors
        if any(rate_limit_indicator in error_message for rate_limit_indicator in [
            'rate limit', 'too many requests', '429', 'quota exceeded', 
            'requests per minute', 'tokens per minute'
        ]):
            logger.warning(f"Rate limit hit: {e}. Retrying with backoff...")
            # Add extra delay for rate limits
            import time
            time.sleep(RATE_LIMIT_CONFIG['extra_rate_limit_delay'])
            raise e  # Re-raise to trigger retry
        
        # Check for budget/quota exhaustion (don't retry, mark for manual key entry)
        elif any(budget_error in error_message for budget_error in [
            'quota exceeded', 'billing', 'payment', 'insufficient funds', 
            'budget exceeded', 'usage limit', 'account suspended'
        ]):
            logger.error(f"Budget/quota exhausted: {e}")
            raise e  # Don't retry, let user handle manually
        
        # Check for server errors that should be retried
        elif any(server_error in error_message for server_error in [
            '500', '502', '503', '504', 'internal server error', 
            'bad gateway', 'service unavailable', 'gateway timeout'
        ]):
            logger.warning(f"Server error: {e}. Retrying...")
            raise e  # Re-raise to trigger retry
        
        # Check for authentication errors (don't retry)
        elif any(auth_error in error_message for auth_error in [
            'unauthorized', '401', 'invalid api key', 'authentication'
        ]):
            logger.error(f"Authentication error (not retrying): {e}")
            raise e  # Re-raise without retry
        
        # For other errors, log and re-raise to trigger retry
        else:
            logger.warning(f"API error: {e}. Retrying...")
            raise e
