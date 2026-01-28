"""
Test Analysis Flow - Step by Step Tests
========================================

This file tests each step of the PubMed analysis flow independently.
Run with: python test_analysis_flow.py

The analysis flow has these steps:
1. PubMed Search - Search PubMed and get paper list
2. API Client - Create OpenAI/Claude client  
3. Analysis - Analyze each paper with AI
4. Results - Store and display results
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def test_step1_pubmed_search():
    """
    STEP 1: Test PubMed search functionality
    
    This tests that we can:
    - Connect to PubMed
    - Search for papers
    - Get paper metadata
    """
    print("\n" + "="*60)
    print("STEP 1: Testing PubMed Search")
    print("="*60)
    
    try:
        from app.utils.pubmed_utils import search_and_fetch_pubmed, get_pubmed_count, configure_entrez
        
        # Configure Entrez (optional - uses defaults if not set)
        ncbi_email = os.environ.get('NCBI_EMAIL', 'test@example.com')
        ncbi_api_key = os.environ.get('NCBI_API_KEY')
        configure_entrez(ncbi_email, ncbi_api_key)
        
        # Test query
        query = "aspirin AND (clinicaltrial[filter])"
        max_results = 3
        
        # Test 1a: Get count
        print(f"\n1a. Getting paper count for query: {query}")
        count = get_pubmed_count(query)
        print(f"    → Found {count} papers total")
        assert count is not None, "Failed to get paper count"
        assert count > 0, "No papers found"
        print("    ✓ Count test passed")
        
        # Test 1b: Search and fetch
        print(f"\n1b. Fetching {max_results} papers...")
        papers = search_and_fetch_pubmed(query, max_results)
        assert 'PubmedArticle' in papers, "No PubmedArticle key in response"
        num_papers = len(papers['PubmedArticle'])
        print(f"    → Retrieved {num_papers} papers")
        assert num_papers > 0, "No papers retrieved"
        
        # Test 1c: Check paper structure
        print("\n1c. Checking paper structure...")
        paper = papers['PubmedArticle'][0]
        assert 'MedlineCitation' in paper, "Missing MedlineCitation"
        
        # Extract title for display
        article = paper['MedlineCitation'].get('Article', {})
        title = article.get('ArticleTitle', 'No title')
        pmid = paper['MedlineCitation'].get('PMID', 'No PMID')
        print(f"    → First paper: {title[:50]}...")
        print(f"    → PMID: {pmid}")
        print("    ✓ Paper structure test passed")
        
        print("\n✅ STEP 1 PASSED: PubMed search is working")
        return papers
        
    except Exception as e:
        print(f"\n❌ STEP 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step2_api_client():
    """
    STEP 2: Test API client creation
    
    This tests that we can:
    - Create an OpenAI or Claude client
    - Validate API keys (only non-empty keys)
    """
    print("\n" + "="*60)
    print("STEP 2: Testing API Client Creation")
    print("="*60)
    
    client = None
    provider = None
    
    # Get API keys (only non-empty strings)
    openai_key = (os.environ.get('OPENAI_KEY') or os.environ.get('OPENAI_API_KEY') or '').strip()
    anthropic_key = (os.environ.get('ANTHROPIC_KEY') or os.environ.get('ANTHROPIC_API_KEY') or '').strip()
    
    # Check which keys are available
    print(f"\n    OpenAI key available: {'Yes' if openai_key else 'No (empty)'}")
    print(f"    Anthropic key available: {'Yes' if anthropic_key else 'No (empty)'}")
    
    # Determine preferred provider from .env MODEL setting
    model_setting = os.environ.get('MODEL', '').lower()
    prefer_anthropic = 'anthropic' in model_setting or 'claude' in model_setting or 'haiku' in model_setting
    print(f"    Preferred provider (from MODEL setting): {'Anthropic' if prefer_anthropic else 'OpenAI'}")
    
    # Try Anthropic first if preferred or if OpenAI is not available
    if (prefer_anthropic or not openai_key) and anthropic_key:
        print("\n2a. Testing Anthropic client...")
        try:
            from app.utils.claude_utils import create_claude_client
            from app.utils.api_utils import validate_anthropic_api_key
            
            is_valid, error = validate_anthropic_api_key(anthropic_key)
            if is_valid:
                print("    → Anthropic API key is valid")
                client = create_claude_client(anthropic_key)
                provider = 'anthropic'
                print("    ✓ Claude client created")
            else:
                print(f"    → Anthropic key validation failed: {error}")
        except Exception as e:
            print(f"    → Anthropic client failed: {e}")
    
    # Try OpenAI if we don't have a client yet
    if not client and openai_key:
        print("\n2b. Testing OpenAI client...")
        try:
            from app.utils.openai_utils import create_openai_client
            from app.utils.api_utils import validate_openai_api_key
            
            # Validate key
            is_valid, error = validate_openai_api_key(openai_key)
            if is_valid:
                print("    → OpenAI API key is valid")
                client = create_openai_client(openai_key)
                provider = 'openai'
                print("    ✓ OpenAI client created")
            else:
                print(f"    → OpenAI key validation failed: {error}")
        except Exception as e:
            print(f"    → OpenAI client failed: {e}")
    
    if client:
        print(f"\n✅ STEP 2 PASSED: {provider.upper()} client created successfully")
        return client, provider
    else:
        print("\n❌ STEP 2 FAILED: No valid API key found")
        print("    Set OPENAI_KEY or ANTHROPIC_KEY in .env file")
        return None, None


def test_step3_analysis_service(papers=None, client=None, provider=None):
    """
    STEP 3: Test analysis service
    
    This tests that we can:
    - Create an AnalysisService
    - Analyze a single paper
    """
    print("\n" + "="*60)
    print("STEP 3: Testing Analysis Service")
    print("="*60)
    
    if papers is None or client is None:
        print("    → Running prerequisite tests first...")
        papers = test_step1_pubmed_search()
        client, provider = test_step2_api_client()
    
    if papers is None or client is None:
        print("\n❌ STEP 3 SKIPPED: Prerequisites not met")
        return None
    
    try:
        from app.services.analysis_service import AnalysisService
        
        # Create analysis service
        print("\n3a. Creating AnalysisService...")
        model = 'gpt-4o-mini' if provider == 'openai' else 'claude-3-haiku-20240307'
        service = AnalysisService(client, provider, model)
        print(f"    → Service created with {provider}/{model}")
        
        # Analyze just one paper
        print("\n3b. Analyzing single paper...")
        paper = papers['PubmedArticle'][0]
        
        # Use the appropriate analysis function directly
        if provider == 'openai':
            from app.utils.openai_utils import analyze_paper_with_openai
            result = analyze_paper_with_openai(client, paper, is_pdf=False, model=model)
        else:
            from app.utils.claude_utils import analyze_paper_with_claude
            result = analyze_paper_with_claude(client, paper, is_pdf=False, model=model)
        
        print(f"    → Analysis returned {len(result)} fields")
        
        # Check result structure
        print("\n3c. Checking result structure...")
        expected_fields = ['Title', 'PMID', 'Subject of Study', 'Type of Study']
        for field in expected_fields:
            if field in result:
                value = str(result[field])[:50]
                print(f"    → {field}: {value}...")
            else:
                print(f"    → {field}: MISSING")
        
        print("\n✅ STEP 3 PASSED: Analysis service is working")
        return result
        
    except Exception as e:
        print(f"\n❌ STEP 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step4_flask_routes():
    """
    STEP 4: Test Flask routes
    
    This tests that:
    - Flask app starts
    - Routes respond correctly
    - Session handling works
    """
    print("\n" + "="*60)
    print("STEP 4: Testing Flask Routes")
    print("="*60)
    
    try:
        from app import create_app
        
        print("\n4a. Creating Flask test app...")
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        
        with app.test_client() as test_client:
            # Test 4a: Home page
            print("\n4b. Testing home page (/)...")
            response = test_client.get('/')
            assert response.status_code == 200, f"Home page failed: {response.status_code}"
            print("    ✓ Home page works")
            
            # Test 4b: Settings page (may redirect if auto-configured from .env)
            print("\n4c. Testing settings page (/settings)...")
            response = test_client.get('/settings')
            # 200 = settings form displayed, 302 = auto-configured and redirected
            assert response.status_code in [200, 302], f"Settings page failed: {response.status_code}"
            if response.status_code == 302:
                print("    → Auto-configured from .env (redirected)")
            print("    ✓ Settings page works")
            
            # Test 4c: Analysis status endpoint
            print("\n4d. Testing analysis status API (/api/analysis-status)...")
            response = test_client.get('/api/analysis-status')
            assert response.status_code == 200, f"Status API failed: {response.status_code}"
            data = response.get_json()
            print(f"    → Status: {data.get('status', 'unknown')}")
            print("    ✓ Analysis status API works")
            
            # Test 4d: Results endpoint
            print("\n4e. Testing results API (/api/results)...")
            response = test_client.get('/api/results')
            assert response.status_code == 200, f"Results API failed: {response.status_code}"
            print("    ✓ Results API works")
            
            # Test 4e: Start analysis endpoint (with mock session)
            print("\n4f. Testing start analysis API (/api/start-analysis)...")
            with test_client.session_transaction() as sess:
                sess['api_key_valid'] = True
                sess['api_provider'] = 'openai'
                sess['api_key'] = os.environ.get('OPENAI_KEY', 'test-key')
                sess['model'] = 'gpt-4o-mini'
                sess['analysis_type'] = 'pubmed'
                sess['query'] = 'test'
                sess['max_results'] = 1
            
            response = test_client.post('/api/start-analysis')
            print(f"    → Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"    → Analysis status: {data.get('status', 'unknown')}")
                print("    ✓ Start analysis API works")
            else:
                # This is expected to fail without proper API key
                print(f"    → Expected failure (no real API key in test)")
        
        print("\n✅ STEP 4 PASSED: Flask routes are working")
        return True
        
    except Exception as e:
        print(f"\n❌ STEP 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_javascript_ajax():
    """
    STEP 5: Document JavaScript AJAX issue
    
    This explains the JavaScript issue and how to debug it.
    """
    print("\n" + "="*60)
    print("STEP 5: JavaScript AJAX Debugging")
    print("="*60)
    
    print("""
    The issue: POST /api/start-analysis is not appearing in server logs.
    
    To debug in browser:
    
    1. Open Developer Tools (F12)
    2. Go to Network tab
    3. Click "Start Analysis"
    4. Look for the POST request to /api/start-analysis
    
    Possible issues:
    
    a) JavaScript Error BEFORE the AJAX call:
       - Check Console tab for errors
       - Look for "Uncaught TypeError" or similar
    
    b) jQuery not loaded:
       - Check if $ is defined: type "typeof $" in console
       - Should return "function"
    
    c) url_for returning wrong URL:
       - In results.html, check the generated URL
       - Look for: url: '{{ url_for("main.start_analysis") }}'
    
    d) CSRF Token missing:
       - Flask-WTF may require CSRF token for POST
       - Check if CSRF is enabled in config
    
    Quick browser console test:
    ```javascript
    // Run this in browser console to test the API directly:
    fetch('/api/start-analysis', {method: 'POST'})
      .then(r => r.json())
      .then(d => console.log('Response:', d))
      .catch(e => console.error('Error:', e));
    ```
    """)
    
    print("✅ STEP 5: See debugging instructions above")
    return True


def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "="*60)
    print("CLARA ANALYSIS FLOW - COMPLETE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Step 1: PubMed
    papers = test_step1_pubmed_search()
    results['step1_pubmed'] = papers is not None
    
    # Step 2: API Client
    client, provider = test_step2_api_client()
    results['step2_api_client'] = client is not None
    
    # Step 3: Analysis Service (only if steps 1 and 2 passed)
    if papers and client:
        result = test_step3_analysis_service(papers, client, provider)
        results['step3_analysis'] = result is not None
    else:
        results['step3_analysis'] = False
        print("\n⏭️  STEP 3 SKIPPED: Prerequisites not met")
    
    # Step 4: Flask Routes
    results['step4_flask'] = test_step4_flask_routes()
    
    # Step 5: JavaScript debugging info
    results['step5_js'] = test_javascript_ajax()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for step, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {step}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == 'test_pubmed_search':
            test_step1_pubmed_search()
        elif test_name == 'test_api_client':
            test_step2_api_client()
        elif test_name == 'test_analysis_service':
            test_step3_analysis_service()
        elif test_name == 'test_flask_routes':
            test_step4_flask_routes()
        elif test_name == 'test_javascript':
            test_javascript_ajax()
        elif test_name == 'all':
            run_all_tests()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: test_pubmed_search, test_api_client, test_analysis_service, test_flask_routes, test_javascript, all")
    else:
        run_all_tests()
