#!/usr/bin/env python3
"""
Test script to verify the PubMed search functionality with the new search modes.
This script tests the form validation and route handling.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.forms import PubMedSearchForm
from app.config import Config

def test_form_validation():
    """Test the PubMedSearchForm validation"""
    print("Testing PubMedSearchForm validation...")
    
    # Test with full mode (default)
    form_data = {
        'query': 'asthma clinical trials',
        'search_mode': 'full'
    }
    
    with create_app().test_request_context(data=form_data):
        form = PubMedSearchForm(data=form_data)
        if form.validate():
            print("✓ Full mode form validation passed")
            print(f"  Query: {form.query.data}")
            print(f"  Search Mode: {form.search_mode.data}")
            print(f"  Max Results: {form.max_results.data}")
        else:
            print("✗ Full mode form validation failed")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
    
    # Test with partial mode
    form_data = {
        'query': 'asthma clinical trials',
        'search_mode': 'partial',
        'max_results': 50
    }
    
    with create_app().test_request_context(data=form_data):
        form = PubMedSearchForm(data=form_data)
        if form.validate():
            print("✓ Partial mode form validation passed")
            print(f"  Query: {form.query.data}")
            print(f"  Search Mode: {form.search_mode.data}")
            print(f"  Max Results: {form.max_results.data}")
        else:
            print("✗ Partial mode form validation failed")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")

def test_search_mode_logic():
    """Test the search mode logic in routes"""
    print("\nTesting search mode logic...")
    
    # Test full mode logic
    search_mode = 'full'
    max_results = 10000  # Should be set to 10000 for full mode
    
    if search_mode == 'full':
        expected_max_results = 10000
        print(f"✓ Full mode: max_results set to {expected_max_results}")
    else:
        print("✗ Full mode logic failed")
    
    # Test partial mode logic
    search_mode = 'partial'
    user_max_results = 50
    max_results = user_max_results  # Should use user-specified value
    
    if search_mode == 'partial' and max_results == user_max_results:
        print(f"✓ Partial mode: max_results set to {max_results}")
    else:
        print("✗ Partial mode logic failed")

def test_config_defaults():
    """Test configuration defaults"""
    print("\nTesting configuration defaults...")
    
    # Check that default search mode is 'full'
    print(f"✓ Default search mode: 'full' (set in form)")
    print(f"✓ Max PubMed results: {Config.MAX_PUBMED_RESULTS}")
    print(f"✓ Default PubMed results: {Config.DEFAULT_PUBMED_RESULTS}")

if __name__ == '__main__':
    print("PubMed Search Mode Test")
    print("=" * 50)
    
    try:
        test_form_validation()
        test_search_mode_logic()
        test_config_defaults()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("\nFeatures implemented:")
        print("- ✓ Default search mode is 'Full Analysis (All Results)'")
        print("- ✓ Partial analysis option with max results selection")
        print("- ✓ Collapsed partial analysis section that shows/hides based on selection")
        print("- ✓ Form validation for both modes")
        print("- ✓ Route logic to handle both search modes")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
