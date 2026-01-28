# CLARA Analysis Flow Documentation

## Complete Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER WORKFLOW                                  │
└─────────────────────────────────────────────────────────────────────────┘

STEP 1: Settings Page (/settings)
        ├─> User enters API key (OpenAI or Anthropic)
        ├─> Key is validated via API call
        └─> Session stores: api_provider, api_key, model, api_key_valid=True

STEP 2: PubMed Search Page (/pubmed-search)
        ├─> User enters search query
        ├─> Optional: Check paper count via /api/pubmed-count
        └─> Form POST → Session stores: query, max_results, search_mode
            └─> Redirect to /analyze-pubmed

STEP 3: Analysis Page (/analyze-pubmed)
        ├─> Sets session: analysis_type='pubmed', analysis_status='pending'
        └─> Renders results.html with is_new_analysis=True

STEP 4: JavaScript in results.html (on page load)
        ├─> startAnalysis() called
        │   ├─> Updates progress UI to "Starting..."
        │   ├─> Calls startProgressPolling() → polls /api/analysis-status every 2s
        │   └─> Makes AJAX POST to /api/start-analysis
        │
        └─> /api/start-analysis (Server-side)
            ├─> Validates session has API key
            ├─> Sets analysis_status='running'
            ├─> Creates AI client (OpenAI or Claude)
            ├─> Calls AnalysisService.analyze_pubmed_papers()
            │   ├─> Searches PubMed (search_and_fetch_pubmed)
            │   ├─> For each paper:
            │   │   ├─> Analyzes with AI (analyze_paper_with_openai/claude)
            │   │   └─> Updates progress in session
            │   └─> Returns list of results
            ├─> Sets analysis_status='completed'
            └─> Returns JSON: {status: 'completed', count: N}

STEP 5: Results Display
        ├─> loadResults() called after analysis completes
        ├─> GET /api/results returns analysis_results from session
        └─> Grid.js renders the results table
```

## Debugging the Flow

### Check Browser Console (F12)
Look for these log messages:
```
[CLARA] Page loaded, initializing...
[CLARA] isNewAnalysis: true
[CLARA] Starting new analysis...
[CLARA] startAnalysis() called
[CLARA] Calling POST: /api/start-analysis
[CLARA] AJAX request starting...
[CLARA] Starting progress polling...
[CLARA] Progress update: {status: "pending", ...}
[CLARA] Analysis response: {status: "completed", count: N}
```

### Check Server Logs
Look for:
```
=== START ANALYSIS CALLED ===
Analysis type: pubmed
Session keys: ['api_provider', 'api_key', 'model', ...]
```

### Common Issues

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| No POST in logs | JavaScript error | Check browser console for errors |
| 400 Error | API key not valid | Ensure settings saved correctly |
| 500 Error | Analysis service error | Check server logs for traceback |
| Stuck on "pending" | POST never made | Check jQuery loaded, no CORS issues |

## Key Files

| File | Purpose |
|------|---------|
| `app/routes.py` | Flask routes and API endpoints |
| `app/services/analysis_service.py` | Core analysis logic |
| `app/utils/pubmed_utils.py` | PubMed search functions |
| `app/utils/openai_utils.py` | OpenAI API calls |
| `app/utils/claude_utils.py` | Claude API calls |
| `app/templates/results.html` | Results page with JS |

## Testing Each Step

```bash
# Test 1: Verify PubMed search works
python test_analysis_flow.py test_pubmed_search

# Test 2: Verify API client creation
python test_analysis_flow.py test_api_client

# Test 3: Verify analysis service
python test_analysis_flow.py test_analysis_service

# Test 4: Test Flask routes
python test_analysis_flow.py test_flask_routes

# Test 5: JavaScript debugging info
python test_analysis_flow.py test_javascript

# Run all tests
python test_analysis_flow.py all
```

## Quick Browser Console Test

Run this in the browser console to test the API directly:
```javascript
// Test if the analysis API is reachable
fetch('/api/start-analysis', {method: 'POST'})
  .then(r => r.json())
  .then(d => console.log('Response:', d))
  .catch(e => console.error('Error:', e));

// Check analysis status
fetch('/api/analysis-status')
  .then(r => r.json())
  .then(d => console.log('Status:', d));

// Check if jQuery is loaded
console.log('jQuery loaded:', typeof $ === 'function');
```
