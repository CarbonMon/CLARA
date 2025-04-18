# CLARA
Clinical Literature Analysis Research Assistant - AI-based clinical research built in Flask
# Clinical Research Analysis Tool

![Clinical Research Analysis Tool](https://via.placeholder.com/1200x300/0d6efd/ffffff?text=Clinical+Research+Analysis+Tool)

## Overview

CLARA is a powerful Flask web application designed to help researchers, clinicians, and healthcare professionals analyze clinical trial data from multiple sources using state-of-the-art AI models. This tool automates the extraction of key data points from PubMed clinical trials and PDF documents, saving valuable time and improving research efficiency.

## Features

### Core Functionality

- **PubMed Clinical Trial Analysis**: Search and analyze PubMed clinical trials with customizable search parameters
- **PDF Document Analysis**: Upload and process clinical trial PDFs, including support for OCR on scanned documents
- **AI-Powered Extraction**: Leverages OpenAI (GPT-4/3.5) and Anthropic (Claude) models to extract structured data
- **Comprehensive Data Extraction**: Extracts key clinical trial information including:
  - Study design and population
  - Intervention details and dosing
  - Primary and secondary endpoints
  - Statistical and clinical significance
  - Results and conclusions
  - Publication details

### User Interface

- **Modern, Responsive Design**: Built with Bootstrap 5 for a professional look and feel across devices
- **Interactive Results Table**: Sortable, searchable tables with DataTables integration
- **Detailed Result Views**: Modal dialogs for in-depth examination of extracted data
- **Progress Tracking**: Real-time progress indicators during analysis
- **Excel Export**: One-click export of selected or all results to Excel

### Technical Features

- **API Integration**: Seamless integration with OpenAI and Anthropic APIs
- **OCR Capabilities**: Multilingual OCR for processing scanned documents
- **Session Management**: Persistent state management across user sessions
- **Secure File Handling**: Safe processing of uploaded documents

## Installation

### Prerequisites

- Python 3.8 or higher
- Pip package manager
- Tesseract OCR (for PDF OCR functionality)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/clinical-research-analysis-tool.git
   cd clinical-research-analysis-tool
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Tesseract OCR:
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
   - **macOS**: `brew install tesseract`
   - **Windows**: Download and install from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

5. Set environment variables (optional but recommended):

    **For Unix/Linux/macOS:**
    ```bash
    export SECRET_KEY="your-secret-key"
    export NCBI_EMAIL="your-email@example.com"
    export NCBI_API_KEY="your-ncbi-api-key"
    ```
  
    **For Windows:**
    ```cmd
    set SECRET_KEY=your-secret-key
    set NCBI_EMAIL=your-email@example.com
    set NCBI_API_KEY=your-ncbi-api-key
    ```
  
    **For GitHub Codespaces:**
    
    1. Go to your GitHub repository
    2. Click on "Settings" > "Secrets and variables" > "Codespaces"
    3. Click "New repository secret" for each variable:
       - Name: `SECRET_KEY`, Value: your-secret-key
       - Name: `NCBI_EMAIL`, Value: your-email@example.com
       - Name: `NCBI_API_KEY`, Value: your-ncbi-api-key
  
    **Alternatively, you can add these to your `.devcontainer/devcontainer.json` file:**
    ```json
    {
      "name": "Your Dev Container",
      "remoteEnv": {
        "SECRET_KEY": "your-secret-key",
        "NCBI_EMAIL": "your-email@example.com",
        "NCBI_API_KEY": "your-ncbi-api-key"
      }
    }
    ```

Note: For sensitive values, using GitHub Secrets is more secure than hardcoding them in your devcontainer.json file.


### Running the Application

Run the application locally:
```bash
python run.py
```

The application will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Usage Guide

### Setting Up API Access

1. Navigate to the **Settings** page
2. Select either **OpenAI** or **Anthropic** as your API provider
3. Enter your API key
4. Select your preferred model
5. Click **Save Settings**

### PubMed Analysis

1. Navigate to the **PubMed Search** page
2. Enter your search query
3. Specify the maximum number of results to analyze
4. Click **Start Analysis**
5. View the results table once analysis is complete
6. Click **Download Excel** to export results

### PDF Analysis

1. Navigate to the **PDF Upload** page
2. Toggle **Enable OCR** if analyzing scanned documents
3. Select the document language if using OCR
4. Upload one or more PDF files
5. Click **Process and Analyze**
6. View the results table once analysis is complete
7. Click **Download Excel** to export results

### Working with Results

- Click on the eye icon to view detailed information for a specific result
- Use the search function to filter results
- Sort by any column by clicking the column header
- Select individual rows or use the "Select All" checkbox
- Clear all results using the "Clear Results" button

## Configuration

The application can be configured through environment variables or by modifying `app/config.py`.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for session security | dev-key-for-development-only |
| `NCBI_EMAIL` | Email for NCBI API access | None |
| `NCBI_API_KEY` | API key for NCBI API access | None |

### API Models

The application supports the following models:

**OpenAI**
- GPT-4o
- GPT-4 Turbo
- GPT-3.5 Turbo

**Anthropic**
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku

## Deployment

### Deploying with Gunicorn (Linux/macOS)

For production environments, we recommend using Gunicorn:

```bash
gunicorn 'app:create_app()' --workers 4 --bind 0.0.0.0:8000
```

### Docker Deployment

A Dockerfile is included for containerized deployment:

```bash
# Build the Docker image
docker build -t clinical-research-tool .

# Run the container
docker run -p 8000:8000 -e SECRET_KEY=your-secret-key clinical-research-tool
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- This application uses the [OpenAI API](https://openai.com/api/) and [Anthropic API](https://www.anthropic.com/)
- PubMed data access is provided through [Biopython](https://biopython.org/)
- PDF processing utilizes [PyPDF2](https://pypdf2.readthedocs.io/) and [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

---

## Screenshots

### Home Page
![Home Page](https://via.placeholder.com/800x450/0d6efd/ffffff?text=Home+Page)

### PubMed Search
![PubMed Search](https://via.placeholder.com/800x450/0d6efd/ffffff?text=PubMed+Search)

### PDF Upload
![PDF Upload](https://via.placeholder.com/800x450/0d6efd/ffffff?text=PDF+Upload)

### Results Page
![Results Page](https://via.placeholder.com/800x450/0d6efd/ffffff?text=Results+Page)

### Detailed View
![Detailed View](https://via.placeholder.com/800x450/0d6efd/ffffff?text=Detailed+View)

---

Created with ❤️ for medical researchers and healthcare professionals.
