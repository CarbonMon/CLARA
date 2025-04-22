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
