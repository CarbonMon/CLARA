#!/usr/bin/env python3
"""
Test script to verify Anthropic Claude API integration with real API calls.
Uses .env file for API key configuration.
"""

import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_result(success, message):
    """Print test result with icon"""
    icon = "✓" if success else "✗"
    status = "PASS" if success else "FAIL"
    print(f"  [{icon}] {status}: {message}")
    return success

def print_debug(label, value):
    """Print debug information"""
    if isinstance(value, (dict, list)):
        print(f"    DEBUG {label}: {json.dumps(value, indent=2, default=str)[:500]}")
    else:
        print(f"    DEBUG {label}: {value}")


# Sample paper abstract for testing
SAMPLE_PAPER_ABSTRACT = """
Title: Efficacy and Safety of Dupilumab in Patients With Moderate-to-Severe Atopic Dermatitis

Authors: Simpson EL, Bieber T, Guttman-Yassky E, et al.

Journal: New England Journal of Medicine

PMID: 27690741

DOI: 10.1056/NEJMoa1610020

Abstract:
BACKGROUND: Dupilumab, a human monoclonal antibody against interleukin-4 receptor alpha, inhibits 
signaling of interleukin-4 and interleukin-13, type 2 cytokines that may be important drivers of 
atopic diseases.

METHODS: In two randomized, placebo-controlled, phase 3 trials (SOLO 1 and SOLO 2) of identical 
design, we enrolled adults with moderate-to-severe atopic dermatitis whose disease was inadequately 
controlled by topical treatment. Patients were randomly assigned in a 1:1:1 ratio to receive 
subcutaneous dupilumab (300 mg) weekly, dupilumab every 2 weeks alternating with placebo, or 
placebo weekly for 16 weeks. The primary outcome was an Investigator's Global Assessment (IGA) 
score of 0 or 1 (clear or almost clear) at week 16. Secondary outcomes included a reduction of 
at least 75% in the Eczema Area and Severity Index score (EASI-75) and improvement in pruritus.

RESULTS: A total of 671 patients underwent randomization in SOLO 1 and 708 in SOLO 2. In SOLO 1, 
IGA 0 or 1 was achieved at week 16 by 38% of patients who received dupilumab every 2 weeks and 
37% of those who received dupilumab weekly, as compared with 10% of those who received placebo 
(P<0.001 for both comparisons with placebo). In SOLO 2, the corresponding rates were 36%, 36%, 
and 8% (P<0.001 for both comparisons). EASI-75 was achieved by a significantly greater percentage 
of patients who received each regimen of dupilumab than of those who received placebo (P<0.001 
for all comparisons). Improvement in pruritus was also significantly greater with dupilumab 
(P<0.001 for all comparisons). Injection-site reactions and conjunctivitis were more common 
with dupilumab than with placebo.

CONCLUSIONS: In two phase 3 trials, dupilumab improved the signs and symptoms of atopic dermatitis 
in adults, including pruritus. Injection-site reactions and conjunctivitis were observed more 
frequently in dupilumab-treated patients.

ClinicalTrials.gov numbers: NCT02277743 and NCT02277769.
"""


def test_env_configuration():
    """Test that .env file is properly configured"""
    print_header("Testing Environment Configuration")
    
    anthropic_key = os.getenv('ANTHROPIC_KEY')
    
    if anthropic_key:
        # Mask most of the key for security
        masked_key = anthropic_key[:10] + "..." + anthropic_key[-4:] if len(anthropic_key) > 14 else "***"
        print_result(True, f"ANTHROPIC_KEY loaded from .env: {masked_key}")
        print_debug("Key length", len(anthropic_key))
        return anthropic_key
    else:
        print_result(False, "ANTHROPIC_KEY not found in .env file")
        print("    Make sure your .env file contains: ANTHROPIC_KEY=sk-ant-...")
        return None


def test_anthropic_client_creation(api_key):
    """Test that Anthropic client can be created"""
    print_header("Testing Anthropic Client Creation")
    
    if not api_key:
        print_result(False, "No API key available - skipping")
        return None
    
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        print_result(True, "Anthropic client created successfully")
        return client
    except ImportError:
        print_result(False, "Anthropic library not installed. Run: pip install anthropic")
        return None
    except Exception as e:
        print_result(False, f"Failed to create client: {e}")
        return None


def test_basic_api_call(client):
    """Test a basic API call to verify connectivity"""
    print_header("Testing Basic Anthropic API Call")
    
    if not client:
        print_result(False, "No client available - skipping")
        return False
    
    try:
        print("    Making API call to Claude (claude-3-haiku-20240307)...")
        
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'API connection successful!' in exactly those words."}
            ]
        )
        
        response_text = message.content[0].text if message.content else ""
        print_debug("Response", response_text)
        print_debug("Model used", message.model)
        print_debug("Usage (input tokens)", message.usage.input_tokens)
        print_debug("Usage (output tokens)", message.usage.output_tokens)
        
        print_result(True, "Basic API call successful!")
        return True
        
    except Exception as e:
        print_result(False, f"API call failed: {e}")
        return False


def test_paper_analysis_with_claude(client):
    """Test analyzing a real paper abstract with Claude"""
    print_header("Testing Paper Analysis with Claude")
    
    if not client:
        print_result(False, "No client available - skipping")
        return None
    
    try:
        from app.utils.claude_utils import analyze_paper_with_claude
        
        print("    Analyzing sample paper abstract with Claude...")
        print("    (This may take a few seconds)")
        
        # Use haiku model for faster/cheaper testing
        result = analyze_paper_with_claude(
            client=client,
            paper_content=SAMPLE_PAPER_ABSTRACT,
            is_pdf=False,
            model="claude-3-haiku-20240307"
        )
        
        print_result(True, "Paper analysis completed!")
        print("\n    Analysis Results:")
        print("    " + "-"*50)
        
        # Display key fields from the analysis
        key_fields = [
            "Title", "PMID", "Main Author", "Journal Name", 
            "Disease State", "Type of Study", "Number of Subjects Studied",
            "Intervention", "Primary Endpoint", "Primary Endpoint Met",
            "Statistical Significance", "Conclusion"
        ]
        
        for field in key_fields:
            value = result.get(field, "Not found")
            if value and len(str(value)) > 60:
                value = str(value)[:57] + "..."
            print(f"    {field}: {value}")
        
        print("    " + "-"*50)
        
        return result
        
    except Exception as e:
        print_result(False, f"Paper analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_analysis_service_with_anthropic():
    """Test the AnalysisService with Anthropic"""
    print_header("Testing AnalysisService with Anthropic")
    
    try:
        from anthropic import Anthropic
        from app.services.analysis_service import AnalysisService
        
        api_key = os.getenv('ANTHROPIC_KEY')
        if not api_key:
            print_result(False, "ANTHROPIC_KEY not available")
            return False
        
        # Create client and service
        client = Anthropic(api_key=api_key)
        service = AnalysisService(client, "anthropic", "claude-3-haiku-20240307")
        
        print_result(True, "AnalysisService created with Anthropic client")
        print_debug("Provider", service.provider)
        print_debug("Model", service.model)
        
        return True
        
    except Exception as e:
        print_result(False, f"AnalysisService test failed: {e}")
        return False


def test_flask_app_with_anthropic():
    """Test Flask app creation and session with Anthropic config"""
    print_header("Testing Flask App with Anthropic Configuration")
    
    try:
        from app import create_app
        app = create_app()
        
        print_result(True, "Flask app created successfully")
        
        with app.test_client() as client:
            # Set up session with Anthropic configuration
            with client.session_transaction() as sess:
                sess['api_key_valid'] = True
                sess['api_provider'] = 'anthropic'
                sess['api_key'] = os.getenv('ANTHROPIC_KEY')
                sess['model'] = 'claude-3-haiku-20240307'
                sess['analysis_type'] = 'pubmed'
            
            print_debug("Session configured", "anthropic provider")
            
            # Verify session was set
            with client.session_transaction() as sess:
                print_debug("api_provider in session", sess.get('api_provider'))
                print_debug("model in session", sess.get('model'))
            
            print_result(True, "Flask session configured with Anthropic settings")
            return True
            
    except Exception as e:
        print_result(False, f"Flask app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_analysis_workflow():
    """Test a complete analysis workflow using Anthropic"""
    print_header("Testing Full Analysis Workflow")
    
    api_key = os.getenv('ANTHROPIC_KEY')
    if not api_key:
        print_result(False, "ANTHROPIC_KEY not available")
        return False
    
    try:
        from anthropic import Anthropic
        from app.utils.claude_utils import analyze_paper_with_claude
        
        # Create client
        client = Anthropic(api_key=api_key)
        
        # Simulate analyzing multiple papers
        test_abstracts = [
            {
                "title": "Dupilumab for Atopic Dermatitis",
                "content": SAMPLE_PAPER_ABSTRACT
            },
            {
                "title": "Simple Test",
                "content": """
                Title: A Simple Clinical Study
                Authors: Test Author
                Abstract: This is a test abstract for a simple randomized controlled trial
                studying drug X vs placebo in 50 patients with condition Y. Results showed
                significant improvement (p<0.05) in the primary endpoint.
                """
            }
        ]
        
        results = []
        for i, paper in enumerate(test_abstracts, 1):
            print(f"\n    Analyzing paper {i}/{len(test_abstracts)}: {paper['title'][:40]}...")
            
            result = analyze_paper_with_claude(
                client=client,
                paper_content=paper['content'],
                is_pdf=False,
                model="claude-3-haiku-20240307"
            )
            
            results.append(result)
            print(f"    ✓ Completed analysis for paper {i}")
        
        print(f"\n    Successfully analyzed {len(results)} papers")
        print_result(True, f"Full workflow completed with {len(results)} results")
        
        # Quick summary of results
        print("\n    Results Summary:")
        for i, result in enumerate(results, 1):
            title = result.get('Title', 'Unknown')[:50]
            endpoint_met = result.get('Primary Endpoint Met', 'Unknown')
            print(f"      Paper {i}: {title}... | Endpoint Met: {endpoint_met}")
        
        return results
        
    except Exception as e:
        print_result(False, f"Full workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all_tests():
    """Run all Anthropic integration tests"""
    print("\n" + "="*60)
    print(" CLARA - Anthropic Claude API Integration Test")
    print(" Testing Real API Calls with .env Configuration")
    print("="*60)
    
    results = {}
    
    # Test 1: Environment configuration
    api_key = test_env_configuration()
    results["Environment Configuration"] = api_key is not None
    
    if not api_key:
        print("\n" + "!"*60)
        print(" ERROR: ANTHROPIC_KEY not found in .env file")
        print(" Please add your API key to .env:")
        print(" ANTHROPIC_KEY=sk-ant-api03-...")
        print("!"*60)
        return False
    
    # Test 2: Client creation
    client = test_anthropic_client_creation(api_key)
    results["Anthropic Client Creation"] = client is not None
    
    # Test 3: Basic API call
    results["Basic API Call"] = test_basic_api_call(client)
    
    # Test 4: Paper analysis
    analysis_result = test_paper_analysis_with_claude(client)
    results["Paper Analysis"] = analysis_result is not None
    
    # Test 5: Analysis Service
    results["Analysis Service"] = test_analysis_service_with_anthropic()
    
    # Test 6: Flask App
    results["Flask App Integration"] = test_flask_app_with_anthropic()
    
    # Test 7: Full workflow
    workflow_results = test_full_analysis_workflow()
    results["Full Analysis Workflow"] = workflow_results is not None
    
    # Print summary
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n  Results: {passed}/{total} tests passed\n")
    
    for test_name, test_passed in results.items():
        status = "✓ PASS" if test_passed else "✗ FAIL"
        print(f"    {status}: {test_name}")
    
    print("\n" + "="*60)
    
    if passed == total:
        print("  ✓ All tests passed!")
        print("  Anthropic Claude API is working correctly.")
        print("  You can now use CLARA with your Anthropic API key.")
    else:
        print("  ✗ Some tests failed. Review the output above.")
    
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
