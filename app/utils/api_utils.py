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

def check_openai_budget(api_key: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Check OpenAI API budget/usage information.
    
    Args:
        api_key: The API key to check budget for
        
    Returns:
        Tuple of (is_valid, error_message, budget_info)
    """
    try:
        # For OpenAI, we can't directly check budget via API, so we'll just validate the key
        # and return a placeholder budget info
        is_valid, error = validate_openai_api_key(api_key)
        if not is_valid:
            return False, error, None
        
        # Placeholder budget info for OpenAI (would need to be implemented via OpenAI's usage API)
        budget_info = {
            'accumulated_cost': 0.0,
            'total_budget': 0.0,  # OpenAI doesn't provide this via simple API
            'remaining_budget': 0.0,
            'user_name': 'OpenAI User',
            'email': 'N/A'
        }
        
        return True, None, budget_info
    except Exception as e:
        return False, str(e), None

def check_anthropic_budget(api_key: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Check Anthropic API budget/usage information.
    
    Args:
        api_key: The API key to check budget for
        
    Returns:
        Tuple of (is_valid, error_message, budget_info)
    """
    try:
        # For Anthropic, we can't directly check budget via API, so we'll just validate the key
        # and return a placeholder budget info
        is_valid, error = validate_anthropic_api_key(api_key)
        if not is_valid:
            return False, error, None
        
        # Placeholder budget info for Anthropic (would need to be implemented via Anthropic's usage API)
        budget_info = {
            'accumulated_cost': 0.0,
            'total_budget': 0.0,  # Anthropic doesn't provide this via simple API
            'remaining_budget': 0.0,
            'user_name': 'Anthropic User',
            'email': 'N/A'
        }
        
        return True, None, budget_info
    except Exception as e:
        return False, str(e), None
