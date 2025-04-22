# authenticates API key
import requests
from typing import Tuple, Optional
import openai
from anthropic import Anthropic

def validate_openai_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the OpenAI API key by making a test request.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        client = openai.OpenAI(api_key=api_key)
        # Make a simple request to validate the key
        models = client.models.list()
        return True, None
    except Exception as e:
        return False, str(e)

def validate_anthropic_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the Anthropic API key by making a test request.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        client = Anthropic(api_key=api_key)
        # Make a simple request to validate the key
        models = client.models.list()
        return True, None
    except Exception as e:
        return False, str(e)
