/**
 * CivicExtract Frontend JavaScript
 * Handles file upload, API communication, and UI interactions
 */

class CivicExtract {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000';
        this.currentFile = null;
        this.currentSessionId = null;
        
        this.initializeElements();
        this.bindEvents();
    }
    
    initializeElements() {
        // Upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.selectedFile = document.getElementById('selectedFile');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        this.removeFile = document.getElementById('removeFile');
        this.uploadBtn = document.getElementById('uploadBtn');
        
        // Progress elements
        this.progressSection = document.getElementById('progressSection');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        
        // Results elements
        this.resultsSection = document.getElementById('resultsSection');
        this.resultsSummary = document.getElementById('resultsSummary');
        this.textSummaryCard = document.getElementById('textSummaryCard');
        this.textSummary = document.getElementById('textSummary');
        this.tablesContainer = document.getElementById('tablesContainer');
        this.errorMessages = document.getElementById('errorMessages');
        this.errorList = document.getElementById('errorList');
        
        // Loading elements
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingMessage = document.getElementById('loadingMessage');
        
        // Toast container
        this.toastContainer = document.getElementById('toastContainer');
    }
    
    bindEvents() {
        // File upload events
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.removeFile.addEventListener('click', () => this.clearFile());
        this.uploadBtn.addEventListener('click', () => this.uploadFile());
        
        // Drag and drop events
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
    }
    
    handleDragOver(e) {
        this.uploadArea.classList.add('dragover');
    }
    
    handleDragLeave(e) {
        this.uploadArea.classList.remove('dragover');
    }
    
    handleDrop(e) {
        this.uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }
    
    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }
    
    processFile(file) {
        // Validate file type
        const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff'];
        const allowedExtensions = ['pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff'];
        
        const fileExtension = file.name.toLowerCase().split('.').pop();
        
        if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
            this.showToast('Please select a valid file (PDF, JPG, PNG, BMP, TIFF)', 'error');
            return;
        }
        
        // Validate file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            this.showToast('File size must be less than 10MB', 'error');
            return;
        }
        
        this.currentFile = file;
        this.displaySelectedFile(file);
    }
    
    displaySelectedFile(file) {
        this.fileName.textContent = file.name;
        this.fileSize.textContent = this.formatFileSize(file.size);
        
        this.selectedFile.style.display = 'flex';
        this.uploadBtn.disabled = false;
        
        // Hide upload area
        this.uploadArea.style.display = 'none';
    }
    
    clearFile() {
        this.currentFile = null;
        this.selectedFile.style.display = 'none';
        this.uploadArea.style.display = 'block';
        this.uploadBtn.disabled = true;
        this.fileInput.value = '';
        
        // Hide results
        this.hideResults();
    }
    
    async uploadFile() {
        if (!this.currentFile) {
            this.showToast('Please select a file first', 'error');
            return;
        }
        
        try {
            this.showLoading('Uploading and processing your document...');
            this.showProgress();
            
            // Create form data
            const formData = new FormData();
            formData.append('file', this.currentFile);
            
            // Simulate progress
            this.updateProgress(20, 'Uploading file...');
            
            // Upload file
            const response = await fetch(`${this.apiBaseUrl}/upload`, {
                method: 'POST',
                body: formData
            });
            
            this.updateProgress(60, 'Extracting data...');
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }
            
            const result = await response.json();
            
            this.updateProgress(100, 'Processing complete!');
            
            setTimeout(() => {
                this.hideLoading();
                this.hideProgress();
                this.displayResults(result);
            }, 500);
            
        } catch (error) {
            console.error('Upload error:', error);
            this.hideLoading();
            this.hideProgress();
            this.showToast(`Upload failed: ${error.message}`, 'error');
        }
    }
    
    showLoading(message = 'Processing...') {
        this.loadingMessage.textContent = message;
        this.loadingOverlay.style.display = 'flex';
    }
    
    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }
    
    showProgress() {
        this.progressSection.style.display = 'block';
        this.updateProgress(0, 'Initializing...');
    }
    
    hideProgress() {
        this.progressSection.style.display = 'none';
    }
    
    updateProgress(percentage, text) {
        this.progressFill.style.width = `${percentage}%`;
        this.progressText.textContent = text;
    }
    
    displayResults(result) {
        this.currentSessionId = result.session_id;
        
        // Show results section
        this.resultsSection.style.display = 'block';
        
        // Display summary
        this.displaySummary(result);
        
        // Display text summary if available
        if (result.text_summary) {
            this.textSummary.textContent = result.text_summary;
            this.textSummaryCard.style.display = 'block';
        }
        
        // Display tables
        this.displayTables(result.tables);
        
        // Display errors if any
        if (result.errors && result.errors.length > 0) {
            this.displayErrors(result.errors);
        }
        
        // Scroll to results
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
        
        this.showToast('Document processed successfully!', 'success');
    }
    
    displaySummary(result) {
        const summaryHtml = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <strong>📄 File:</strong> ${result.filename}<br>
                    <strong>📊 Method:</strong> ${result.extraction_method.toUpperCase()}
                </div>
                <div>
                    <strong>📋 Tables Found:</strong> ${result.tables_found}<br>
                    <strong>💾 Size:</strong> ${this.formatFileSize(result.file_size)}
                </div>
            </div>
        `;
        this.resultsSummary.innerHTML = summaryHtml;
    }
    
    displayTables(tables) {
        this.tablesContainer.innerHTML = '';
        
        if (!tables || tables.length === 0) {
            this.tablesContainer.innerHTML = `
                <div class="table-card">
                    <h3>📊 No Tables Found</h3>
                    <p>No structured tabular data was detected in your document. The text content is available above.</p>
                </div>
            `;
            return;
        }
        
        tables.forEach((table, index) => {
            const tableCard = this.createTableCard(table, index);
            this.tablesContainer.appendChild(tableCard);
        });
    }
    
    createTableCard(table, index) {
        const card = document.createElement('div');
        card.className = 'table-card';
        
        const tableHtml = `
            <div class="table-header">
                <div class="table-info">
                    <h3>📊 Table ${table.table_id}</h3>
                    <div class="table-meta">
                        Page ${table.source_page} • ${table.rows} rows × ${table.columns} columns
                    </div>
                </div>
                <div class="download-buttons">
                    <button class="download-btn csv" onclick="civicExtract.downloadTable(${table.table_id}, 'csv')">
                        📄 Download CSV
                    </button>
                    <button class="download-btn json" onclick="civicExtract.downloadTable(${table.table_id}, 'json')">
                        📋 Download JSON
                    </button>
                </div>
            </div>
            <div class="table-container">
                ${this.createTableHTML(table)}
            </div>
        `;
        
        card.innerHTML = tableHtml;
        return card;
    }
    
    createTableHTML(table) {
        if (!table.preview_data || table.preview_data.length === 0) {
            return '<p>No preview data available</p>';
        }
        
        let html = '<table class="data-table"><thead><tr>';
        
        // Create headers
        table.all_columns.forEach(column => {
            html += `<th>${this.escapeHtml(column)}</th>`;
        });
        html += '</tr></thead><tbody>';
        
        // Create rows (limit to preview data)
        table.preview_data.forEach(row => {
            html += '<tr>';
            row.forEach(cell => {
                const cellValue = cell === null || cell === undefined ? '' : String(cell);
                html += `<td>${this.escapeHtml(cellValue)}</td>`;
            });
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        
        if (table.rows > table.preview_data.length) {
            html += `<p style="text-align: center; margin-top: 10px; color: #718096; font-style: italic;">
                Showing first ${table.preview_data.length} rows of ${table.rows} total rows. Download for complete data.
            </p>`;
        }
        
        return html;
    }
    
    async downloadTable(tableId, format) {
        if (!this.currentSessionId) {
            this.showToast('No active session found', 'error');
            return;
        }
        
        try {
            const url = `${this.apiBaseUrl}/download/${this.currentSessionId}/${tableId}/${format}`;
            
            // Create a temporary link and click it
            const link = document.createElement('a');
            link.href = url;
            link.download = `table_${tableId}.${format}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showToast(`Table ${tableId} downloaded as ${format.toUpperCase()}`, 'success');
            
        } catch (error) {
            console.error('Download error:', error);
            this.showToast(`Download failed: ${error.message}`, 'error');
        }
    }
    
    displayErrors(errors) {
        this.errorList.innerHTML = '';
        errors.forEach(error => {
            const li = document.createElement('li');
            li.textContent = error;
            this.errorList.appendChild(li);
        });
        this.errorMessages.style.display = 'block';
    }
    
    hideResults() {
        this.resultsSection.style.display = 'none';
        this.textSummaryCard.style.display = 'none';
        this.errorMessages.style.display = 'none';
        this.tablesContainer.innerHTML = '';
    }
    
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        this.toastContainer.appendChild(toast);
        
        // Remove toast after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.civicExtract = new CivicExtract();
});

// Handle API connection errors
window.addEventListener('unhandledrejection', (event) => {
    if (event.reason && event.reason.message && event.reason.message.includes('fetch')) {
        console.error('API connection error:', event.reason);
        if (window.civicExtract) {
            window.civicExtract.showToast('Cannot connect to API server. Please ensure the backend is running on http://localhost:8000', 'error');
        }
    }
});