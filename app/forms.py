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
