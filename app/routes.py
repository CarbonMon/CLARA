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
    
    # Pre-fill form with session data if available
    if 'api_provider' in session:
        form.api_provider.data = session.get('api_provider')
    if 'model' in session:
        form.model.data = session.get('model')
    
    return render_template('settings.html', form=form)

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
        session['max_results'] = form.max_results.data
        
        # Redirect to results page which will handle the analysis
        return redirect(url_for('main.analyze_pubmed'))
    
    return render_template('pubmed_search.html', form=form)

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
                # Save file temporarily
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                filenames.append(file_path)
        
        # Store parameters in session
        session['pdf_files'] = filenames
        session['use_ocr'] = form.use_ocr.data
        session['language'] = current_app.config['SUPPORTED_LANGUAGES'][form.language.data]
        
        # Redirect to results page which will handle the analysis
        return redirect(url_for('main.analyze_pdf'))
    
    return render_template('pdf_upload.html', form=form)

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
                          max_results=session.get('max_results'))

@bp.route('/analyze-pdf')
def analyze_pdf():
    # Check if the necessary session variables are set
    if not all(k in session for k in ['pdf_files', 'use_ocr', 'language', 'api_provider', 'api_key', 'model']):
        flash('Missing required parameters', 'danger')
        return redirect(url_for('main.pdf_upload'))
    
    # Store analysis job in session
    session['analysis_type'] = 'pdf'
    session['analysis_status'] = 'pending'
    
    pdf_filenames = [os.path.basename(f) for f in session.get('pdf_files', [])]
    
    return render_template('results.html', 
                          analysis_type='pdf',
                          files=pdf_filenames,
                          use_ocr=session.get('use_ocr'),
                          language=session.get('language'))

@bp.route('/api/start-analysis', methods=['POST'])
def start_analysis():
    """API endpoint to start the analysis process"""
    # Check if API settings are valid
    if not session.get('api_key_valid'):
        return jsonify({'status': 'error', 'message': 'API key not configured'}), 400
    
    analysis_type = session.get('analysis_type')
    
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
                session['query'] + " AND (clinicaltrial[filter]", 
                session['max_results'],
                action="new"
            )
            
        elif analysis_type == 'pdf':
            # Prepare PDF files
            pdf_files = []
            for filepath in session.get('pdf_files', []):
                with open(filepath, 'rb') as f:
                    # Create file-like object with name attribute
                    file_obj = type('', (), {})()
                    file_obj.read = lambda: f.read()
                    file_obj.name = os.path.basename(filepath)
                    pdf_files.append(file_obj)
            
            # Start PDF analysis
            results = analysis_service.analyze_pdf_files(
                pdf_files,
                session.get('use_ocr', False),
                session.get('language', 'eng'),
                action="new"
            )
        else:
            return jsonify({'status': 'error', 'message': 'Invalid analysis type'}), 400
        
        # Store results in session
        session['analysis_results'] = [result for result in results]
        session['analysis_status'] = 'completed'
        
        return jsonify({'status': 'success', 'message': 'Analysis completed'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/analysis-status')
def analysis_status():
    """API endpoint to check analysis status"""
    status = session.get('analysis_status', 'unknown')
    results = session.get('analysis_results', [])
    
    return jsonify({
        'status': status,
        'completed': status == 'completed',
        'count': len(results) if results else 0
    })

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
    
    # Clear PubMed search parameters
    session.pop('query', None)
    session.pop('max_results', None)
    
    # Clear PDF parameters
    session.pop('pdf_files', None)
    session.pop('use_ocr', None)
    session.pop('language', None)
    
    return jsonify({'status': 'success'})
