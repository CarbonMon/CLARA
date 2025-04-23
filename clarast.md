## Tree for 
```
├── app/
│   ├── config.py
│   ├── forms.py
│   ├── routes.py
│   ├── services/
│   │   ├── analysis_service.py
│   │   ├── export_service.py
│   │   └── __init__
│   ├── static/
│   │   └── css/
│   │       ├── js/
│   │       │   └── main.js
│   │       └── style.css
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── pdf_upload.html
│   │   ├── pubmed_search.html
│   │   ├── results.html
│   │   └── settings.html
│   ├── utils/
│   │   ├── api_utils.py
│   │   ├── claude_utils.py
│   │   ├── openai_utils.py
│   │   ├── pdf_utils.py
│   │   ├── prompts.py
│   │   ├── pubmed_utils.py
│   │   └── __init__.py
│   └── __init__.py
├── requirements.txt
└── run.py
```

## File: requirements.txt
```
flask>=2.0.1
flask-wtf>=1.0.0
flask-session>=0.4.0
pandas>=1.5.3
openai>=1.6.0
anthropic>=0.8.0
biopython>=1.81
requests>=2.31.0
pdf2image>=1.16.3
pytesseract>=0.3.10
Pillow>=10.0.0
PyPDF2>=3.0.1
openpyxl>=3.1.2
gunicorn>=20.1.0  # For production deployment
```
## File: run.py
```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
```
## File: app\config.py
```python
import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development-only'
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Application configuration
    APP_TITLE = "Clinical Research Analysis Tool"
    OPENAI_MODELS = {
        "gpt-4o": "GPT-4o",
        "gpt-4-turbo": "GPT-4 Turbo",
        "gpt-3.5-turbo": "GPT-3.5 Turbo"
    }
    CLAUDE_MODELS = {
        "claude-3-opus-20240229": "Claude 3 Opus",
        "claude-3-sonnet-20240229": "Claude 3 Sonnet",
        "claude-3-haiku-20240307": "Claude 3 Haiku"
    }
    DEFAULT_OPENAI_MODEL = "gpt-4o"
    DEFAULT_CLAUDE_MODEL = "claude-3-sonnet-20240229"
    MAX_PUBMED_RESULTS = 400
    DEFAULT_PUBMED_RESULTS = 20
    SUPPORTED_LANGUAGES = {
        'English': 'eng',
        'French': 'fra',
        'Arabic': 'ara',
        'Spanish': 'spa',
    }
    
    # NCBI Credentials - from environment or to be set via UI
    NCBI_EMAIL = os.environ.get('NCBI_EMAIL')
    NCBI_API_KEY = os.environ.get('NCBI_API_KEY')
```
## File: app\forms.py
```python
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, IntegerField, SelectField, BooleanField, SubmitField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Optional
from app.config import Config

class APISettingsForm(FlaskForm):
    """Form for API settings"""
    api_provider = SelectField('API Provider', choices=[
        ('openai', 'OpenAI'), 
        ('anthropic', 'Anthropic')
    ])
    api_key = PasswordField('API Key', validators=[DataRequired()])
    model = SelectField('Model', validators=[DataRequired()])
    submit = SubmitField('Save Settings')
    
    def __init__(self, *args, **kwargs):
        super(APISettingsForm, self).__init__(*args, **kwargs)
        # Model choices will be updated in the route based on provider selection

class PubMedSearchForm(FlaskForm):
    """Form for PubMed search"""
    query = StringField('Search Query', validators=[DataRequired()])
    max_results = IntegerField('Max Results', 
                              validators=[
                                  DataRequired(),
                                  NumberRange(min=1, max=Config.MAX_PUBMED_RESULTS)
                              ],
                              default=Config.DEFAULT_PUBMED_RESULTS)
    submit = SubmitField('Start Analysis')

class PDFUploadForm(FlaskForm):
    """Form for PDF upload"""
    files = FileField('Upload Clinical Trial PDF(s)', 
                     validators=[
                         FileRequired(),
                         FileAllowed(['pdf', 'png', 'jpg', 'jpeg'], 'PDFs and images only!')
                     ],
                     render_kw={"multiple": True})
    
    use_ocr = BooleanField('Enable OCR (for scanned documents)', default=False)
    language = SelectField('Document Language', choices=[(k, k) for k in Config.SUPPORTED_LANGUAGES.keys()], default='English')
    submit = SubmitField('Process and Analyze')
```
## File: app\routes.py
```python
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
            # Get PDF files from session
            pdf_files = session.get('pdf_files', [])
            
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
```
## File: app\__init__.py
```python
from flask import Flask
from flask_session import Session
import os

session = Session()

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    if test_config is None:
        app.config.from_object('app.config.Config')
    else:
        app.config.from_mapping(test_config)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize session
    session.init_app(app)
    
    # Register blueprints
    from app import routes
    app.register_blueprint(routes.bp)
    
    return app
```
## File: app\services\analysis_service.py
```python
from typing import List, Dict, Any, Optional, Union, BinaryIO
import logging
from openai import OpenAI
from anthropic import Anthropic
from app.utils.openai_utils import analyze_paper_with_openai
from app.utils.claude_utils import analyze_paper_with_claude
from app.utils.pubmed_utils import search_and_fetch_pubmed
from app.utils.pdf_utils import process_file

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for analyzing papers from PubMed or PDFs"""
    
    def __init__(self, client: Union[OpenAI, Anthropic], provider: str = "openai", model: str = None):
        self.client = client
        self.provider = provider.lower()
        self.model = model
    
    def analyze_pubmed_papers(self, query: str, max_results: int, action: str = "new") -> List[Dict[str, Any]]:
        """
        Search PubMed and analyze papers
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results
            action: "new" to start fresh or "append" to existing results
            
        Returns:
            List of analyzed papers
        """
        papers = search_and_fetch_pubmed(query, max_results)
        if 'PubmedArticle' not in papers or not papers['PubmedArticle']:
            logger.warning("No papers found for query: %s", query)
            return []

        results = []
        for paper in papers['PubmedArticle']:
            try:
                if self.provider == "openai":
                    result = analyze_paper_with_openai(
                        self.client, 
                        paper, 
                        is_pdf=False,
                        model=self.model
                    )
                else:  # anthropic
                    result = analyze_paper_with_claude(
                        self.client, 
                        paper, 
                        is_pdf=False,
                        model=self.model
                    )
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing paper: {e}")
                # Add error record
                results.append({
                    "Title": "Error analyzing paper",
                    "Error": str(e)
                })

        return results
    
    def analyze_pdf_files(
        self, 
        pdf_files: List[Any], 
        use_ocr: bool = False, 
        language: str = "eng", 
        action: str = "new"
    ) -> List[Dict[str, Any]]:
        """
        Process and analyze PDF files
        
        Args:
            pdf_files: List of PDF file objects
            use_ocr: Whether to use OCR
            language: Language code for OCR
            action: "new" to start fresh or "append" to existing results
            
        Returns:
            List of analyzed papers
        """
        results = []
        pdf_texts = []
        
        for pdf_file in pdf_files:
            try:
                # Process the file
                processed_file = process_file(pdf_file, use_ocr, language)
                
                # Store extracted text
                pdf_texts.append({
                    'filename': processed_file['filename'],
                    'content': processed_file['content']
                })
                
                # Analyze the PDF content
                if self.provider == "openai":
                    result = analyze_paper_with_openai(
                        self.client, 
                        processed_file['content'], 
                        is_pdf=True,
                        model=self.model
                    )
                else:  # anthropic
                    result = analyze_paper_with_claude(
                        self.client, 
                        processed_file['content'], 
                        is_pdf=True,
                        model=self.model
                    )
                # Add filename to result
                result['Filename'] = pdf_file.name
                results.append(result)
            
            except Exception as e:
                logger.error(f"Error processing PDF: {e}")
                # Add error record
                results.append({
                    "Title": f"Error processing {pdf_file.name}",
                    "Filename": pdf_file.name,
                    "Error": str(e)
                })
        
        return results
```
## File: app\services\export_service.py
```python
import pandas as pd
import io
from typing import List, Dict, Any

def create_excel_file(data: List[Dict[str, Any]], filename: str) -> io.BytesIO:
    """
    Create an Excel file from a list of dictionaries
    
    Args:
        data: List of dictionaries to convert to Excel
        filename: Name of the Excel file
        
    Returns:
        BytesIO object containing the Excel file
    """
    df = pd.DataFrame(data)
    excel_file = io.BytesIO()
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    excel_file.seek(0)
    return excel_file
```
## File: app\services\__init__
```

```
## File: app\templates\base.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Clinical Research Analysis Tool{% endblock %}</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    
    <!-- DataTables CSS -->
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    
    <!-- Custom CSS -->
    <link href="{{ url_for('static', filename='css/style.css') }}" rel="stylesheet">
    
    {% block head %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('main.index') }}">
                <i class="fas fa-microscope me-2"></i>
                Clinical Research Analysis Tool
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link {% if request.path == url_for('main.index') %}active{% endif %}" href="{{ url_for('main.index') }}">
                            <i class="fas fa-home me-1"></i> Home
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.path == url_for('main.pubmed_search') %}active{% endif %}" href="{{ url_for('main.pubmed_search') }}">
                            <i class="fas fa-search me-1"></i> PubMed Search
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.path == url_for('main.pdf_upload') %}active{% endif %}" href="{{ url_for('main.pdf_upload') }}">
                            <i class="fas fa-file-pdf me-1"></i> PDF Upload
                        </a>
                    </li>
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link {% if request.path == url_for('main.settings') %}active{% endif %}" href="{{ url_for('main.settings') }}">
                            <i class="fas fa-cog me-1"></i> Settings
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Flash messages -->
    <div class="container mt-3">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    </div>

    <!-- Main content -->
    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <!-- Footer -->
    <footer class="bg-light text-center text-lg-start mt-5">
        <div class="container p-4">
            <div class="text-center p-3">
                © 2024 Clinical Research Analysis Tool
            </div>
        </div>
    </footer>

    <!-- Bootstrap 5 JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    
    <!-- DataTables JS -->
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    
    <!-- Custom JS -->
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    
    {% block scripts %}{% endblock %}
</body>
</html>
```
## File: app\templates\index.html
```html
{% extends 'base.html' %}

{% block title %}Clinical Research Analysis Tool{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-10">
        <div class="card shadow-lg">
            <div class="card-header bg-primary text-white">
                <h2 class="mb-0"><i class="fas fa-microscope me-2"></i>Welcome to the Clinical Research Analysis Tool</h2>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-lg-6">
                        <h3 class="mb-4">Analyze Clinical Research with AI</h3>
                        <p class="lead">
                            This tool helps researchers and healthcare professionals analyze clinical trial data from multiple sources using advanced AI models.
                        </p>
                        <p>
                            Our platform leverages the power of OpenAI and Anthropic models to extract and summarize key information from clinical research papers and documents.
                        </p>
                        <div class="mt-4">
                            <h4>Key Features:</h4>
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item"><i class="fas fa-search text-primary me-2"></i> Search and analyze PubMed clinical trials</li>
                                <li class="list-group-item"><i class="fas fa-file-pdf text-primary me-2"></i> Upload and analyze clinical trial PDFs</li>
                                <li class="list-group-item"><i class="fas fa-robot text-primary me-2"></i> Advanced AI extraction of study parameters</li>
                                <li class="list-group-item"><i class="fas fa-table text-primary me-2"></i> Export results to Excel for further analysis</li>
                            </ul>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="card bg-light mb-4">
                            <div class="card-body text-center">
                                <h3 class="card-title">Get Started</h3>
                                <p>Choose one of the options below to begin analyzing clinical research</p>
                                <div class="d-grid gap-3">
                                    <a href="{{ url_for('main.pubmed_search') }}" class="btn btn-primary btn-lg">
                                        <i class="fas fa-search me-2"></i> PubMed Search
                                    </a>
                                    <a href="{{ url_for('main.pdf_upload') }}" class="btn btn-success btn-lg">
                                        <i class="fas fa-file-pdf me-2"></i> PDF Upload
                                    </a>
                                </div>
                            </div>
                        </div>
                        
                        {% if not session.get('api_key_valid') %}
                        <div class="alert alert-warning">
                            <h4><i class="fas fa-exclamation-triangle me-2"></i>API Setup Required</h4>
                            <p>You need to configure your API settings before you can use the analysis features.</p>
                            <a href="{{ url_for('main.settings') }}" class="btn btn-warning">
                                <i class="fas fa-cog me-2"></i> Configure API Settings
                            </a>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```
## File: app\templates\pdf_upload.html
```html
{% extends 'base.html' %}

{% block title %}PDF Upload - Clinical Research Analysis Tool{% endblock %}

{% block content %}
<div class="card shadow-lg">
    <div class="card-header bg-primary text-white">
        <h2 class="mb-0"><i class="fas fa-file-pdf me-2"></i>Clinical Trial PDF Analysis</h2>
    </div>
    <div class="card-body">
        <p class="lead">Upload PDF documents containing clinical trial information for AI analysis.</p>
        
        <form method="POST" action="{{ url_for('main.pdf_upload') }}" enctype="multipart/form-data" id="uploadForm">
            {{ form.csrf_token }}
            
            <div class="mb-4">
                <label class="form-label d-block">{{ form.files.label }}</label>
                <div class="custom-file-upload" id="file-dropzone">
                    <i class="fas fa-cloud-upload-alt fa-3x mb-3"></i>
                    <p class="mb-0">Drag and drop files here or click to browse</p>
                    <small class="text-muted d-block mt-2">Supported formats: PDF, PNG, JPG</small>
                </div>
                {{ form.files(id="file-input", style="position: absolute; left: -9999px;") }}
                <div id="file-list" class="mt-3">
                    <!-- Selected files will appear here -->
                </div>
                {% if form.files.errors %}
                <div class="invalid-feedback d-block mt-2">
                    {% for error in form.files.errors %}
                        {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="form-check">
                        {{ form.use_ocr(class="form-check-input") }}
                        <label class="form-check-label" for="use_ocr">
                            {{ form.use_ocr.label.text }}
                        </label>
                        <div class="form-text">
                            Enable for scanned documents or images where text cannot be directly extracted
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6" id="language-selector" style="display: none;">
                    <label class="form-label">{{ form.language.label }}</label>
                    {{ form.language(class="form-select") }}
                    <div class="form-text">
                        Select the primary language of the document for OCR processing
                    </div>
                </div>
            </div>
            
            <div class="alert alert-info">
                <h5><i class="fas fa-info-circle me-2"></i>PDF Analysis Information</h5>
                <p>The AI will analyze the uploaded documents to extract information such as:</p>
                <ul>
                    <li>Study design and methodology</li>
                    <li>Patient population and demographics</li>
                    <li>Interventions and treatments</li>
                    <li>Primary and secondary outcomes</li>
                    <li>Statistical analyses and results</li>
                </ul>
                <p class="mb-0">For best results, upload clearly formatted clinical trial documents.</p>
            </div>
            
            <div class="d-grid gap-2 col-lg-4 col-md-6 mx-auto mt-4">
                {{ form.submit(class="btn btn-primary btn-lg", id="submit-btn", disabled="disabled") }}
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    $(document).ready(function() {
        const dropzone = $('#file-dropzone');
        const fileInput = $('#file-input');
        const fileList = $('#file-list');
        const submitBtn = $('#submit-btn');
        const ocrCheckbox = $('#use_ocr');
        const languageSelector = $('#language-selector');
        const uploadForm = $('#uploadForm');
        
        // Store the DataTransfer object for managing files
        const dataTransfer = new DataTransfer();
        
        // Toggle language selector based on OCR checkbox
        ocrCheckbox.on('change', function() {
            if ($(this).is(':checked')) {
                languageSelector.slideDown(300);
            } else {
                languageSelector.slideUp(300);
            }
        });
        
        // Handle file dropzone click - open file dialog
        dropzone.on('click', function(e) {
            fileInput.click();
        });
        
        // Handle drag and drop events
        dropzone.on('dragover', function(e) {
            e.preventDefault();
            dropzone.addClass('dragover');
        });
        
        dropzone.on('dragleave', function(e) {
            e.preventDefault();
            dropzone.removeClass('dragover');
        });
        
        dropzone.on('drop', function(e) {
            e.preventDefault();
            dropzone.removeClass('dragover');
            
            if (e.originalEvent.dataTransfer && e.originalEvent.dataTransfer.files.length) {
                // Add new files to our collection
                const newFiles = e.originalEvent.dataTransfer.files;
                for (let i = 0; i < newFiles.length; i++) {
                    // Check if it's a valid file type
                    const fileType = newFiles[i].type;
                    if (fileType === 'application/pdf' || fileType.startsWith('image/')) {
                        dataTransfer.items.add(newFiles[i]);
                    }
                }
                
                // Update the file input with all files
                fileInput[0].files = dataTransfer.files;
                updateFileList();
            }
        });
        
        // Handle file selection via file dialog
        fileInput.on('change', function(e) {
            // Add new files to our collection
            const newFiles = e.target.files;
            for (let i = 0; i < newFiles.length; i++) {
                // Check if it's a valid file type
                const fileType = newFiles[i].type;
                if (fileType === 'application/pdf' || fileType.startsWith('image/')) {
                    dataTransfer.items.add(newFiles[i]);
                }
            }
            
            // Update the file input with all files
            fileInput[0].files = dataTransfer.files;
            updateFileList();
        });
        
        // Update file list display
        function updateFileList() {
            const files = fileInput[0].files;
            fileList.empty();
            
            if (files.length > 0) {
                // Enable submit button
                submitBtn.prop('disabled', false);
                
                // Create file list
                const listGroup = $('<div class="list-group"></div>');
                
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    const fileSize = formatFileSize(file.size);
                    const fileType = file.type.split('/')[1].toUpperCase();
                    const fileIndex = i;
                    
                    const listItem = `
                        <div class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <i class="fas fa-file-pdf text-danger me-2"></i>
                                <span>${file.name}</span>
                            </div>
                            <div class="d-flex align-items-center">
                                <span class="badge bg-secondary me-2">${fileType}</span>
                                <span class="badge bg-info me-3">${fileSize}</span>
                                <button type="button" class="btn btn-sm btn-outline-danger remove-file" data-index="${fileIndex}">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                    `;
                    
                    listGroup.append(listItem);
                }
                
                fileList.append(listGroup);
                
                // Set up remove buttons
                $('.remove-file').on('click', function() {
                    const index = $(this).data('index');
                    removeFile(index);
                });
            } else {
                // Disable submit button if no files
                submitBtn.prop('disabled', true);
            }
        }
        
        // Remove a file from the list
        function removeFile(index) {
            // Create a new DataTransfer object
            const newDataTransfer = new DataTransfer();
            
            // Add all files except the one to remove
            for (let i = 0; i < dataTransfer.files.length; i++) {
                if (i !== index) {
                    newDataTransfer.items.add(dataTransfer.files[i]);
                }
            }
            
            // Update our dataTransfer object
            dataTransfer.items.clear();
            for (let i = 0; i < newDataTransfer.files.length; i++) {
                dataTransfer.items.add(newDataTransfer.files[i]);
            }
            
            // Update the file input
            fileInput[0].files = dataTransfer.files;
            
            // Update the display
            updateFileList();
        }
        
        // Format file size
        function formatFileSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB'];
            let unitIndex = 0;
            
            while (bytes >= 1024 && unitIndex < units.length - 1) {
                bytes /= 1024;
                unitIndex++;
            }
            
            return `${bytes.toFixed(1)} ${units[unitIndex]}`;
        }
    });
</script>
{% endblock %}
```
## File: app\templates\pubmed_search.html
```html
{% extends 'base.html' %}

{% block title %}PubMed Search - Clinical Research Analysis Tool{% endblock %}

{% block content %}
<div class="card shadow-lg">
    <div class="card-header bg-primary text-white">
        <h2 class="mb-0"><i class="fas fa-search me-2"></i>PubMed Clinical Trial Analysis</h2>
    </div>
    <div class="card-body">
        <p class="lead">Search PubMed for clinical trials and analyze them with AI.</p>
        
        <form method="POST" action="{{ url_for('main.pubmed_search') }}">
            {{ form.csrf_token }}
            
            <div class="row">
                <div class="col-md-8 mb-3">
                    <label class="form-label">{{ form.query.label }}</label>
                    {{ form.query(class="form-control", placeholder="e.g., loratadine, cancer, etc.") }}
                    <div class="form-text">
                        Enter a search term to find clinical trials in PubMed. The search will be filtered to clinical trials only.
                    </div>
                    {% if form.query.errors %}
                    <div class="invalid-feedback d-block">
                        {% for error in form.query.errors %}
                            {{ error }}
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
                
                <div class="col-md-4 mb-3">
                    <label class="form-label">{{ form.max_results.label }}</label>
                    {{ form.max_results(class="form-control", type="number") }}
                    <div class="form-text">
                        Maximum number of papers to retrieve and analyze (1-{{ config['MAX_PUBMED_RESULTS'] }})
                    </div>
                    {% if form.max_results.errors %}
                    <div class="invalid-feedback d-block">
                        {% for error in form.max_results.errors %}
                            {{ error }}
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-md-6">
                    <div class="alert alert-info">
                        <h5><i class="fas fa-info-circle me-2"></i>Search Tips</h5>
                        <ul>
                            <li>Use AND, OR, NOT for complex queries (e.g., asthma AND children)</li>
                            <li>Use quotation marks for exact phrases (e.g., "heart failure")</li>
                            <li>Add [MeSH] to use Medical Subject Headings (e.g., hypertension[MeSH])</li>
                            <li>Avoid too many search terms to get more relevant results</li>
                        </ul>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h5><i class="fas fa-flask me-2"></i>Using AI Analysis</h5>
                            <p>The analysis will extract key information such as:</p>
                            <ul>
                                <li>Study design and population</li>
                                <li>Interventions and dosing</li>
                                <li>Primary and secondary endpoints</li>
                                <li>Key results and conclusions</li>
                            </ul>
                            <p class="mb-0"><strong>Model:</strong> {{ session.get('model') or 'Not selected' }}</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="d-grid gap-2 col-lg-4 col-md-6 mx-auto mt-4">
                {{ form.submit(class="btn btn-primary btn-lg") }}
            </div>
        </form>
    </div>
</div>
{% endblock %}
```
## File: app\templates\results.html
```html
{% extends 'base.html' %}

{% block title %}Analysis Results{% endblock %}

{% block content %}
<div class="card shadow">
    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
        <h2 class="mb-0">
            <i class="fas fa-chart-bar me-2"></i>Analysis Results
        </h2>
        <div>
            <button id="downloadBtn" class="btn btn-light" disabled>
                <i class="fas fa-download me-1"></i> Download Excel
            </button>
            <button id="clearBtn" class="btn btn-outline-light ms-2">
                <i class="fas fa-trash me-1"></i> Clear Results
            </button>
        </div>
    </div>
    <div class="card-body">
        <div id="analysisProgress" class="mb-4">
            <h3>
                {% if analysis_type == 'pubmed' %}
                <i class="fas fa-search me-2"></i>Analyzing PubMed Results
                <small class="text-muted">Query: {{ query }}</small>
                {% else %}
                <i class="fas fa-file-pdf me-2"></i>Analyzing PDF Files
                {% endif %}
            </h3>
            
            <div class="progress mt-3" style="height: 25px;">
                <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
            </div>
            
            <div class="d-flex justify-content-between mt-2">
                <span id="progressText">Starting analysis...</span>
                <span id="progressCount">0/0</span>
            </div>
        </div>
        
        <div id="resultsContainer" class="mt-4" style="display: none;">
            <table id="resultsTable" class="table table-striped table-bordered" style="width:100%">
                <thead>
                    <tr>
                        <th><input type="checkbox" id="selectAll"></th>
                        <th>Title</th>
                        <th>PMID</th>
                        <th>Subject of Study</th>
                        <th>Disease State</th>
                        <th>Number of Subjects</th>
                        <th>Type of Study</th>
                        <th>Intervention</th>
                        <th>Results Available</th>
                        <th>Primary Endpoint Met</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Results will be populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Modal for detailed result view -->
<div class="modal fade" id="resultDetailModal" tabindex="-1" aria-labelledby="resultDetailModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-scrollable modal-xl">
        <div class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title" id="resultDetailModalLabel">Result Details</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body" id="resultDetailContent">
                <!-- Content will be populated by JavaScript -->
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<!-- Confirmation modal for clearing results -->
<div class="modal fade" id="clearConfirmModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-danger text-white">
                <h5 class="modal-title">
                    <i class="fas fa-exclamation-triangle me-2"></i>Confirm Clear
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <p>Are you sure you want to clear all results? This action cannot be undone.</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-danger" id="confirmClearBtn">Yes, Clear All</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    $(document).ready(function() {
        let resultsData = [];
        let dataTable;
        
        // Start the analysis process
        function startAnalysis() {
            $.ajax({
                url: '{{ url_for("main.start_analysis") }}',
                type: 'POST',
                success: function(response) {
                    checkStatus();
                },
                error: function(error) {
                    $('#progressText').text('Error: ' + error.responseJSON.message);
                    $('#progressBar').addClass('bg-danger');
                }
            });
        }
        
        // Check analysis status
        function checkStatus() {
            $.ajax({
                url: '{{ url_for("main.analysis_status") }}',
                type: 'GET',
                success: function(response) {
                    if (response.status === 'completed') {
                        $('#progressBar').css('width', '100%');
                        $('#progressBar').removeClass('progress-bar-animated');
                        $('#progressText').text('Analysis completed!');
                        $('#progressCount').text(response.count + '/' + response.count);
                        
                        // Enable download button
                        $('#downloadBtn').prop('disabled', false);
                        
                        // Load results
                        loadResults();
                    } else {
                        // Update progress 
                        $('#progressText').text('Processing...');
                        
                        // Check again in 2 seconds
                        setTimeout(checkStatus, 2000);
                    }
                },
                error: function() {
                    $('#progressText').text('Error checking status');
                    $('#progressBar').addClass('bg-danger');
                }
            });
        }
        
        // Load results data
        function loadResults() {
            $.ajax({
                url: '{{ url_for("main.get_results") }}',
                type: 'GET',
                success: function(data) {
                    resultsData = data;
                    populateResultsTable(data);
                    $('#resultsContainer').show();
                },
                error: function() {
                    $('#progressText').text('Error loading results');
                }
            });
        }
        
        // Populate results table
        function populateResultsTable(data) {
            if (dataTable) {
                dataTable.destroy();
            }
            
            let tableBody = $('#resultsTable tbody');
            tableBody.empty();
            
            data.forEach(function(item, index) {
                let row = `<tr>
                    <td><input type="checkbox" class="select-row" data-index="${index}"></td>
                    <td>${item.Title || ''}</td>
                    <td>${item.PMID || 'N/A'}</td>
                    <td>${item['Subject of Study'] || ''}</td>
                    <td>${item['Disease State'] || ''}</td>
                    <td>${item['Number of Subjects Studied'] || ''}</td>
                    <td>${item['Type of Study'] || ''}</td>
                    <td>${item.Intervention || ''}</td>
                    <td>${item['Results Available'] || ''}</td>
                    <td>${item['Primary Endpoint Met'] || ''}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-details" data-index="${index}">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>`;
                tableBody.append(row);
            });
            
            // Initialize DataTable
            dataTable = $('#resultsTable').DataTable({
                responsive: true,
                dom: 'Bfrtip',
                buttons: [
                    'copy', 'csv', 'excel'
                ]
            });
            
            // Setup event handlers for the view details buttons
            $('.view-details').on('click', function() {
                let index = $(this).data('index');
                showResultDetails(resultsData[index]);
            });
        }
        
        // Show result details in modal
        function showResultDetails(result) {
            let content = '<div class="table-responsive"><table class="table table-bordered">';
            
            for (let key in result) {
                if (result.hasOwnProperty(key)) {
                    content += `<tr>
                        <th style="width: 30%">${key}</th>
                        <td>${result[key] || ''}</td>
                    </tr>`;
                }
            }
            
            content += '</table></div>';
            $('#resultDetailContent').html(content);
            
            // Show the modal
            new bootstrap.Modal(document.getElementById('resultDetailModal')).show();
        }
        
        // Handle download button
        $('#downloadBtn').on('click', function() {
            window.location.href = '{{ url_for("main.download_excel") }}';
        });
        
        // Handle clear button
        $('#clearBtn').on('click', function() {
            new bootstrap.Modal(document.getElementById('clearConfirmModal')).show();
        });
        
        // Handle confirm clear
        $('#confirmClearBtn').on('click', function() {
            $.ajax({
                url: '{{ url_for("main.clear_results") }}',
                type: 'POST',
                success: function() {
                    window.location.href = '{{ url_for("main.index") }}';
                }
            });
        });
        
        // Handle select all checkbox
        $('#selectAll').on('change', function() {
            $('.select-row').prop('checked', $(this).prop('checked'));
        });
        
        // Start the analysis automatically when page loads
        startAnalysis();
    });
</script>
{% endblock %}
```
## File: app\templates\settings.html
```html
{% extends 'base.html' %}

{% block title %}API Settings - Clinical Research Analysis Tool{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card shadow-lg">
            <div class="card-header bg-primary text-white">
                <h2 class="mb-0"><i class="fas fa-key me-2"></i>API Settings</h2>
            </div>
            <div class="card-body">
                <p class="lead">Configure your API credentials to use with the analysis tools.</p>
                
                {% if session.get('api_key_valid') %}
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>{{ session.get('api_provider')|capitalize }} API is configured and validated!</strong>
                </div>
                {% else %}
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Please configure your API settings to use the analysis tools
                </div>
                {% endif %}
                
                <form method="POST" action="{{ url_for('main.settings') }}">
                    {{ form.csrf_token }}
                    
                    <div class="mb-3">
                        <label class="form-label">{{ form.api_provider.label }}</label>
                        {{ form.api_provider(class="form-select") }}
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">{{ form.api_key.label }}</label>
                        {{ form.api_key(class="form-control", placeholder="Enter your API key") }}
                        <div class="form-text">
                            Your API key is stored securely in your session and is not persisted on the server.
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">{{ form.model.label }}</label>
                        {{ form.model(class="form-select") }}
                    </div>
                    
                    <div class="d-grid gap-2">
                        {{ form.submit(class="btn btn-primary") }}
                    </div>
                </form>
                
                <div class="mt-4">
                    <h4>API Information</h4>
                    <div class="accordion" id="apiInfoAccordion">
                        <div class="accordion-item">
                            <h2 class="accordion-header" id="openaiHeading">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#openaiInfo" aria-expanded="false" aria-controls="openaiInfo">
                                    OpenAI API
                                </button>
                            </h2>
                            <div id="openaiInfo" class="accordion-collapse collapse" aria-labelledby="openaiHeading" data-bs-parent="#apiInfoAccordion">
                                <div class="accordion-body">
                                    <p>To use OpenAI models, you need an API key from OpenAI.</p>
                                    <p>You can get an API key by signing up at <a href="https://platform.openai.com/signup" target="_blank">platform.openai.com</a>.</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header" id="anthropicHeading">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#anthropicInfo" aria-expanded="false" aria-controls="anthropicInfo">
                                    Anthropic API
                                </button>
                            </h2>
                            <div id="anthropicInfo" class="accordion-collapse collapse" aria-labelledby="anthropicHeading" data-bs-parent="#apiInfoAccordion">
                                <div class="accordion-body">
                                    <p>To use Claude models, you need an API key from Anthropic.</p>
                                    <p>You can get an API key by signing up at <a href="https://console.anthropic.com/" target="_blank">console.anthropic.com</a>.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    $(document).ready(function() {
        // Update model options when provider changes
        $('#api_provider').change(function() {
            let provider = $(this).val();
            let modelSelect = $('#model');
            
            // Clear current options
            modelSelect.empty();
            
            if (provider === 'openai') {
                // Add OpenAI models
                modelSelect.append(new Option('GPT-4o', 'gpt-4o'));
                modelSelect.append(new Option('GPT-4 Turbo', 'gpt-4-turbo'));
                modelSelect.append(new Option('GPT-3.5 Turbo', 'gpt-3.5-turbo'));
                
                // Set default
                modelSelect.val('gpt-4o');
            } else {
                // Add Claude models
                modelSelect.append(new Option('Claude 3 Opus', 'claude-3-opus-20240229'));
                modelSelect.append(new Option('Claude 3 Sonnet', 'claude-3-sonnet-20240229'));
                modelSelect.append(new Option('Claude 3 Haiku', 'claude-3-haiku-20240307'));
                
                // Set default
                modelSelect.val('claude-3-sonnet-20240229');
            }
        });
    });
</script>
{% endblock %}
```
## File: app\utils\api_utils.py
```python
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
```
## File: app\utils\claude_utils.py
```python
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
```
## File: app\utils\openai_utils.py
```python
# openai calls and prompting
import json
import re
import openai
from typing import Dict, Any, Optional
import logging
from app.utils.prompts import get_base_analysis_prompt, get_pdf_prompt_addition, get_openai_specific_instructions

logger = logging.getLogger(__name__)

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
    Analyze a paper using OpenAI
    
    Args:
        client: OpenAI client
        paper_content: Content to analyze
        is_pdf: Whether the content is from a PDF
        model: OpenAI model to use
        
    Returns:
        Analyzed paper data as dictionary
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
        logger.error(f"Error analyzing paper with OpenAI: {e}")
        return {
            "Title": "Error analyzing document",
            "Error": str(e)
        }
```
## File: app\utils\pdf_utils.py
```python
import io
import PyPDF2
import pdf2image
import pytesseract
from PIL import Image
from typing import Tuple, List, Dict, Any, BinaryIO, Union
import logging
import os

logger = logging.getLogger(__name__)

def convert_pdf_to_txt_file(pdf_file: Union[BinaryIO, str]) -> Tuple[str, int]:
    """
    Convert PDF to a single text file
    
    Args:
        pdf_file: PDF file object or path to file
        
    Returns:
        Tuple of (extracted_text, page_count)
    """
    try:
        # If pdf_file is a string (filepath), open it
        if isinstance(pdf_file, str):
            with open(pdf_file, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n\n"
                return text, len(pdf_reader.pages)
        else:
            # Otherwise, assume it's already a file-like object
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"
            return text, len(pdf_reader.pages)
    except Exception as e:
        logger.error(f"Error converting PDF to text: {e}")
        raise

def images_to_txt(pdf_file: Union[bytes, str], lang: str = 'eng') -> Tuple[List[str], int]:
    """
    Convert PDF to text using OCR
    
    Args:
        pdf_file: PDF file as bytes or path to file
        lang: Language code for OCR
        
    Returns:
        Tuple of (list_of_page_texts, page_count)
    """
    try:
        # If pdf_file is a string (filepath), read it
        if isinstance(pdf_file, str):
            with open(pdf_file, 'rb') as f:
                pdf_content = f.read()
                images = pdf2image.convert_from_bytes(pdf_content)
        else:
            # Otherwise, assume it's already bytes
            images = pdf2image.convert_from_bytes(pdf_file)
            
        texts = []
        for image in images:
            text = pytesseract.image_to_string(image, lang=lang)
            texts.append(text)
        return texts, len(images)
    except Exception as e:
        logger.error(f"Error performing OCR on PDF: {e}")
        raise

def process_file(file: Any, use_ocr: bool = False, language: str = 'eng') -> Dict[str, Any]:
    """
    Process a file (PDF or image) and extract text
    
    Args:
        file: File object or path to file
        use_ocr: Whether to use OCR
        language: Language code for OCR
        
    Returns:
        Dictionary with filename and extracted content
    """
    try:
        # Handle different file input types
        if isinstance(file, dict) and 'path' in file and 'name' in file:
            # This is a dict with path and name
            filepath = file['path']
            filename = file['name']
            file_extension = filename.split(".")[-1].lower()
            
            if file_extension == "pdf":
                if use_ocr:
                    texts, page_count = images_to_txt(filepath, language)
                    text_content = "\n\n".join(texts)
                else:
                    text_content, page_count = convert_pdf_to_txt_file(filepath)
            elif file_extension in ["png", "jpg", "jpeg"]:
                # For image files, we need to open them first
                with open(filepath, 'rb') as f:
                    pil_image = Image.open(f)
                    text_content = pytesseract.image_to_string(pil_image, lang=language)
                    page_count = 1
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
            return {
                'filename': filename,
                'content': text_content,
                'page_count': page_count
            }
            
        elif hasattr(file, 'read') and hasattr(file, 'name'):
            # This is a file-like object
            filename = os.path.basename(file.name)
            file_extension = filename.split(".")[-1].lower()
            
            # Store the file content so we don't lose it after reading
            file_content = file.read()
            
            if file_extension == "pdf":
                if use_ocr:
                    texts, page_count = images_to_txt(file_content, language)
                    text_content = "\n\n".join(texts)
                else:
                    # Create a new file-like object from the content
                    pdf_file = io.BytesIO(file_content)
                    text_content, page_count = convert_pdf_to_txt_file(pdf_file)
            elif file_extension in ["png", "jpg", "jpeg"]:
                pil_image = Image.open(io.BytesIO(file_content))
                text_content = pytesseract.image_to_string(pil_image, lang=language)
                page_count = 1
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
            return {
                'filename': filename,
                'content': text_content,
                'page_count': page_count
            }
            
        else:
            raise ValueError(f"Unsupported file object type: {type(file)}")
            
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise
```
## File: app\utils\prompts.py
```python
"""
Prompts for AI models used in the application
"""

def get_base_analysis_prompt() -> str:
    """
    Get the base system prompt for paper analysis that is common to all models.
    
    Returns:
        Base system prompt string
    """
    return """
    You are a bot speaking with another program that takes JSON formatted text as an input. Only return results in JSON format, with NO PREAMBLE.
    The user will input the results from a PubMed search or a full-text clinical trial PDF. Your job is to extract the exact information to return:
      'Title': The complete article title
      'PMID': The Pubmed ID of the article (if available, otherwise 'NA')
      'Full Text Link' : If available, the DOI URL, otherwise, NA
      'Subject of Study': The type of subject in the study. Human, Animal, In-Vitro, Other
      'Disease State': Disease state studied, if any, or if the study is done on a healthy population. leave blank if disease state or healthy patients is not mentioned explicitly. "Healthy patients" if patients are explicitly mentioned to be healthy.
      'Number of Subjects Studied': If human, the total study population. Otherwise, leave blank. This field needs to be an integer or empty.
      'Type of Study': Type of study done. 'RCT' for randomized controlled trial, '1. Meta-analysis','2. Systematic Review','3. Cohort Study', or '4. Other'. If it is '5. Other', append a short description
      'Study Design': Brief and succinct details about study design, if applicable
      'Intervention': Intervention(s) studied, if any. Intervention is the treatment applied to the group.
      'Intervention Dose': Go in detail here about the intervention's doses and treatment duration if available.
      'Intervention Dosage Form': A brief description of the dosage form - ie. oral, topical, intranasal, if available.
      'Control': Control or comarators, if any
      'Primary Endpoint': What the primary endpoint of the study was, if available. Include how it was measured too if available.
      'Primary Endpoint Result': The measurement for the primary endpoints
      'Secondary Endpoints' If available
      'Safety Endpoints' If available
      'Results Available': Yes or No
      'Primary Endpoint Met': Summarize from results whether or not the primary endpoint(s) was met: Yes or No or NA if results unavailable
      'Statistical Significance': alpha-level and p-value for primary endpoint(s), if available
      'Clinical Significance': Effect size, and Number needed to treat (NNT)/Number needed to harm (NNH), if available
      'Conclusion': Brief summary of the conclusions of the paper
      'Main Author': Last name, First initials
      'Other Authors': Last name, First initials; Last name First initials; ...
      'Journal Name': Full journal name
      'Date of Publication': YYYY-MM-DD
      'Error': Error description, if any. Otherwise, leave emtpy

    IMPORTANT: Your output MUST be a valid JSON object. Do not include any explanations, comments, or markdown formatting. Only return a JSON object with the fields described above.
    """

def get_pdf_prompt_addition() -> str:

    # PDF-specific prompt addition

    return """
    Note: This is a full-text PDF of a clinical trial. Extract as much detail as possible from the full text.
    """

def get_openai_specific_instructions() -> str:
    
    # Returns OpenAI-specific instructions
    
    return """
    Format your response as a valid JSON object without any explanations or text outside the JSON structure.
    """

def get_claude_specific_instructions() -> str:

    # Returns Claude-specific instructions
    
    return """
    You must format your output as a valid JSON object. Do not include any text outside the JSON structure.
    Do not wrap the JSON in markdown code blocks - just return the raw JSON object.
    """
```
## File: app\utils\pubmed_utils.py
```python
from Bio import Entrez
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def configure_entrez(email: Optional[str] = None, api_key: Optional[str] = None) -> None:
    """Configure Entrez with email and API key"""
    if email:
        Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

def search_and_fetch_pubmed(query: str, max_results: int) -> Dict[str, Any]:
    """
    Search PubMed and fetch details in one function.
    
    Args:
        query: PubMed search query
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing PubMed article records
    """
    try:
        with Entrez.esearch(db="pubmed", term=query, retmax=max_results) as handle:
            record = Entrez.read(handle)

        id_list = record["IdList"]
        if not id_list:
            return {"PubmedArticle": []}

        ids = ','.join(id_list)
        with Entrez.efetch(db="pubmed", id=ids, retmode="xml") as handle:
            records = Entrez.read(handle)

        return records
    except Exception as e:
        logger.error(f"Error searching PubMed: {e}")
        raise
```
## File: app\utils\__init__.py
```python

```
## File: app\static\css\style.css
```css
/* Custom styles for Clinical Research Analysis Tool */

/* Global styles */
body {
    background-color: #f8f9fa;
    color: #343a40;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Card styling */
.card {
    border-radius: 0.5rem;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    margin-bottom: 1.5rem;
}

.card-header {
    border-top-left-radius: 0.5rem !important;
    border-top-right-radius: 0.5rem !important;
    font-weight: 500;
}

/* Button styling */
.btn {
    border-radius: 0.25rem;
    padding: 0.375rem 0.75rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

.btn-primary {
    background-color: #0d6efd;
    border-color: #0d6efd;
}

.btn-primary:hover {
    background-color: #0b5ed7;
    border-color: #0a58ca;
}

/* Navbar customization */
.navbar {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar-brand {
    font-weight: 600;
    font-size: 1.25rem;
}

/* Form elements */
.form-control, .form-select {
    border-radius: 0.25rem;
    padding: 0.5rem 0.75rem;
    border: 1px solid #ced4da;
    transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control:focus, .form-select:focus {
    border-color: #86b7fe;
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

/* File upload styling */
.custom-file-upload {
    border: 1px dashed #ced4da;
    border-radius: 0.25rem;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    background-color: #f8f9fa;
    transition: all 0.2s ease;
}

.custom-file-upload:hover {
    background-color: #e9ecef;
    border-color: #6c757d;
}

/* Results table customization */
.dataTables_wrapper {
    padding: 1rem 0;
}

/* Animation */
.fade-in {
    animation: fadeIn 0.5s;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Footer styling */
footer {
    background-color: #f8f9fa;
    padding: 1rem 0;
    border-top: 1px solid #e9ecef;
    margin-top: 2rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .card-body {
        padding: 1rem;
    }
}
```
## File: app\static\css\js\main.js
```javascript
// Common JavaScript functions for the application

document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips everywhere
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Add animation when scrolling into view
    function animateOnScroll() {
        const elements = document.querySelectorAll('.animate-on-scroll');
        
        elements.forEach(element => {
            const position = element.getBoundingClientRect();
            
            // Check if element is in viewport
            if(position.top < window.innerHeight && position.bottom >= 0) {
                element.classList.add('animate__animated', element.dataset.animation || 'animate__fadeIn');
            }
        });
    }
    
    // Listen for scroll events
    window.addEventListener('scroll', animateOnScroll);
    
    // Initial check for animations
    animateOnScroll();
    
    // Handle API provider selection
    const apiProviderSelect = document.getElementById('api_provider');
    if (apiProviderSelect) {
        apiProviderSelect.addEventListener('change', function() {
            // This is now handled in the page-specific script in settings.html
        });
    }
    
    // Handle form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Format date as YYYY-MM-DD
function formatDate(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

// Format number with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Create and show toast notification
        const toastEl = document.createElement('div');
        toastEl.className = 'toast position-fixed bottom-0 end-0 m-3';
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="toast-header bg-success text-white">
                <i class="fas fa-check-circle me-2"></i>
                <strong class="me-auto">Success</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                Text copied to clipboard
            </div>
        `;
        
        document.body.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        // Remove toast after it's hidden
        toastEl.addEventListener('hidden.bs.toast', function() {
            document.body.removeChild(toastEl);
        });
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
    });
}
```
