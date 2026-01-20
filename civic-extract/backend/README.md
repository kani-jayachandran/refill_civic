# CivicExtract Backend

AI-powered backend service for extracting and structuring data from public documents.

## Features

- **Multi-format Support**: PDF and image files (JPG, PNG, BMP, TIFF)
- **OCR Processing**: Advanced text extraction using Tesseract
- **PDF Processing**: Native PDF text and table extraction
- **Data Cleaning**: Automatic data normalization and structuring
- **REST API**: Clean, documented endpoints
- **Export Options**: CSV and JSON download formats

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR** (for image processing)

#### Installing Tesseract

**Windows:**
```bash
# Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
# Or using chocolatey:
choco install tesseract
```

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr
```

### Setup

1. **Clone and navigate to backend directory:**
```bash
cd civic-extract/backend
```

2. **Create virtual environment:**
```bash
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure Tesseract (if needed):**
   - Windows users may need to update the tesseract path in `extractor.py`
   - Uncomment and modify this line if tesseract is not in PATH:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

## Running the Server

### Development Mode
```bash
python main.py
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## API Documentation

### Endpoints

#### `GET /`
Health check endpoint
- **Response**: Basic API information

#### `GET /health`
Detailed health check
- **Response**: Service status information

#### `POST /upload`
Upload and process document
- **Parameters**: 
  - `file`: Document file (PDF or image)
- **Response**: Extraction results with session ID

#### `GET /download/{session_id}/{table_id}/{format}`
Download processed data
- **Parameters**:
  - `session_id`: Processing session ID
  - `table_id`: Table number (1-based)
  - `format`: 'csv' or 'json'
- **Response**: File download

#### `GET /sessions/{session_id}`
Get session information
- **Parameters**: `session_id`: Session ID
- **Response**: Session metadata

#### `DELETE /sessions/{session_id}`
Clean up session data
- **Parameters**: `session_id`: Session ID
- **Response**: Cleanup confirmation

#### `GET /stats`
API usage statistics
- **Response**: Current API statistics

### Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Architecture

### Core Components

1. **`main.py`**: FastAPI application and API endpoints
2. **`extractor.py`**: Data extraction logic (OCR and PDF processing)
3. **`cleaner.py`**: Data cleaning and structuring

### Data Flow

1. **File Upload** → Validation and type detection
2. **Extraction** → OCR or PDF processing based on file type
3. **Cleaning** → Data normalization and DataFrame creation
4. **Storage** → Temporary session-based storage
5. **Export** → CSV/JSON download generation

### Processing Methods

#### PDF Processing
- Uses `pdfplumber` for native text and table extraction
- Falls back to OCR if PDF extraction fails
- Preserves table structure and formatting

#### Image Processing
- Preprocesses images for better OCR results
- Uses Tesseract OCR for text extraction
- Attempts to detect tabular structures in text

#### Data Cleaning
- Normalizes column names and cell values
- Infers appropriate data types (numeric, datetime, string)
- Removes empty rows and columns
- Handles OCR artifacts and noise

## Configuration

### Environment Variables

```bash
# Optional: Set custom Tesseract path
TESSERACT_CMD=/usr/local/bin/tesseract

# Optional: Set log level
LOG_LEVEL=INFO

# Optional: Set max file size (bytes)
MAX_FILE_SIZE=10485760  # 10MB
```

### Logging

Logs are configured to output to console with INFO level by default. Modify logging configuration in `main.py` for different setups.

## Error Handling

The API includes comprehensive error handling:

- **File validation**: Type and size checks
- **Processing errors**: Graceful fallbacks and error messages
- **Session management**: Automatic cleanup and error recovery
- **HTTP errors**: Proper status codes and error details

## Performance Considerations

- **File Size Limit**: 10MB default (configurable)
- **Session Storage**: In-memory (use Redis/database for production)
- **Processing Time**: Varies by document complexity and size
- **Concurrent Requests**: Supported via FastAPI's async capabilities

## Development

### Adding New Features

1. **New extraction methods**: Extend `DataExtractor` class
2. **Additional cleaning logic**: Modify `DataCleaner` class
3. **New endpoints**: Add to `main.py` with proper error handling
4. **File format support**: Update validation and processing logic

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when test files are added)
pytest
```

## Troubleshooting

### Common Issues

1. **Tesseract not found**:
   - Ensure Tesseract is installed and in PATH
   - Update tesseract path in `extractor.py` if needed

2. **Poor OCR results**:
   - Check image quality and resolution
   - Ensure text is clearly visible and not rotated
   - Try preprocessing the image externally

3. **PDF extraction fails**:
   - Some PDFs may be image-based (scanned documents)
   - The system will automatically fall back to OCR

4. **Memory issues with large files**:
   - Reduce file size limit in configuration
   - Consider implementing streaming for large files

### Logs and Debugging

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

Check logs for detailed processing information and error traces.

## Security Considerations

- **File validation**: Strict type and size checking
- **Input sanitization**: Clean extracted data before processing
- **Session isolation**: Each session is isolated and temporary
- **CORS configuration**: Update for production domains
- **File cleanup**: Automatic temporary file cleanup

## Production Deployment

### Recommendations

1. **Use proper ASGI server**: Gunicorn with Uvicorn workers
2. **Add authentication**: Implement API key or OAuth
3. **Use external storage**: Redis or database for session data
4. **Add rate limiting**: Prevent abuse and overload
5. **Configure CORS**: Restrict to actual frontend domains
6. **Add monitoring**: Health checks and performance metrics
7. **Use HTTPS**: Secure communication in production

### Example Production Command

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```