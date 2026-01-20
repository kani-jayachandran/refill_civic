"""
Data extraction module for CivicExtract
Handles OCR and PDF text/table extraction
"""

import pytesseract
import pdfplumber
import cv2
import numpy as np
from PIL import Image
import pandas as pd
import io
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExtractor:
    """Main class for extracting data from PDFs and images"""
    
    def __init__(self):
        # Configure tesseract path if needed (Windows users may need to set this)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass
    
    def extract_from_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract data from uploaded file based on file type
        
        Args:
            file_content: Raw file bytes
            filename: Original filename with extension
            
        Returns:
            Dictionary containing extracted text, tables, and metadata
        """
        try:
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                return self._extract_from_pdf(file_content)
            elif file_extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
                return self._extract_from_image(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"Error extracting from file {filename}: {str(e)}")
            raise
    
    def _extract_from_pdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extract text and tables from PDF"""
        result = {
            'text': '',
            'tables': [],
            'metadata': {'pages': 0, 'extraction_method': 'pdf'}
        }
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                result['metadata']['pages'] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        result['text'] += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    
                    # Extract tables
                    tables = page.extract_tables()
                    for table_num, table in enumerate(tables):
                        if table and len(table) > 1:  # Ensure table has header and data
                            table_data = {
                                'page': page_num + 1,
                                'table_number': table_num + 1,
                                'data': table,
                                'rows': len(table),
                                'columns': len(table[0]) if table else 0
                            }
                            result['tables'].append(table_data)
                            
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            # Fallback to OCR if PDF extraction fails
            return self._extract_from_image(pdf_content, is_pdf_fallback=True)
            
        return result
    
    def _extract_from_image(self, image_content: bytes, is_pdf_fallback: bool = False) -> Dict[str, Any]:
        """Extract text from image using OCR"""
        result = {
            'text': '',
            'tables': [],
            'metadata': {'extraction_method': 'ocr', 'is_pdf_fallback': is_pdf_fallback}
        }
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_content))
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Extract text using OCR
            ocr_text = pytesseract.image_to_string(processed_image, config='--psm 6')
            result['text'] = ocr_text
            
            # Try to detect table structure in OCR text
            potential_tables = self._detect_tables_in_text(ocr_text)
            result['tables'] = potential_tables
            
        except Exception as e:
            logger.error(f"OCR extraction error: {str(e)}")
            raise
            
        return result
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            # Convert PIL to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply threshold to get better contrast
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL
            processed_image = Image.fromarray(thresh)
            
            return processed_image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}, using original image")
            return image
    
    def _detect_tables_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Attempt to detect tabular data in extracted text"""
        tables = []
        
        try:
            lines = text.strip().split('\n')
            potential_table_lines = []
            
            for line in lines:
                # Look for lines that might be table rows (contain multiple separators)
                separators = ['\t', '  ', '|', ',']
                separator_count = sum(line.count(sep) for sep in separators)
                
                if separator_count >= 2 and len(line.strip()) > 10:
                    potential_table_lines.append(line.strip())
            
            if len(potential_table_lines) >= 2:  # At least header + one data row
                # Try to parse as table
                table_data = []
                for line in potential_table_lines[:10]:  # Limit to first 10 rows
                    # Split by most common separator
                    for sep in ['\t', '|', ',']:
                        if sep in line:
                            row = [cell.strip() for cell in line.split(sep)]
                            if len(row) >= 2:
                                table_data.append(row)
                                break
                
                if table_data:
                    tables.append({
                        'page': 1,
                        'table_number': 1,
                        'data': table_data,
                        'rows': len(table_data),
                        'columns': len(table_data[0]) if table_data else 0,
                        'source': 'ocr_detection'
                    })
                    
        except Exception as e:
            logger.warning(f"Table detection in text failed: {str(e)}")
            
        return tables