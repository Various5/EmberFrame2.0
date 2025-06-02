// static/js/apps/file-manager.js
/**
 * Enhanced File Manager Application
 */

class FileManagerApp {
    constructor(windowId, desktop) {
        this.windowId = windowId;
        this.desktop = desktop;
        this.currentPath = '/';
        this.selectedFiles = new Set();
        this.viewMode = 'grid'; // grid, list, details
        this.sortBy = 'name';
        this.sortOrder = 'asc';
        this.searchQuery = '';
        this.clipboardFiles = [];
        this.clipboardOperation = null; // copy, cut

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFiles();
        this.updateUI();
    }

    setupEventListeners() {
        const content = document.getElementById(`content-${this.windowId}`);

        // File grid events
        content.addEventListener('click', (e) => {
            const fileItem = e.target.closest('.file-item');
            if (fileItem) {
                this.handleFileClick(fileItem, e);
            }
        });

        content.addEventListener('dblclick', (e) => {
            const fileItem = e.target.closest('.file-item');
            if (fileItem) {
                this.handleFileDoubleClick(fileItem);
            }
        });

        content.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            const fileItem = e.target.closest('.file-item');
            this.showContextMenu(e.clientX, e.clientY, fileItem);
        });

        // Keyboard shortcuts
        content.addEventListener('keydown', (e) => {
            this.handleKeyboard(e);
        });

        // Drag and drop
        this.setupDragAndDrop(content);
    }

    setupDragAndDrop(container) {
        container.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });

        container.addEventListener('drop', (e) => {
            e.preventDefault();
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.uploadFiles(files);
            }
        });

        // Internal drag and drop for file operations
        container.addEventListener('dragstart', (e) => {
            const fileItem = e.target.closest('.file-item');
            if (fileItem) {
                const fileName = fileItem.dataset.file;
                e.dataTransfer.setData('text/plain', fileName);
                e.dataTransfer.effectAllowed = 'move';
            }
        });
    }

    async loadFiles(path = this.currentPath) {
        try {
            this.showLoading();

            const response = await fetch(`/api/files/?path=${encodeURIComponent(path)}&sort=${this.sortBy}&order=${this.sortOrder}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.currentPath = path;
                this.displayFiles(data.files || []);
                this.updateAddressBar();
                this.updateStatus(data);
            } else {
                throw new Error('Failed to load files');
            }
        } catch (error) {
            this.showError('Error loading files: ' + error.message);
        }
    }

    displayFiles(files) {
        const fileGrid = document.querySelector(`#content-${this.windowId} .file-grid`);

        if (!files || files.length === 0) {
            fileGrid.innerHTML = this.getEmptyStateHTML();
            return;
        }

        const filesHTML = files.map(file => this.getFileItemHTML(file)).join('');
        fileGrid.innerHTML = filesHTML;

        this.updateFileCount(files.length);
    }

    getFileItemHTML(file) {
        const isSelected = this.selectedFiles.has(file.name);
        const icon = this.getFileIcon(file);
        const size = file.size ? this.formatFileSize(file.size) : '';
        const modified = file.modified ? new Date(file.modified * 1000).toLocaleDateString() : '';

        return `
            <div class="file-item ${isSelected ? 'selected' : ''}" 
                 data-file="${file.name}" 
                 data-type="${file.type}"
                 data-size="${file.size || 0}"
                 data-modified="${file.modified || 0}"
                 draggable="true">
                <div class="file-icon">
                    <i class="fas ${icon}"></i>
                    ${file.type === 'image' ? `<div class="thumbnail" style="background-image: url('/api/files/thumbnail/${encodeURIComponent(this.currentPath)}/${encodeURIComponent(file.name)}')"></div>` : ''}
                </div>
                <div class="file-info">
                    <div class="file-name" title="${file.name}">${this.truncateFileName(file.name)}</div>
                    ${this.viewMode === 'details' ? `
                        <div class="file-details">
                            <span class="file-size">${size}</span>
                            <span class="file-date">${modified}</span>
                        </div>
                    ` : size ? `<div class="file-size">${size}</div>` : ''}
                </div>
                <div class="file-actions">
                    <button class="btn-icon" onclick="fileManager.shareFile('${file.name}')" title="Share">
                        <i class="fas fa-share-alt"></i>
                    </button>
                    <button class="btn-icon" onclick="fileManager.downloadFile('${file.name}')" title="Download">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </div>
        `;
    }

    getFileIcon(file) {
        if (file.type === 'folder') return 'fa-folder';

        const ext = file.name.split('.').pop()?.toLowerCase() || '';
        const iconMap = {
            // Images
            'jpg': 'fa-file-image', 'jpeg': 'fa-file-image', 'png': 'fa-file-image',
            'gif': 'fa-file-image', 'bmp': 'fa-file-image', 'svg': 'fa-file-image',
            // Documents
            'pdf': 'fa-file-pdf', 'doc': 'fa-file-word', 'docx': 'fa-file-word',
            'txt': 'fa-file-text', 'md': 'fa-file-text', 'rtf': 'fa-file-text',
            // Spreadsheets
            'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel', 'csv': 'fa-file-csv',
            // Presentations
            'ppt': 'fa-file-powerpoint', 'pptx': 'fa-file-powerpoint',
            // Audio
            'mp3': 'fa-file-audio', 'wav': 'fa-file-audio', 'ogg': 'fa-file-audio',
            'flac': 'fa-file-audio', 'm4a': 'fa-file-audio',
            // Video
            'mp4': 'fa-file-video', 'avi': 'fa-file-video', 'mkv': 'fa-file-video',
            'mov': 'fa-file-video', 'wmv': 'fa-file-video',
            // Archives
            'zip': 'fa-file-archive', 'rar': 'fa-file-archive', '7z': 'fa-file-archive',
            'tar': 'fa-file-archive', 'gz': 'fa-file-archive',
            // Code
            'js': 'fa-file-code', 'html': 'fa-file-code', 'css': 'fa-file-code',
            'py': 'fa-file-code', 'php': 'fa-file-code', 'java': 'fa-file-code',
            'cpp': 'fa-file-code', 'c': 'fa-file-code', 'json': 'fa-file-code'
        };

        return iconMap[ext] || 'fa-file';
    }

    handleFileClick(fileItem, event) {
        const fileName = fileItem.dataset.file;

        if (event.ctrlKey || event.metaKey) {
            // Multi-select
            this.toggleFileSelection(fileName);
        } else if (event.shiftKey && this.selectedFiles.size > 0) {
            // Range select
            this.selectFileRange(fileName);
        } else {
            // Single select
            this.clearSelection();
            this.selectFile(fileName);
        }

        this.updateSelectionUI();
    }

    handleFileDoubleClick(fileItem) {
        const fileName = fileItem.dataset.file;
        const fileType = fileItem.dataset.type;

        if (fileType === 'folder') {
            this.navigateToFolder(fileName);
        } else {
            this.openFile(fileName);
        }
    }

    handleKeyboard(event) {
        switch (event.key) {
            case 'Delete':
                event.preventDefault();
                this.deleteSelectedFiles();
                break;
            case 'Enter':
                event.preventDefault();
                if (this.selectedFiles.size === 1) {
                    const fileName = Array.from(this.selectedFiles)[0];
                    const fileItem = document.querySelector(`[data-file="${fileName}"]`);
                    if (fileItem) {
                        this.handleFileDoubleClick(fileItem);
                    }
                }
                break;
            case 'F2':
                event.preventDefault();
                this.renameSelectedFile();
                break;
            case 'a':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    this.selectAllFiles();
                }
                break;
            case 'c':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    this.copySelectedFiles();
                }
                break;
            case 'x':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    this.cutSelectedFiles();
                }
                break;
            case 'v':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    this.pasteFiles();
                }
                break;
        }
    }

    // File operations
    async uploadFiles(files) {
        try {
            const formData = new FormData();
            files.forEach(file => {
                formData.append('files', file);
            });
            formData.append('path', this.currentPath);

            const response = await fetch('/api/files/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                },
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                this.showSuccess(`Uploaded ${result.uploaded_files.length} file(s)`);
                await this.loadFiles();
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            this.showError('Upload failed: ' + error.message);
        }
    }

    async createFolder() {
        const name = prompt('Enter folder name:');
        if (!name || !name.trim()) return;

        try {
            const response = await fetch('/api/files/folder', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `path=${encodeURIComponent(this.currentPath)}&name=${encodeURIComponent(name.trim())}`
            });

            if (response.ok) {
                this.showSuccess(`Created folder: ${name.trim()}`);
                await this.loadFiles();
            } else {
                throw new Error('Failed to create folder');
            }
        } catch (error) {
            this.showError('Failed to create folder: ' + error.message);
        }
    }

    async deleteSelectedFiles() {
        if (this.selectedFiles.size === 0) return;

        const fileNames = Array.from(this.selectedFiles);
        const confirmMessage = fileNames.length === 1
            ? `Are you sure you want to delete "${fileNames[0]}"?`
            : `Are you sure you want to delete ${fileNames.length} files?`;

        if (!confirm(confirmMessage)) return;

        try {
            for (const fileName of fileNames) {
                const filePath = this.currentPath === '/'
                    ? fileName
                    : `${this.currentPath}/${fileName}`;

                const response = await fetch(`/api/files/${encodeURIComponent(filePath)}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                    }
                });

                if (!response.ok) {
                    throw new Error(`Failed to delete ${fileName}`);
                }
            }

            this.showSuccess(`Deleted ${fileNames.length} file(s)`);
            this.clearSelection();
            await this.loadFiles();
        } catch (error) {
            this.showError('Delete failed: ' + error.message);
        }
    }

    async renameSelectedFile() {
        if (this.selectedFiles.size !== 1) return;

        const oldName = Array.from(this.selectedFiles)[0];
        const newName = prompt('Enter new name:', oldName);

        if (!newName || newName === oldName) return;

        try {
            const response = await fetch('/api/files/rename', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    old_path: this.currentPath === '/' ? oldName : `${this.currentPath}/${oldName}`,
                    new_name: newName
                })
            });

            if (response.ok) {
                this.showSuccess(`Renamed to: ${newName}`);
                this.clearSelection();
                await this.loadFiles();
            } else {
                throw new Error('Rename failed');
            }
        } catch (error) {
            this.showError('Rename failed: ' + error.message);
        }
    }

    copySelectedFiles() {
        if (this.selectedFiles.size === 0) return;

        this.clipboardFiles = Array.from(this.selectedFiles);
        this.clipboardOperation = 'copy';

        this.showSuccess(`Copied ${this.clipboardFiles.length} file(s) to clipboard`);
    }

    cutSelectedFiles() {
        if (this.selectedFiles.size === 0) return;

        this.clipboardFiles = Array.from(this.selectedFiles);
        this.clipboardOperation = 'cut';

        this.showSuccess(`Cut ${this.clipboardFiles.length} file(s) to clipboard`);
    }

    async pasteFiles() {
        if (this.clipboardFiles.length === 0) return;

        try {
            const operation = this.clipboardOperation === 'cut' ? 'move' : 'copy';

            const response = await fetch('/api/files/paste', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    files: this.clipboardFiles,
                    target_path: this.currentPath,
                    operation: operation
                })
            });

            if (response.ok) {
                this.showSuccess(`${operation === 'move' ? 'Moved' : 'Copied'} ${this.clipboardFiles.length} file(s)`);

                if (operation === 'move') {
                    this.clipboardFiles = [];
                    this.clipboardOperation = null;
                }

                await this.loadFiles();
            } else {
                throw new Error('Paste operation failed');
            }
        } catch (error) {
            this.showError('Paste failed: ' + error.message);
        }
    }

    // Selection management
    selectFile(fileName) {
        this.selectedFiles.add(fileName);
    }

    toggleFileSelection(fileName) {
        if (this.selectedFiles.has(fileName)) {
            this.selectedFiles.delete(fileName);
        } else {
            this.selectedFiles.add(fileName);
        }
    }

    clearSelection() {
        this.selectedFiles.clear();
    }

    selectAllFiles() {
        const fileItems = document.querySelectorAll(`#content-${this.windowId} .file-item`);
        fileItems.forEach(item => {
            this.selectedFiles.add(item.dataset.file);
        });
        this.updateSelectionUI();
    }

    updateSelectionUI() {
        const fileItems = document.querySelectorAll(`#content-${this.windowId} .file-item`);
        fileItems.forEach(item => {
            const fileName = item.dataset.file;
            if (this.selectedFiles.has(fileName)) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    // UI helpers
    showLoading() {
        const fileGrid = document.querySelector(`#content-${this.windowId} .file-grid`);
        fileGrid.innerHTML = '<div class="loading">Loading files...</div>';
    }

    showError(message) {
        this.desktop.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.desktop.showNotification(message, 'success');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    truncateFileName(name, maxLength = 15) {
        if (name.length <= maxLength) return name;
        const ext = name.split('.').pop();
        const baseName = name.substring(0, name.lastIndexOf('.'));
        const truncatedBase = baseName.substring(0, maxLength - ext.length - 4);
        return `${truncatedBase}...${ext}`;
    }

    getEmptyStateHTML() {
        return `
            <div class="empty-state">
                <i class="fas fa-folder-open" style="font-size: 64px; opacity: 0.3; margin-bottom: 20px;"></i>
                <h3>No files found</h3>
                <p>Drag and drop files here or click the upload button</p>
                <button class="btn btn-primary" onclick="this.uploadFiles()">
                    <i class="fas fa-upload"></i> Upload Files
                </button>
            </div>
        `;
    }
}

// static/js/apps/text-editor.js
/**
 * Advanced Text Editor Application
 */

class TextEditorApp {
    constructor(windowId, desktop) {
        this.windowId = windowId;
        this.desktop = desktop;
        this.currentFile = null;
        this.isDirty = false;
        this.content = '';
        this.history = [];
        this.historyIndex = -1;
        this.settings = {
            fontSize: 14,
            fontFamily: 'Monaco, monospace',
            theme: 'light',
            lineNumbers: true,
            wordWrap: true,
            tabSize: 4
        };

        this.init();
    }

    init() {
        this.setupEditor();
        this.setupEventListeners();
        this.loadSettings();
        this.newFile();
    }

    setupEditor() {
        const content = document.getElementById(`content-${this.windowId}`);
        content.innerHTML = this.getEditorHTML();

        this.textarea = content.querySelector('#textEditor');
        this.lineNumbers = content.querySelector('#lineNumbers');
        this.statusBar = content.querySelector('#statusBar');

        this.updateLineNumbers();
        this.updateStatus();
    }

    getEditorHTML() {
        return `
            <div class="text-editor" style="height: 100%; display: flex; flex-direction: column;">
                <!-- Toolbar -->
                <div class="editor-toolbar">
                    <div class="toolbar-group">
                        <button class="toolbar-btn" onclick="textEditor.newFile()" title="New File (Ctrl+N)">
                            <i class="fas fa-file"></i> New
                        </button>
                        <button class="toolbar-btn" onclick="textEditor.openFile()" title="Open File (Ctrl+O)">
                            <i class="fas fa-folder-open"></i> Open
                        </button>
                        <button class="toolbar-btn" onclick="textEditor.saveFile()" title="Save File (Ctrl+S)">
                            <i class="fas fa-save"></i> Save
                        </button>
                        <button class="toolbar-btn" onclick="textEditor.saveAsFile()" title="Save As (Ctrl+Shift+S)">
                            <i class="fas fa-save"></i> Save As
                        </button>
                    </div>
                    
                    <div class="toolbar-group">
                        <button class="toolbar-btn" onclick="textEditor.undo()" title="Undo (Ctrl+Z)">
                            <i class="fas fa-undo"></i> Undo
                        </button>
                        <button class="toolbar-btn" onclick="textEditor.redo()" title="Redo (Ctrl+Y)">
                            <i class="fas fa-redo"></i> Redo
                        </button>
                    </div>
                    
                    <div class="toolbar-group">
                        <button class="toolbar-btn" onclick="textEditor.find()" title="Find (Ctrl+F)">
                            <i class="fas fa-search"></i> Find
                        </button>
                        <button class="toolbar-btn" onclick="textEditor.replace()" title="Replace (Ctrl+H)">
                            <i class="fas fa-exchange-alt"></i> Replace
                        </button>
                    </div>
                    
                    <div class="toolbar-group">
                        <select id="fontSizeSelect" onchange="textEditor.changeFontSize(this.value)">
                            <option value="10">10px</option>
                            <option value="12">12px</option>
                            <option value="14" selected>14px</option>
                            <option value="16">16px</option>
                            <option value="18">18px</option>
                            <option value="20">20px</option>
                            <option value="24">24px</option>
                        </select>
                        
                        <select id="fontFamilySelect" onchange="textEditor.changeFontFamily(this.value)">
                            <option value="Monaco, monospace">Monaco</option>
                            <option value="Consolas, monospace">Consolas</option>
                            <option value="'Courier New', monospace">Courier New</option>
                            <option value="'Source Code Pro', monospace">Source Code Pro</option>
                            <option value="'Fira Code', monospace">Fira Code</option>
                        </select>
                    </div>
                    
                    <div class="toolbar-group">
                        <button class="toolbar-btn" onclick="textEditor.toggleTheme()" title="Toggle Theme">
                            <i class="fas fa-palette"></i> Theme
                        </button>
                        <button class="toolbar-btn" onclick="textEditor.toggleLineNumbers()" title="Toggle Line Numbers">
                            <i class="fas fa-list-ol"></i> Lines
                        </button>
                        <button class="toolbar-btn" onclick="textEditor.toggleWordWrap()" title="Toggle Word Wrap">
                            <i class="fas fa-align-left"></i> Wrap
                        </button>
                    </div>
                </div>
                
                <!-- Editor Area -->
                <div class="editor-content" style="flex: 1; display: flex; position: relative;">
                    <div id="lineNumbers" class="line-numbers" style="display: ${this.settings.lineNumbers ? 'block' : 'none'};">1</div>
                    <textarea id="textEditor" 
                              style="flex: 1; font-family: ${this.settings.fontFamily}; font-size: ${this.settings.fontSize}px; resize: none; border: none; outline: none; padding: 10px; line-height: 1.5; white-space: ${this.settings.wordWrap ? 'pre-wrap' : 'pre'};"
                              placeholder="Start typing your text here..."
                              spellcheck="false"></textarea>
                </div>
                
                <!-- Status Bar -->
                <div id="statusBar" class="status-bar">
                    <span id="cursorPosition">Line 1, Column 1</span>
                    <span id="fileStatus">New File</span>
                    <span id="fileSize">0 characters</span>
                    <span id="encoding">UTF-8</span>
                </div>
                
                <!-- Find/Replace Dialog -->
                <div id="findDialog" class="find-dialog" style="display: none;">
                    <div class="find-content">
                        <div class="find-row">
                            <label>Find:</label>
                            <input type="text" id="findInput" placeholder="Search...">
                            <button onclick="textEditor.findNext()">Find Next</button>
                            <button onclick="textEditor.findPrevious()">Find Previous</button>
                        </div>
                        <div class="find-row" id="replaceRow" style="display: none;">
                            <label>Replace:</label>
                            <input type="text" id="replaceInput" placeholder="Replace with...">
                            <button onclick="textEditor.replaceNext()">Replace</button>
                            <button onclick="textEditor.replaceAll()">Replace All</button>
                        </div>
                        <div class="find-options">
                            <label><input type="checkbox" id="caseSensitive"> Case sensitive</label>
                            <label><input type="checkbox" id="wholeWord"> Whole word</label>
                            <label><input type="checkbox" id="useRegex"> Regular expression</label>
                        </div>
                        <button class="close-btn" onclick="textEditor.closeFindDialog()">×</button>
                    </div>
                </div>
            </div>
            
            <style>
                .text-editor {
                    background: var(--window-bg);
                    color: var(--text-color);
                }
                
                .editor-toolbar {
                    display: flex;
                    gap: 10px;
                    padding: 10px;
                    border-bottom: 1px solid var(--border-color);
                    flex-wrap: wrap;
                }
                
                .toolbar-group {
                    display: flex;
                    gap: 5px;
                    align-items: center;
                }
                
                .toolbar-btn {
                    padding: 6px 10px;
                    background: var(--primary-color);
                    border: none;
                    border-radius: 4px;
                    color: white;
                    cursor: pointer;
                    font-size: 0.85rem;
                }
                
                .toolbar-btn:hover {
                    background: var(--secondary-color);
                }
                
                .editor-content {
                    position: relative;
                    background: #fff;
                    color: #333;
                }
                
                .editor-content.dark {
                    background: #1e1e1e;
                    color: #d4d4d4;
                }
                
                .line-numbers {
                    background: #f8f8f8;
                    color: #666;
                    padding: 10px 8px;
                    font-family: Monaco, monospace;
                    font-size: 14px;
                    line-height: 1.5;
                    text-align: right;
                    user-select: none;
                    border-right: 1px solid #ddd;
                    white-space: pre;
                }
                
                .line-numbers.dark {
                    background: #252526;
                    color: #858585;
                    border-right-color: #3e3e3e;
                }
                
                .status-bar {
                    display: flex;
                    justify-content: space-between;
                    padding: 5px 10px;
                    background: #f0f0f0;
                    border-top: 1px solid var(--border-color);
                    font-size: 0.8rem;
                    color: #666;
                }
                
                .status-bar.dark {
                    background: #252526;
                    color: #cccccc;
                }
                
                .find-dialog {
                    position: absolute;
                    top: 50px;
                    right: 20px;
                    background: white;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    padding: 15px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 1000;
                    min-width: 300px;
                }
                
                .find-row {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 10px;
                }
                
                .find-row label {
                    min-width: 60px;
                }
                
                .find-row input[type="text"] {
                    flex: 1;
                    padding: 5px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
                
                .find-options {
                    display: flex;
                    gap: 15px;
                    margin-top: 10px;
                    font-size: 0.85rem;
                }
                
                .close-btn {
                    position: absolute;
                    top: 5px;
                    right: 5px;
                    background: none;
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    color: #666;
                }
            </style>
        `;
    }

    setupEventListeners() {
        this.textarea.addEventListener('input', () => {
            this.markDirty();
            this.updateLineNumbers();
            this.updateStatus();
            this.saveToHistory();
        });

        this.textarea.addEventListener('keydown', (e) => {
            this.handleKeyboard(e);
        });

        this.textarea.addEventListener('click', () => {
            this.updateStatus();
        });

        this.textarea.addEventListener('keyup', () => {
            this.updateStatus();
        });

        // Auto-save every 30 seconds
        setInterval(() => {
            if (this.isDirty && this.currentFile) {
                this.autoSave();
            }
        }, 30000);
    }

    handleKeyboard(e) {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'n':
                    e.preventDefault();
                    this.newFile();
                    break;
                case 'o':
                    e.preventDefault();
                    this.openFile();
                    break;
                case 's':
                    e.preventDefault();
                    if (e.shiftKey) {
                        this.saveAsFile();
                    } else {
                        this.saveFile();
                    }
                    break;
                case 'f':
                    e.preventDefault();
                    this.find();
                    break;
                case 'h':
                    e.preventDefault();
                    this.replace();
                    break;
                case 'z':
                    e.preventDefault();
                    if (e.shiftKey) {
                        this.redo();
                    } else {
                        this.undo();
                    }
                    break;
                case 'y':
                    e.preventDefault();
                    this.redo();
                    break;
            }
        }

        // Handle tab key for indentation
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = this.textarea.selectionStart;
            const end = this.textarea.selectionEnd;
            const spaces = ' '.repeat(this.settings.tabSize);

            this.textarea.value = this.textarea.value.substring(0, start) +
                                 spaces +
                                 this.textarea.value.substring(end);

            this.textarea.selectionStart = this.textarea.selectionEnd = start + spaces.length;
        }
    }

    // File operations
    newFile() {
        if (this.isDirty && !confirm('You have unsaved changes. Continue?')) {
            return;
        }

        this.currentFile = null;
        this.textarea.value = '';
        this.content = '';
        this.isDirty = false;
        this.history = [];
        this.historyIndex = -1;

        this.updateStatus();
        this.updateWindowTitle();
    }

    openFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.md,.js,.html,.css,.json,.xml,.py,.php,.java,.cpp,.c';

        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                if (this.isDirty && !confirm('You have unsaved changes. Continue?')) {
                    return;
                }

                const reader = new FileReader();
                reader.onload = (e) => {
                    this.currentFile = {
                        name: file.name,
                        content: e.target.result
                    };

                    this.textarea.value = this.currentFile.content;
                    this.content = this.currentFile.content;
                    this.isDirty = false;

                    this.updateLineNumbers();
                    this.updateStatus();
                    this.updateWindowTitle();
                    this.saveToHistory();
                };
                reader.readAsText(file);
            }
        };

        input.click();
    }

    saveFile() {
        if (!this.currentFile) {
            this.saveAsFile();
            return;
        }

        this.performSave();
    }

    saveAsFile() {
        const filename = prompt('Enter filename:', this.currentFile?.name || 'untitled.txt');
        if (!filename) return;

        this.currentFile = {
            name: filename,
            content: this.textarea.value
        };

        this.performSave();
    }

    performSave() {
        const content = this.textarea.value;
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = this.currentFile.name;
        a.click();

        URL.revokeObjectURL(url);

        this.content = content;
        this.isDirty = false;
        this.updateStatus();
        this.updateWindowTitle();

        this.desktop.showNotification(`Saved: ${this.currentFile.name}`, 'success');
    }

    autoSave() {
        if (this.currentFile) {
            // Save to localStorage as backup
            localStorage.setItem(`textEditor_autosave_${this.currentFile.name}`, this.textarea.value);
            console.log('Auto-saved to localStorage');
        }
    }

    // Edit operations
    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.textarea.value = this.history[this.historyIndex];
            this.updateLineNumbers();
            this.updateStatus();
        }
    }

    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.textarea.value = this.history[this.historyIndex];
            this.updateLineNumbers();
            this.updateStatus();
        }
    }

    saveToHistory() {
        const content = this.textarea.value;

        // Only save if content actually changed
        if (this.history.length === 0 || this.history[this.historyIndex] !== content) {
            // Remove any history after current index
            this.history = this.history.slice(0, this.historyIndex + 1);

            // Add new state
            this.history.push(content);
            this.historyIndex = this.history.length - 1;

            // Limit history size
            if (this.history.length > 50) {
                this.history.shift();
                this.historyIndex--;
            }
        }
    }

    // Find and replace
    find() {
        const dialog = document.getElementById('findDialog');
        const replaceRow = document.getElementById('replaceRow');

        replaceRow.style.display = 'none';
        dialog.style.display = 'block';

        document.getElementById('findInput').focus();
    }

    replace() {
        const dialog = document.getElementById('findDialog');
        const replaceRow = document.getElementById('replaceRow');

        replaceRow.style.display = 'flex';
        dialog.style.display = 'block';

        document.getElementById('findInput').focus();
    }

    closeFindDialog() {
        document.getElementById('findDialog').style.display = 'none';
    }

    findNext() {
        const searchTerm = document.getElementById('findInput').value;
        if (!searchTerm) return;

        const content = this.textarea.value;
        const caseSensitive = document.getElementById('caseSensitive').checked;
        const searchContent = caseSensitive ? content : content.toLowerCase();
        const searchFor = caseSensitive ? searchTerm : searchTerm.toLowerCase();

        const currentPos = this.textarea.selectionStart;
        const foundIndex = searchContent.indexOf(searchFor, currentPos + 1);

        if (foundIndex !== -1) {
            this.textarea.setSelectionRange(foundIndex, foundIndex + searchTerm.length);
            this.textarea.focus();
        } else {
            // Search from beginning
            const foundFromStart = searchContent.indexOf(searchFor);
            if (foundFromStart !== -1) {
                this.textarea.setSelectionRange(foundFromStart, foundFromStart + searchTerm.length);
                this.textarea.focus();
            } else {
                this.desktop.showNotification('Text not found', 'warning');
            }
        }
    }

    findPrevious() {
        const searchTerm = document.getElementById('findInput').value;
        if (!searchTerm) return;

        const content = this.textarea.value;
        const caseSensitive = document.getElementById('caseSensitive').checked;
        const searchContent = caseSensitive ? content : content.toLowerCase();
        const searchFor = caseSensitive ? searchTerm : searchTerm.toLowerCase();

        const currentPos = this.textarea.selectionStart;
        const beforeCursor = searchContent.substring(0, currentPos);
        const foundIndex = beforeCursor.lastIndexOf(searchFor);

        if (foundIndex !== -1) {
            this.textarea.setSelectionRange(foundIndex, foundIndex + searchTerm.length);
            this.textarea.focus();
        } else {
            this.desktop.showNotification('Text not found', 'warning');
        }
    }

    replaceNext() {
        const searchTerm = document.getElementById('findInput').value;
        const replaceTerm = document.getElementById('replaceInput').value;

        if (!searchTerm) return;

        const selectedText = this.textarea.value.substring(
            this.textarea.selectionStart,
            this.textarea.selectionEnd
        );

        const caseSensitive = document.getElementById('caseSensitive').checked;
        const matches = caseSensitive ?
            selectedText === searchTerm :
            selectedText.toLowerCase() === searchTerm.toLowerCase();

        if (matches) {
            // Replace selected text
            const start = this.textarea.selectionStart;
            const end = this.textarea.selectionEnd;

            this.textarea.value = this.textarea.value.substring(0, start) +
                                 replaceTerm +
                                 this.textarea.value.substring(end);

            this.textarea.setSelectionRange(start, start + replaceTerm.length);
            this.markDirty();
            this.updateLineNumbers();
            this.updateStatus();
        }

        // Find next occurrence
        this.findNext();
    }

    replaceAll() {
        const searchTerm = document.getElementById('findInput').value;
        const replaceTerm = document.getElementById('replaceInput').value;

        if (!searchTerm) return;

        const caseSensitive = document.getElementById('caseSensitive').checked;
        const content = this.textarea.value;

        let newContent;
        let count = 0;

        if (caseSensitive) {
            newContent = content.split(searchTerm).join(replaceTerm);
            count = content.split(searchTerm).length - 1;
        } else {
            const regex = new RegExp(searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
            newContent = content.replace(regex, replaceTerm);
            count = (content.match(regex) || []).length;
        }

        if (count > 0) {
            this.textarea.value = newContent;
            this.markDirty();
            this.updateLineNumbers();
            this.updateStatus();
            this.desktop.showNotification(`Replaced ${count} occurrence(s)`, 'success');
        } else {
            this.desktop.showNotification('No occurrences found', 'warning');
        }
    }

    // Settings and UI
    changeFontSize(size) {
        this.settings.fontSize = parseInt(size);
        this.textarea.style.fontSize = size + 'px';
        this.lineNumbers.style.fontSize = size + 'px';
        this.updateLineNumbers();
    }

    changeFontFamily(family) {
        this.settings.fontFamily = family;
        this.textarea.style.fontFamily = family;
        this.lineNumbers.style.fontFamily = family;
    }

    toggleTheme() {
        const editorContent = document.querySelector(`#content-${this.windowId} .editor-content`);
        const lineNumbers = document.querySelector(`#content-${this.windowId} .line-numbers`);
        const statusBar = document.querySelector(`#content-${this.windowId} .status-bar`);

        if (this.settings.theme === 'light') {
            this.settings.theme = 'dark';
            editorContent.classList.add('dark');
            lineNumbers.classList.add('dark');
            statusBar.classList.add('dark');
            this.textarea.style.background = '#1e1e1e';
            this.textarea.style.color = '#d4d4d4';
        } else {
            this.settings.theme = 'light';
            editorContent.classList.remove('dark');
            lineNumbers.classList.remove('dark');
            statusBar.classList.remove('dark');
            this.textarea.style.background = '#fff';
            this.textarea.style.color = '#333';
        }
    }

    toggleLineNumbers() {
        this.settings.lineNumbers = !this.settings.lineNumbers;
        this.lineNumbers.style.display = this.settings.lineNumbers ? 'block' : 'none';
    }

    toggleWordWrap() {
        this.settings.wordWrap = !this.settings.wordWrap;
        this.textarea.style.whiteSpace = this.settings.wordWrap ? 'pre-wrap' : 'pre';
    }

    updateLineNumbers() {
        if (!this.settings.lineNumbers) return;

        const lines = this.textarea.value.split('\n').length;
        const lineNumbersText = Array.from({length: lines}, (_, i) => i + 1).join('\n');
        this.lineNumbers.textContent = lineNumbersText;
    }

    updateStatus() {
        const content = this.textarea.value;
        const lines = content.split('\n');
        const currentLine = content.substring(0, this.textarea.selectionStart).split('\n').length;
        const currentCol = this.textarea.selectionStart - content.lastIndexOf('\n', this.textarea.selectionStart - 1);

        document.getElementById('cursorPosition').textContent = `Line ${currentLine}, Column ${currentCol}`;
        document.getElementById('fileStatus').textContent = this.currentFile ?
            (this.isDirty ? `${this.currentFile.name} •` : this.currentFile.name) :
            'New File';
        document.getElementById('fileSize').textContent = `${content.length} characters, ${lines.length} lines`;
    }

    updateWindowTitle() {
        const window = document.getElementById(`window-${this.windowId}`);
        const title = window.querySelector('.window-title span');

        if (this.currentFile) {
            title.textContent = `Text Editor - ${this.currentFile.name}${this.isDirty ? ' •' : ''}`;
        } else {
            title.textContent = 'Text Editor - New File';
        }
    }

    markDirty() {
        this.isDirty = true;
        this.updateWindowTitle();
    }

    loadSettings() {
        const saved = localStorage.getItem('textEditor_settings');
        if (saved) {
            this.settings = {...this.settings, ...JSON.parse(saved)};
            this.applySettings();
        }
    }

    saveSettings() {
        localStorage.setItem('textEditor_settings', JSON.stringify(this.settings));
    }

    applySettings() {
        this.textarea.style.fontSize = this.settings.fontSize + 'px';
        this.textarea.style.fontFamily = this.settings.fontFamily;

        document.getElementById('fontSizeSelect').value = this.settings.fontSize;
        document.getElementById('fontFamilySelect').value = this.settings.fontFamily;

        if (this.settings.theme === 'dark') {
            this.toggleTheme();
        }
    }
}

// Window reference for global access
let textEditor = null;