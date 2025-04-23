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