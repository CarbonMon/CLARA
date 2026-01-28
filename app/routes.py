from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify, current_app, flash, send_file
from app.forms import APISettingsForm, PubMedSearchForm, PDFUploadForm
from app.services.analysis_service import AnalysisService
from app.services.export_service import create_excel_file
from app.utils.api_utils import validate_openai_api_key, validate_anthropic_api_key
from app.utils.pubmed_utils import configure_entrez
import os
import io
import pandas as pd
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    form = APISettingsForm()
    
    # Update model choices based on the selected provider
    if request.method == 'GET':
        provider = session.get('api_provider', 'openai')
    else:
        provider = form.api_provider.data
    
    # Set model choices based on provider
    if provider == 'openai':
        form.model.choices = [(k, v) for k, v in current_app.config['OPENAI_MODELS'].items()]
    else:
        form.model.choices = [(k, v) for k, v in current_app.config['CLAUDE_MODELS'].items()]
    
    if form.validate_on_submit():
        provider = form.api_provider.data
        api_key = form.api_key.data
        model = form.model.data
        
        # Validate API key
        if provider == 'openai':
            is_valid, error = validate_openai_api_key(api_key)
        else:
            is_valid, error = validate_anthropic_api_key(api_key)
        
        if is_valid:
            # Store in session
            session['api_provider'] = provider
            session['api_key'] = api_key
            session['model'] = model
            session['api_key_valid'] = True
            
            flash('API settings saved successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash(f'API Key Invalid: {error}', 'danger')
    
    # Check for .env file configuration and auto-configure if available
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Auto-detect API keys from .env (only non-empty keys)
    openai_key = os.environ.get('OPENAI_KEY', '').strip()
    anthropic_key = os.environ.get('ANTHROPIC_KEY', '').strip()
    
    # If keys are in .env and no session configuration exists, auto-configure
    # Check Anthropic first if it's available (based on .env MODEL setting)
    if (openai_key or anthropic_key) and not session.get('api_key_valid'):
        # Determine preferred provider from .env MODEL setting
        model_setting = os.environ.get('MODEL', '').lower()
        prefer_anthropic = 'anthropic' in model_setting or 'claude' in model_setting or 'haiku' in model_setting
        
        # Try preferred provider first
        if prefer_anthropic and anthropic_key:
            is_valid, error = validate_anthropic_api_key(anthropic_key)
            if is_valid:
                session['api_provider'] = 'anthropic'
                session['api_key'] = anthropic_key
                session['model'] = current_app.config['DEFAULT_CLAUDE_MODEL']
                session['api_key_valid'] = True
                flash('Auto-configured Anthropic API settings from .env file!', 'success')
                return redirect(url_for('main.index'))
        
        # Try OpenAI if available
        if openai_key:
            is_valid, error = validate_openai_api_key(openai_key)
            if is_valid:
                session['api_provider'] = 'openai'
                session['api_key'] = openai_key
                session['model'] = current_app.config['DEFAULT_OPENAI_MODEL']
                session['api_key_valid'] = True
                flash('Auto-configured OpenAI API settings from .env file!', 'success')
                return redirect(url_for('main.index'))
        
        # Fallback to Anthropic if OpenAI wasn't preferred but Anthropic is available
        if not prefer_anthropic and anthropic_key:
            is_valid, error = validate_anthropic_api_key(anthropic_key)
            if is_valid:
                session['api_provider'] = 'anthropic'
                session['api_key'] = anthropic_key
                session['model'] = current_app.config['DEFAULT_CLAUDE_MODEL']
                session['api_key_valid'] = True
                flash('Auto-configured Anthropic API settings from .env file!', 'success')
                return redirect(url_for('main.index'))
    
    # Pre-fill form with session data if available
    if 'api_provider' in session:
        form.api_provider.data = session.get('api_provider')
    if 'model' in session:
        form.model.data = session.get('model')
    
    return render_template('settings.html', form=form, 
                         openai_key_available=bool(openai_key),
                         anthropic_key_available=bool(anthropic_key))

@bp.route('/pubmed-search', methods=['GET', 'POST'])
def pubmed_search():
    # Redirect to settings if API key is not configured
    if not session.get('api_key_valid'):
        flash('Please configure your API settings first', 'warning')
        return redirect(url_for('main.settings'))
    
    form = PubMedSearchForm()
    
    if form.validate_on_submit():
        # Store search parameters in session
        session['query'] = form.query.data
        session['search_mode'] = form.search_mode.data
        
        # Set max_results based on search mode
        if form.search_mode.data == 'full':
            # For full analysis, we'll use a large number (10000) to get all results
            session['max_results'] = 10000
        else:
            # For partial analysis, use the user-specified max_results
            session['max_results'] = form.max_results.data
        
        # Redirect to results page which will handle the analysis
        return redirect(url_for('main.analyze_pubmed'))
    
    return render_template('pubmed_search.html', form=form)

@bp.route('/api/pubmed-count')
def pubmed_count():
    """API endpoint to get PubMed paper count for a query"""
    query = request.args.get('query', '').strip()
    
    if not query:
        return jsonify({'status': 'error', 'message': 'No query provided'}), 400
    
    try:
        from app.utils.pubmed_utils import get_pubmed_count
        # Add clinical trial filter to match what will actually be analyzed
        query_with_filter = query + " AND (clinicaltrial[filter])"
        count = get_pubmed_count(query_with_filter)
        
        if count is None:
            return jsonify({'status': 'error', 'message': 'Unable to retrieve paper count'}), 500
        
        return jsonify({'status': 'success', 'count': count})
    except Exception as e:
        logger.error(f"PubMed count error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/analyze-pubmed')
def analyze_pubmed():
    # Check if the necessary session variables are set
    if not all(k in session for k in ['query', 'max_results', 'api_provider', 'api_key', 'model']):
        flash('Missing required parameters', 'danger')
        return redirect(url_for('main.pubmed_search'))
    
    # Store analysis job in session
    session['analysis_type'] = 'pubmed'
    session['analysis_status'] = 'pending'
    
    return render_template('results.html', 
                          analysis_type='pubmed',
                          query=session.get('query'),
                          max_results=session.get('max_results'),
                          is_new_analysis=True)

@bp.route('/pdf-upload', methods=['GET', 'POST'])
def pdf_upload():
    # Redirect to settings if API key is not configured
    if not session.get('api_key_valid'):
        flash('Please configure your API settings first', 'warning')
        return redirect(url_for('main.settings'))
    
    form = PDFUploadForm()
    
    if form.validate_on_submit():
        # Create upload directory if it doesn't exist
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        uploaded_files = request.files.getlist('files')
        filenames = []
        
        for file in uploaded_files:
            if file.filename:
                # Generate a secure filename to avoid conflicts
                secure_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_name)
                file.save(file_path)
                filenames.append({'path': file_path, 'name': file.filename})
        
        # Store parameters in session
        session['pdf_files'] = filenames
        session['use_ocr'] = form.use_ocr.data
        session['language'] = current_app.config['SUPPORTED_LANGUAGES'][form.language.data]
        
        # Redirect to results page which will handle the analysis
        return redirect(url_for('main.analyze_pdf'))
    
    return render_template('pdf_upload.html', form=form)

@bp.route('/analyze-pdf')
def analyze_pdf():
    # Check if the necessary session variables are set
    if not all(k in session for k in ['pdf_files', 'use_ocr', 'language', 'api_provider', 'api_key', 'model']):
        flash('Missing required parameters', 'danger')
        return redirect(url_for('main.pdf_upload'))
    
    # Store analysis job in session
    session['analysis_type'] = 'pdf'
    session['analysis_status'] = 'pending'
    
    pdf_filenames = [f['name'] for f in session.get('pdf_files', [])]
    
    return render_template('results.html', 
                          analysis_type='pdf',
                          files=pdf_filenames,
                          use_ocr=session.get('use_ocr'),
                          language=session.get('language'),
                          is_new_analysis=True)

@bp.route('/view-results')
def view_results():
    """View the most recent analysis results"""
    # Check if there are any analysis results to show
    if not session.get('analysis_results'):
        flash('No analysis results found', 'warning')
        return redirect(url_for('main.index'))
    
    # Get analysis details from session
    analysis_type = session.get('analysis_type')
    
    if analysis_type == 'pubmed':
        return render_template('results.html',
                              analysis_type='pubmed',
                              query=session.get('query'),
                              max_results=session.get('max_results'),
                              is_new_analysis=False)
    else:  # pdf
        pdf_filenames = []
        if session.get('pdf_files'):
            pdf_filenames = [f['name'] for f in session.get('pdf_files', [])]
        
        return render_template('results.html',
                              analysis_type='pdf',
                              files=pdf_filenames,
                              use_ocr=session.get('use_ocr'),
                              language=session.get('language'),
                              is_new_analysis=False)

@bp.route('/api/start-analysis', methods=['POST'])
def start_analysis():
    """
    API endpoint to start the analysis process
    
    Flow:
    1. Validate session has API key
    2. Get analysis type (pubmed or pdf)
    3. Create AI client (OpenAI or Claude)
    4. Run analysis
    5. Store results in session
    """
    logger.info("=== START ANALYSIS CALLED ===")
    
    # Step 1: Validate API settings
    if not session.get('api_key_valid'):
        logger.error("API key not valid in session")
        return jsonify({'status': 'error', 'message': 'API key not configured'}), 400
    
    analysis_type = session.get('analysis_type')
    logger.info(f"Analysis type: {analysis_type}")
    logger.info(f"Session keys: {list(session.keys())}")
    
    # Step 2: Initialize progress tracking
    session['progress'] = 0
    session['total_papers'] = 0
    session['analysis_status'] = 'running'
    session['current_paper'] = ''
    import time
    session['start_time'] = time.time()
    
    # Create analysis service
    if session['api_provider'] == 'openai':
        from app.utils.openai_utils import create_openai_client
        client = create_openai_client(session['api_key'])
    else:  # anthropic
        from app.utils.claude_utils import create_claude_client
        client = create_claude_client(session['api_key'])
    
    analysis_service = AnalysisService(
        client, 
        session['api_provider'],
        session['model']
    )
    
    try:
        if analysis_type == 'pubmed':
            # Configure NCBI credentials if available
            if current_app.config.get('NCBI_EMAIL') and current_app.config.get('NCBI_API_KEY'):
                configure_entrez(current_app.config['NCBI_EMAIL'], current_app.config['NCBI_API_KEY'])
            
            # Start PubMed analysis
            results = analysis_service.analyze_pubmed_papers(
                session['query'] + " AND (clinicaltrial[filter])", 
                session['max_results'],
                action="new"
            )
            
        elif analysis_type == 'pdf':
            # Get PDF files from session
            pdf_files = session.get('pdf_files', [])
            
            # Initialize total for PDF analysis
            session['total_papers'] = len(pdf_files)
            session['progress'] = 0
            
            # Start PDF analysis
            results = analysis_service.analyze_pdf_files(
                pdf_files,
                session.get('use_ocr', False),
                session.get('language', 'eng'),
                action="new"
            )
        else:
            return jsonify({'status': 'error', 'message': 'Invalid analysis type'}), 400
        
        # Store results in session and mark as completed
        session['analysis_results'] = [result for result in results]
        session['analysis_status'] = 'completed'
        session['progress'] = len(results)
        session['analysis_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'status': 'completed',
            'message': 'Analysis completed',
            'count': len(results)
        })
    
    except Exception as e:
        session['analysis_status'] = 'error'
        logger.error(f"Analysis error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/analysis-status')
def analysis_status():
    """API endpoint to check analysis status"""
    status = session.get('analysis_status', 'unknown')
    results = session.get('analysis_results', [])
    progress = session.get('progress', 0)
    total_papers = session.get('total_papers', 0)
    
    return jsonify({
        'status': status,
        'completed': status == 'completed',
        'count': len(results) if results else 0,
        'progress': progress,
        'total': total_papers,
        'progress_percent': int((progress / total_papers) * 100) if total_papers > 0 else 0
    })

@bp.route('/api/analysis-progress')
def analysis_progress():
    """API endpoint to get detailed progress information"""
    progress = session.get('progress', 0)
    total_papers = session.get('total_papers', 0)
    current_paper = session.get('current_paper', '')
    status = session.get('analysis_status', 'unknown')
    
    return jsonify({
        'progress': progress,
        'total': total_papers,
        'progress_percent': int((progress / total_papers) * 100) if total_papers > 0 else 0,
        'current_paper': current_paper,
        'status': status,
        'eta': calculate_eta(progress, total_papers, session.get('start_time'))
    })

def calculate_eta(progress, total, start_time):
    """Calculate estimated time remaining"""
    if not start_time or progress == 0 or progress >= total:
        return None
    
    try:
        import time
        elapsed = time.time() - start_time
        rate = progress / elapsed
        remaining = (total - progress) / rate
        return int(remaining)
    except:
        return None

@bp.route('/api/results')
def get_results():
    """API endpoint to get analysis results"""
    results = session.get('analysis_results', [])
    return jsonify(results)

@bp.route('/download-excel')
def download_excel():
    """Download results as Excel file"""
    results = session.get('analysis_results', [])
    
    if not results:
        flash('No results to download', 'warning')
        return redirect(url_for('main.index'))
    
    # Generate filename based on analysis type
    if session.get('analysis_type') == 'pubmed':
        query_word = session.get('query', 'search').split()[0]
        filename = f"PubMed_{query_word}_{datetime.now().strftime('%y%m%d')}.xlsx"
    else:
        filename = f"PDF_Analysis_{datetime.now().strftime('%y%m%d')}.xlsx"
    
    # Create Excel file
    excel_file = create_excel_file(results, filename)
    
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@bp.route('/clear-results', methods=['POST'])
def clear_results():
    """Clear all results from the session"""
    # Clear analysis results
    session.pop('analysis_results', None)
    session.pop('analysis_status', None)
    session.pop('analysis_type', None)
    session.pop('analysis_timestamp', None)
    
    # Clear PubMed search parameters
    session.pop('query', None)
    session.pop('max_results', None)
    
    # Clear PDF parameters
    session.pop('pdf_files', None)
    session.pop('use_ocr', None)
    session.pop('language', None)
    
    # Cleanup temporary files
    if session.get('pdf_files'):
        for file_info in session.get('pdf_files', []):
            try:
                if os.path.exists(file_info['path']):
                    os.remove(file_info['path'])
            except Exception as e:
                current_app.logger.error(f"Error deleting file {file_info['path']}: {e}")
    
    return jsonify({'status': 'success'})

@bp.route('/download-pdf-text/<int:index>')
def download_pdf_text(index):
    """Download extracted text from a PDF file"""
    pdf_files = session.get('pdf_files', [])
    
    if index < 0 or index >= len(pdf_files):
        flash('Invalid PDF index', 'danger')
        return redirect(url_for('main.index'))
    
    # Get the file info
    file_info = pdf_files[index]
    
    # Get analysis results to find the text
    results = session.get('analysis_results', [])
    
    # Try to find matching result
    text_content = "No text content available"
    for result in results:
        if result.get('Filename') == file_info['name']:
            # Create a text summary from the analysis results
            text_content = f"# Analysis of {file_info['name']}\n\n"
            for key, value in result.items():
                if key != 'Filename' and value:
                    text_content += f"## {key}\n{value}\n\n"
            break
    
    # If no matching result found, try to extract the text directly
    if text_content == "No text content available":
        try:
            from app.utils.pdf_utils import process_file
            processed = process_file(
                file_info,
                session.get('use_ocr', False),
                session.get('language', 'eng')
            )
            text_content = processed.get('content', "No text content available")
        except Exception as e:
            text_content = f"Error extracting text: {str(e)}"
    
    # Create text file
    text_file = io.BytesIO(text_content.encode('utf-8'))
    
    return send_file(
        text_file,
        as_attachment=True,
        download_name=f"{file_info['name']}.txt",
        mimetype='text/plain'
    )

@bp.route('/api/selected-results', methods=['POST'])
def selected_results():
    """API endpoint to get selected results for download"""
    data = request.json
    if not data or 'indices' not in data:
        return jsonify({'status': 'error', 'message': 'No indices provided'}), 400
    
    results = session.get('analysis_results', [])
    selected_indices = data['indices']
    
    selected_results = [results[i] for i in selected_indices if i < len(results)]
    
    if not selected_results:
        return jsonify({'status': 'error', 'message': 'No valid results selected'}), 400
    
    # Store selected results in session
    session['selected_results'] = selected_results
    
    return jsonify({'status': 'success', 'count': len(selected_results)})

@bp.route('/download-selected-excel')
def download_selected_excel():
    """Download selected results as Excel file"""
    results = session.get('selected_results', [])
    
    if not results:
        flash('No results selected for download', 'warning')
        return redirect(url_for('main.index'))
    
    # Generate filename
    filename = f"Selected_Results_{datetime.now().strftime('%y%m%d')}.xlsx"
    
    # Create Excel file
    excel_file = create_excel_file(results, filename)
    
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@bp.route('/cleanup-temp-files', methods=['POST'])
def cleanup_temp_files():
    """Clean up temporary files after analysis is complete"""
    pdf_files = session.get('pdf_files', [])
    
    for file_info in pdf_files:
        try:
            if os.path.exists(file_info['path']):
                os.remove(file_info['path'])
        except Exception as e:
            # Log error but continue
            current_app.logger.error(f"Error deleting file {file_info['path']}: {e}")
    
    # Clear the files from session
    session.pop('pdf_files', None)
    
    return jsonify({'status': 'success'})
