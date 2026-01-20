"""
CivicExtract - AI Platform for Public Data Extraction & Structuring
FastAPI backend server
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
import json
import os
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, List
import uuid

from extractor import DataExtractor
from cleaner import DataCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CivicExtract API",
    description="AI Platform for Public Data Extraction & Structuring",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
extractor = DataExtractor()
cleaner = DataCleaner()

# Store processed files temporarily (in production, use proper storage)
processed_files = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "CivicExtract API is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "extractor": "ready",
            "cleaner": "ready",
            "storage": "ready"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and process a document (PDF or image)
    
    Returns:
        JSON response with extracted and structured data
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (limit to 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Validate file type
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff']
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        logger.info(f"Processing file: {file.filename} ({len(file_content)} bytes)")
        
        # Extract data
        extraction_result = extractor.extract_from_file(file_content, file.filename)
        
        # Clean and structure data
        cleaning_result = cleaner.clean_and_structure_data(extraction_result)
        
        # Generate unique ID for this processing session
        session_id = str(uuid.uuid4())
        
        # Prepare response data
        response_data = {
            "session_id": session_id,
            "filename": file.filename,
            "file_size": len(file_content),
            "extraction_method": extraction_result.get('metadata', {}).get('extraction_method', 'unknown'),
            "success": cleaning_result['success'],
            "errors": cleaning_result.get('errors', []),
            "text_summary": cleaning_result.get('text_summary', ''),
            "tables_found": len(cleaning_result['dataframes']),
            "tables": []
        }
        
        # Process each DataFrame
        for i, df_info in enumerate(cleaning_result['dataframes']):
            df = df_info['dataframe']
            
            # Convert DataFrame to JSON-serializable format
            table_data = cleaner.dataframe_to_dict(df)
            
            table_info = {
                "table_id": i + 1,
                "source_page": df_info.get('source_page', 1),
                "rows": df_info['rows'],
                "columns": df_info['columns'],
                "column_names": df_info['column_names'],
                "preview_data": table_data['data'][:5],  # First 5 rows for preview
                "all_columns": table_data['columns']
            }
            
            response_data["tables"].append(table_info)
            
            # Store full DataFrame for download
            processed_files[f"{session_id}_table_{i+1}"] = df
        
        # Store metadata
        processed_files[f"{session_id}_metadata"] = {
            'filename': file.filename,
            'extraction_result': extraction_result,
            'cleaning_result': cleaning_result
        }
        
        logger.info(f"Successfully processed {file.filename} - Session: {session_id}")
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/download/{session_id}/{table_id}/{format}")
async def download_data(session_id: str, table_id: int, format: str):
    """
    Download processed data in CSV or JSON format
    
    Args:
        session_id: Processing session ID
        table_id: Table number (1-based)
        format: 'csv' or 'json'
    """
    try:
        # Validate format
        if format not in ['csv', 'json']:
            raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
        
        # Get DataFrame
        df_key = f"{session_id}_table_{table_id}"
        if df_key not in processed_files:
            raise HTTPException(status_code=404, detail="Data not found or expired")
        
        df = processed_files[df_key]
        metadata = processed_files.get(f"{session_id}_metadata", {})
        original_filename = metadata.get('filename', 'extracted_data')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{format}') as tmp_file:
            if format == 'csv':
                df.to_csv(tmp_file.name, index=False)
                media_type = 'text/csv'
                filename = f"{original_filename}_table_{table_id}.csv"
            else:  # json
                df.to_json(tmp_file.name, orient='records', indent=2)
                media_type = 'application/json'
                filename = f"{original_filename}_table_{table_id}.json"
            
            return FileResponse(
                path=tmp_file.name,
                media_type=media_type,
                filename=filename
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a processing session"""
    try:
        metadata_key = f"{session_id}_metadata"
        if metadata_key not in processed_files:
            raise HTTPException(status_code=404, detail="Session not found")
        
        metadata = processed_files[metadata_key]
        
        # Count available tables
        table_count = 0
        for key in processed_files.keys():
            if key.startswith(f"{session_id}_table_"):
                table_count += 1
        
        return {
            "session_id": session_id,
            "filename": metadata.get('filename'),
            "tables_available": table_count,
            "extraction_method": metadata.get('extraction_result', {}).get('metadata', {}).get('extraction_method'),
            "success": metadata.get('cleaning_result', {}).get('success', False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session info error: {str(e)}")

@app.delete("/sessions/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up session data"""
    try:
        keys_to_remove = [key for key in processed_files.keys() if key.startswith(session_id)]
        
        for key in keys_to_remove:
            del processed_files[key]
        
        return {"message": f"Cleaned up {len(keys_to_remove)} items for session {session_id}"}
        
    except Exception as e:
        logger.error(f"Error cleaning up session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get API usage statistics"""
    return {
        "active_sessions": len(set(key.split('_')[0] for key in processed_files.keys())),
        "total_stored_items": len(processed_files),
        "supported_formats": ["PDF", "JPG", "JPEG", "PNG", "BMP", "TIFF"],
        "max_file_size": "10MB"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    logger.info("Starting CivicExtract API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )