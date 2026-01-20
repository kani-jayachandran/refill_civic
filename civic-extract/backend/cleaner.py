"""
Data cleaning and normalization module for CivicExtract
Handles data cleaning, validation, and structuring
"""

import pandas as pd
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCleaner:
    """Class for cleaning and structuring extracted data"""
    
    def __init__(self):
        self.common_headers = [
            'name', 'date', 'amount', 'description', 'type', 'category',
            'address', 'phone', 'email', 'id', 'number', 'status'
        ]
    
    def clean_and_structure_data(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and structure the extracted data into pandas DataFrames
        
        Args:
            extraction_result: Result from DataExtractor
            
        Returns:
            Dictionary containing cleaned DataFrames and metadata
        """
        try:
            result = {
                'dataframes': [],
                'text_summary': '',
                'metadata': extraction_result.get('metadata', {}),
                'success': True,
                'errors': []
            }
            
            # Process tables if available
            if extraction_result.get('tables'):
                for table_info in extraction_result['tables']:
                    try:
                        df = self._clean_table_data(table_info['data'])
                        if df is not None and not df.empty:
                            df_info = {
                                'dataframe': df,
                                'source_page': table_info.get('page', 1),
                                'table_number': table_info.get('table_number', 1),
                                'rows': len(df),
                                'columns': len(df.columns),
                                'column_names': df.columns.tolist()
                            }
                            result['dataframes'].append(df_info)
                    except Exception as e:
                        error_msg = f"Error processing table {table_info.get('table_number', 'unknown')}: {str(e)}"
                        logger.warning(error_msg)
                        result['errors'].append(error_msg)
            
            # Process text if no tables found or as fallback
            if not result['dataframes'] and extraction_result.get('text'):
                try:
                    text_df = self._extract_structured_data_from_text(extraction_result['text'])
                    if text_df is not None and not text_df.empty:
                        df_info = {
                            'dataframe': text_df,
                            'source_page': 1,
                            'table_number': 1,
                            'rows': len(text_df),
                            'columns': len(text_df.columns),
                            'column_names': text_df.columns.tolist(),
                            'source': 'text_extraction'
                        }
                        result['dataframes'].append(df_info)
                except Exception as e:
                    error_msg = f"Error processing text data: {str(e)}"
                    logger.warning(error_msg)
                    result['errors'].append(error_msg)
            
            # Create text summary
            result['text_summary'] = self._create_text_summary(extraction_result.get('text', ''))
            
            # If no structured data found, create a simple text dataframe
            if not result['dataframes']:
                text_lines = extraction_result.get('text', '').strip().split('\n')
                if text_lines and text_lines[0]:
                    simple_df = pd.DataFrame({
                        'line_number': range(1, len(text_lines) + 1),
                        'content': text_lines
                    })
                    df_info = {
                        'dataframe': simple_df,
                        'source_page': 1,
                        'table_number': 1,
                        'rows': len(simple_df),
                        'columns': len(simple_df.columns),
                        'column_names': simple_df.columns.tolist(),
                        'source': 'text_lines'
                    }
                    result['dataframes'].append(df_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in clean_and_structure_data: {str(e)}")
            return {
                'dataframes': [],
                'text_summary': '',
                'metadata': {},
                'success': False,
                'errors': [str(e)]
            }
    
    def _clean_table_data(self, table_data: List[List[str]]) -> Optional[pd.DataFrame]:
        """Clean and convert table data to DataFrame"""
        try:
            if not table_data or len(table_data) < 2:
                return None
            
            # Clean the data
            cleaned_data = []
            for row in table_data:
                cleaned_row = [self._clean_cell_value(cell) for cell in row]
                # Skip completely empty rows
                if any(cell.strip() for cell in cleaned_row):
                    cleaned_data.append(cleaned_row)
            
            if len(cleaned_data) < 2:
                return None
            
            # Use first row as headers
            headers = cleaned_data[0]
            data_rows = cleaned_data[1:]
            
            # Clean headers
            clean_headers = [self._clean_column_name(header) for header in headers]
            
            # Ensure all rows have the same number of columns
            max_cols = len(clean_headers)
            normalized_rows = []
            for row in data_rows:
                # Pad or truncate row to match header length
                if len(row) < max_cols:
                    row.extend([''] * (max_cols - len(row)))
                elif len(row) > max_cols:
                    row = row[:max_cols]
                normalized_rows.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(normalized_rows, columns=clean_headers)
            
            # Clean data types
            df = self._infer_and_convert_data_types(df)
            
            # Remove completely empty rows and columns
            df = df.dropna(how='all').loc[:, df.notna().any()]
            
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning table data: {str(e)}")
            return None
    
    def _clean_cell_value(self, value: Any) -> str:
        """Clean individual cell value"""
        if value is None:
            return ''
        
        # Convert to string and clean
        str_value = str(value).strip()
        
        # Remove extra whitespace
        str_value = re.sub(r'\s+', ' ', str_value)
        
        # Remove common OCR artifacts
        str_value = re.sub(r'[^\w\s\-.,()/$%@#]', '', str_value)
        
        return str_value
    
    def _clean_column_name(self, name: str) -> str:
        """Clean column name"""
        if not name or not name.strip():
            return 'unnamed_column'
        
        # Clean the name
        clean_name = str(name).strip().lower()
        
        # Replace spaces and special characters with underscores
        clean_name = re.sub(r'[^\w]', '_', clean_name)
        
        # Remove multiple underscores
        clean_name = re.sub(r'_+', '_', clean_name)
        
        # Remove leading/trailing underscores
        clean_name = clean_name.strip('_')
        
        # Ensure it's not empty
        if not clean_name:
            clean_name = 'unnamed_column'
        
        return clean_name
    
    def _infer_and_convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Infer and convert appropriate data types"""
        try:
            for column in df.columns:
                # Skip if column is already numeric
                if df[column].dtype in ['int64', 'float64']:
                    continue
                
                # Try to convert to numeric
                numeric_series = pd.to_numeric(df[column], errors='coerce')
                if numeric_series.notna().sum() > len(df) * 0.7:  # If 70% can be converted
                    df[column] = numeric_series
                    continue
                
                # Try to convert to datetime
                try:
                    datetime_series = pd.to_datetime(df[column], errors='coerce', infer_datetime_format=True)
                    if datetime_series.notna().sum() > len(df) * 0.7:  # If 70% can be converted
                        df[column] = datetime_series
                        continue
                except:
                    pass
                
                # Keep as string but clean
                df[column] = df[column].astype(str).str.strip()
            
            return df
            
        except Exception as e:
            logger.warning(f"Error inferring data types: {str(e)}")
            return df
    
    def _extract_structured_data_from_text(self, text: str) -> Optional[pd.DataFrame]:
        """Try to extract structured data from plain text"""
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if len(lines) < 2:
                return None
            
            # Look for patterns that suggest structured data
            structured_lines = []
            
            for line in lines:
                # Look for lines with multiple separators (potential table rows)
                if any(sep in line for sep in ['\t', '|', ',']) and len(line.split()) >= 2:
                    structured_lines.append(line)
            
            if len(structured_lines) >= 2:
                # Try to parse as CSV-like data
                data_rows = []
                for line in structured_lines:
                    # Try different separators
                    for sep in ['\t', '|', ',', ';']:
                        if sep in line:
                            row = [cell.strip() for cell in line.split(sep)]
                            if len(row) >= 2:
                                data_rows.append(row)
                                break
                
                if data_rows and len(data_rows) >= 2:
                    # Use first row as headers
                    headers = [self._clean_column_name(h) for h in data_rows[0]]
                    data = data_rows[1:]
                    
                    # Normalize row lengths
                    max_cols = len(headers)
                    normalized_data = []
                    for row in data:
                        if len(row) < max_cols:
                            row.extend([''] * (max_cols - len(row)))
                        elif len(row) > max_cols:
                            row = row[:max_cols]
                        normalized_data.append(row)
                    
                    df = pd.DataFrame(normalized_data, columns=headers)
                    return self._infer_and_convert_data_types(df)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting structured data from text: {str(e)}")
            return None
    
    def _create_text_summary(self, text: str) -> str:
        """Create a summary of the extracted text"""
        try:
            if not text or not text.strip():
                return "No text content extracted."
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            summary = f"Extracted {len(lines)} lines of text. "
            
            if lines:
                # Get first few non-empty lines as preview
                preview_lines = lines[:3]
                summary += f"Preview: {' | '.join(preview_lines[:50])}..."
            
            return summary
            
        except Exception as e:
            logger.warning(f"Error creating text summary: {str(e)}")
            return "Text summary unavailable."
    
    def dataframe_to_dict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Convert DataFrame to JSON-serializable dictionary"""
        try:
            # Replace NaN values with None for JSON serialization
            df_clean = df.replace({np.nan: None})
            
            return {
                'columns': df_clean.columns.tolist(),
                'data': df_clean.values.tolist(),
                'index': df_clean.index.tolist(),
                'shape': df_clean.shape
            }
            
        except Exception as e:
            logger.error(f"Error converting DataFrame to dict: {str(e)}")
            return {'columns': [], 'data': [], 'index': [], 'shape': [0, 0]}