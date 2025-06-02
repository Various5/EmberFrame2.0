/**
 * EmberFrame V2 Desktop Core
 * Enhanced desktop environment with full functionality
 */

class EmberFrameDesktop {
    constructor() {
        this.windows = new Map();
        this.apps = new Map();
        this.windowZIndex = 100;
        this.activeWindow = null;
        this.user = null;
        this.apiBase = '/api';
        this.ws = null;
        this.clipboardData = null;
        this.currentPath = '';
        this.fileHistory = [];

        // Calculator state
        this.calcDisplay = '0';
        this.calcPrevious = null;
        this.calcOperation = null;
        this.calcWaitingForOperand = false;

        this.init();
    }

    async init() {
        console.log('🔥 Initializing EmberFrame Desktop...');

        try {
            await this.checkAuthentication();
            this.setupEventListeners();
            this.initializeApps();
            this.updateTime();
            this.setupWebSocket();
            this.loadUserPreferences();

            this.showNotification('Welcome to EmberFrame V2!', 'success');
            console.log('✅ Desktop initialized successfully');
        } catch (error) {
            console.error('❌ Desktop initialization failed:', error);
            this.showNotification('Desktop initialization failed', 'error');
        }
    }

    async checkAuthentication() {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/users/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.user = await response.json();
                console.log('✅ User authenticated:', this.user.username);
                this.updateUserDisplay();
            } else {
                throw new Error('Authentication failed');
            }
        } catch (error) {
            console.error('Authentication error:', error);
            localStorage.clear();
            window.location.href = '/login';
        }
    }

    updateUserDisplay() {
        const userIcon = document.getElementById('userIcon');
        if (userIcon && this.user) {
            userIcon.title = `Logged in as ${this.user.username}`;
        }
    }

    setupEventListeners() {
        // Desktop icons
        document.getElementById('desktopIcons').addEventListener('click', (e) => {
            const icon = e.target.closest('.desktop-icon');
            if (icon) {
                const appName = icon.dataset.app;
                this.openApp(appName);
            }
        });

        // Start button
        document.getElementById('startButton').addEventListener('click', () => {
            this.toggleStartMenu();
        });

        // Context menu
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.showContextMenu(e.clientX, e.clientY);
        });

        document.addEventListener('click', () => {
            this.hideContextMenu();
        });

        // Context menu actions
        document.getElementById('contextMenu').addEventListener('click', (e) => {
            const item = e.target.closest('.context-menu-item');
            if (item) {
                this.handleContextMenuAction(item.dataset.action);
            }
        });

        // System tray
        document.getElementById('userIcon').addEventListener('click', () => {
            this.showUserMenu();
        });

        document.getElementById('notificationIcon').addEventListener('click', () => {
            this.toggleNotificationCenter();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });

        // Window management
        document.addEventListener('click', (e) => {
            const window = e.target.closest('.window');
            if (window) {
                const windowId = window.id.replace('window-', '');
                this.focusWindow(windowId);
            }
        });

        // File drag and drop
        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        const desktop = document.getElementById('desktop');

        desktop.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });

        desktop.addEventListener('drop', (e) => {
            e.preventDefault();
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.handleFileUpload(files);
            }
        });
    }

    initializeApps() {
        // Register applications
        this.apps.set('filemanager', {
            name: 'File Manager',
            icon: 'fas fa-folder',
            component: 'FileManagerApp',
            shortcut: 'Ctrl+F'
        });

        this.apps.set('settings', {
            name: 'Settings',
            icon: 'fas fa-cog',
            component: 'SettingsApp',
            shortcut: 'Ctrl+S'
        });

        this.apps.set('texteditor', {
            name: 'Text Editor',
            icon: 'fas fa-edit',
            component: 'TextEditorApp',
            shortcut: 'Ctrl+E'
        });

        this.apps.set('calculator', {
            name: 'Calculator',
            icon: 'fas fa-calculator',
            component: 'CalculatorApp'
        });

        this.apps.set('terminal', {
            name: 'Terminal',
            icon: 'fas fa-terminal',
            component: 'TerminalApp',
            shortcut: 'Ctrl+T'
        });

        this.apps.set('imageviewer', {
            name: 'Image Viewer',
            icon: 'fas fa-image',
            component: 'ImageViewerApp'
        });

        console.log(`✅ Registered ${this.apps.size} applications`);
    }

    openApp(appName) {
        const app = this.apps.get(appName);
        if (!app) {
            this.showNotification(`App "${appName}" not found`, 'error');
            return;
        }

        // Check if app is already open
        if (this.windows.has(appName)) {
            this.focusWindow(appName);
            return;
        }

        this.createWindow(appName, app);
        console.log(`🚀 Opened app: ${app.name}`);
    }

    createWindow(appId, app) {
        const window = document.createElement('div');
        window.className = 'window';
        window.id = `window-${appId}`;
        window.style.zIndex = ++this.windowZIndex;

        // Smart positioning
        const windowCount = this.windows.size;
        const offset = windowCount * 30;
        const x = Math.min(50 + offset, window.innerWidth - 650);
        const y = Math.min(50 + offset, window.innerHeight - 450);

        window.style.left = x + 'px';
        window.style.top = y + 'px';
        window.style.width = '600px';
        window.style.height = '400px';

        window.innerHTML = `
            <div class="window-header">
                <div class="window-title">
                    <i class="${app.icon}"></i>
                    <span>${app.name}</span>
                </div>
                <div class="window-controls">
                    <div class="window-control minimize" onclick="desktop.minimizeWindow('${appId}')" title="Minimize"></div>
                    <div class="window-control maximize" onclick="desktop.toggleMaximize('${appId}')" title="Maximize"></div>
                    <div class="window-control close" onclick="desktop.closeWindow('${appId}')" title="Close"></div>
                </div>
            </div>
            <div class="window-content" id="content-${appId}">
                <div class="flex items-center justify-center" style="height: 100%;">
                    <div class="text-center">
                        <i class="fas fa-spinner fa-spin" style="font-size: 24px; margin-bottom: 10px; color: var(--primary-color);"></i>
                        <div>Loading ${app.name}...</div>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('desktop').appendChild(window);
        this.windows.set(appId, window);

        // Make window interactive
        this.makeDraggable(window);
        this.makeResizable(window);

        // Load app content
        setTimeout(() => this.loadAppContent(appId, app), 100);

        // Add to taskbar
        this.addToTaskbar(appId, app);

        // Focus window
        this.focusWindow(appId);

        // Animate window appearance
        window.style.opacity = '0';
        window.style.transform = 'scale(0.8)';
        requestAnimationFrame(() => {
            window.style.transition = 'all 0.3s ease';
            window.style.opacity = '1';
            window.style.transform = 'scale(1)';
        });
    }

    async loadAppContent(appId, app) {
        const content = document.getElementById(`content-${appId}`);

        try {
            switch (appId) {
                case 'filemanager':
                    content.innerHTML = this.getFileManagerHTML();
                    await this.initFileManager(appId);
                    break;
                case 'settings':
                    content.innerHTML = this.getSettingsHTML();
                    this.initSettings(appId);
                    break;
                case 'texteditor':
                    content.innerHTML = this.getTextEditorHTML();
                    this.initTextEditor(appId);
                    break;
                case 'calculator':
                    content.innerHTML = this.getCalculatorHTML();
                    this.initCalculator(appId);
                    break;
                case 'terminal':
                    content.innerHTML = this.getTerminalHTML();
                    this.initTerminal(appId);
                    break;
                case 'imageviewer':
                    content.innerHTML = this.getImageViewerHTML();
                    this.initImageViewer(appId);
                    break;
                default:
                    content.innerHTML = `
                        <div class="text-center p-20">
                            <h2>${app.name}</h2>
                            <p class="text-muted">This application is under development.</p>
                            <button class="toolbar-btn" onclick="desktop.closeWindow('${appId}')" style="margin-top: 20px;">
                                <i class="fas fa-times"></i> Close
                            </button>
                        </div>
                    `;
            }
        } catch (error) {
            console.error(`Error loading app ${appId}:`, error);
            content.innerHTML = `
                <div class="text-center p-20">
                    <h2>Error</h2>
                    <p class="text-muted">Failed to load ${app.name}</p>
                    <button class="toolbar-btn" onclick="desktop.closeWindow('${appId}')" style="margin-top: 20px;">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
            `;
        }
    }

    getFileManagerHTML() {
        return `
            <div class="file-manager" style="height: 100%;">
                <div class="file-toolbar">
                    <button class="toolbar-btn" onclick="desktop.fileManagerBack()" id="backBtn" disabled>
                        <i class="fas fa-arrow-left"></i> Back
                    </button>
                    <button class="toolbar-btn" onclick="desktop.fileManagerRefresh()">
                        <i class="fas fa-sync"></i> Refresh
                    </button>
                    <button class="toolbar-btn" onclick="desktop.fileManagerUpload()">
                        <i class="fas fa-upload"></i> Upload
                    </button>
                    <button class="toolbar-btn" onclick="desktop.fileManagerNewFolder()">
                        <i class="fas fa-folder-plus"></i> New Folder
                    </button>
                    <div style="flex: 1; margin: 0 10px;">
                        <input type="text" id="pathInput" value="/" readonly style="width: 100%; background: var(--glass-bg); border: 1px solid var(--border-color); padding: 6px 10px; border-radius: 4px; color: var(--text-color);">
                    </div>
                    <input type="file" id="fileInput" multiple style="display: none;">
                </div>
                <div class="file-grid" id="fileGrid" style="height: calc(100% - 80px);">
                    <div style="text-align: center; color: #888; grid-column: 1/-1; padding: 40px;">
                        <i class="fas fa-spinner fa-spin" style="font-size: 24px; margin-bottom: 10px;"></i>
                        <div>Loading files...</div>
                    </div>
                </div>
            </div>
        `;
    }

    getSettingsHTML() {
        return `
            <div style="padding: 20px; height: 100%; overflow-y: auto;">
                <h2 style="margin-bottom: 20px; color: var(--primary-color);">Settings</h2>
                
                <div style="margin-bottom: 30px;">
                    <h3 style="margin-bottom: 15px;">Appearance</h3>
                    <div style="margin: 10px 0;">
                        <label for="themeSelect" style="display: block; margin-bottom: 5px;">Theme:</label>
                        <select id="themeSelect" style="width: 200px; padding: 8px; background: var(--window-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 4px;">
                            <option value="ember-blue">Ember Blue</option>
                            <option value="ember-purple">Ember Purple</option>
                            <option value="ember-green">Ember Green</option>
                            <option value="ember-dark">Ember Dark</option>
                        </select>
                    </div>
                </div>
                
                <div style="margin-bottom: 30px;">
                    <h3 style="margin-bottom: 15px;">User Information</h3>
                    <div style="background: var(--glass-bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border-color);">
                        <div style="margin: 10px 0;">
                            <strong>Username:</strong> <span id="userUsername">${this.user?.username || 'N/A'}</span>
                        </div>
                        <div style="margin: 10px 0;">
                            <strong>Email:</strong> <span id="userEmail">${this.user?.email || 'N/A'}</span>
                        </div>
                        <div style="margin: 10px 0;">
                            <strong>Account Type:</strong> <span>${this.user?.is_admin ? 'Administrator' : 'User'}</span>
                        </div>
                        <div style="margin: 10px 0;">
                            <strong>Storage Used:</strong> <span>${this.formatFileSize(this.user?.storage_used || 0)}</span> / <span>${this.formatFileSize(this.user?.storage_quota || 0)}</span>
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 30px;">
                    <h3 style="margin-bottom: 15px;">Preferences</h3>
                    <div style="margin: 15px 0;">
                        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                            <input type="checkbox" id="notificationsEnabled" checked>
                            <span>Enable notifications</span>
                        </label>
                    </div>
                    <div style="margin: 15px 0;">
                        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                            <input type="checkbox" id="soundEnabled" checked>
                            <span>Enable sound effects</span>
                        </label>
                    </div>
                </div>
                
                <div style="border-top: 1px solid var(--border-color); padding-top: 20px;">
                    <button class="toolbar-btn" onclick="desktop.saveSettings()" style="background: var(--success-color); margin-right: 10px;">
                        <i class="fas fa-save"></i> Save Settings
                    </button>
                    <button class="toolbar-btn" onclick="desktop.logout()" style="background: var(--error-color);">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </button>
                </div>
            </div>
        `;
    }

    getTextEditorHTML() {
        return `
            <div style="height: 100%; display: flex; flex-direction: column;">
                <div style="padding: 10px; border-bottom: 1px solid var(--border-color); display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="toolbar-btn" onclick="desktop.textEditorNew()">
                        <i class="fas fa-file"></i> New
                    </button>
                    <button class="toolbar-btn" onclick="desktop.textEditorOpen()">
                        <i class="fas fa-folder-open"></i> Open
                    </button>
                    <button class="toolbar-btn" onclick="desktop.textEditorSave()">
                        <i class="fas fa-save"></i> Save
                    </button>
                    <div style="border-left: 1px solid var(--border-color); margin: 0 5px;"></div>
                    <button class="toolbar-btn" onclick="desktop.textEditorUndo()">
                        <i class="fas fa-undo"></i> Undo
                    </button>
                    <button class="toolbar-btn" onclick="desktop.textEditorRedo()">
                        <i class="fas fa-redo"></i> Redo
                    </button>
                    <div style="flex: 1;"></div>
                    <select id="fontSizeSelect" style="padding: 4px; background: var(--window-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 4px;">
                        <option value="12">12px</option>
                        <option value="14" selected>14px</option>
                        <option value="16">16px</option>
                        <option value="18">18px</option>
                        <option value="20">20px</option>
                    </select>
                </div>
                <textarea id="textEditor" style="flex: 1; background: var(--window-bg); color: var(--text-color); border: none; padding: 15px; font-family: 'Courier New', monospace; font-size: 14px; resize: none; outline: none; line-height: 1.5;" placeholder="Start typing..."></textarea>
                <div style="padding: 8px 15px; border-top: 1px solid var(--border-color); font-size: 0.8rem; color: var(--text-color); opacity: 0.7; display: flex; justify-content: space-between;">
                    <span>Lines: <span id="lineCount">1</span> | Characters: <span id="charCount">0</span></span>
                    <span id="editorStatus">Ready</span>
                </div>
            </div>
        `;
    }

    getCalculatorHTML() {
        return `
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 20px; max-width: 350px; margin: 0 auto;">
                <div id="calcDisplay" style="grid-column: 1/-1; background: var(--glass-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; text-align: right; font-size: 28px; margin-bottom: 15px; font-family: 'Courier New', monospace; word-break: break-all; min-height: 60px; display: flex; align-items: center; justify-content: flex-end;">${this.calcDisplay}</div>
                
                <button class="calc-btn" onclick="desktop.calcClear()" style="background: var(--error-color); font-weight: bold;">C</button>
                <button class="calc-btn" onclick="desktop.calcClearEntry()" style="background: var(--warning-color);">CE</button>
                <button class="calc-btn" onclick="desktop.calcOperation('/')" style="background: var(--secondary-color);">÷</button>
                <button class="calc-btn" onclick="desktop.calcBackspace()" style="background: var(--warning-color);">⌫</button>
                
                <button class="calc-btn" onclick="desktop.calcInput('7')">7</button>
                <button class="calc-btn" onclick="desktop.calcInput('8')">8</button>
                <button class="calc-btn" onclick="desktop.calcInput('9')">9</button>
                <button class="calc-btn" onclick="desktop.calcOperation('*')" style="background: var(--secondary-color);">×</button>
                
                <button class="calc-btn" onclick="desktop.calcInput('4')">4</button>
                <button class="calc-btn" onclick="desktop.calcInput('5')">5</button>
                <button class="calc-btn" onclick="desktop.calcInput('6')">6</button>
                <button class="calc-btn" onclick="desktop.calcOperation('-')" style="background: var(--secondary-color);">-</button>
                
                <button class="calc-btn" onclick="desktop.calcInput('1')">1</button>
                <button class="calc-btn" onclick="desktop.calcInput('2')">2</button>
                <button class="calc-btn" onclick="desktop.calcInput('3')">3</button>
                <button class="calc-btn" onclick="desktop.calcOperation('+')" style="background: var(--secondary-color); grid-row: span 2;">+</button>
                
                <button class="calc-btn" onclick="desktop.calcInput('0')" style="grid-column: span 2;">0</button>
                <button class="calc-btn" onclick="desktop.calcInput('.')">.</button>
                
                <button class="calc-btn" onclick="desktop.calcEquals()" style="background: var(--success-color); grid-column: span 3; font-weight: bold;">=</button>
            </div>
            <style>
                .calc-btn {
                    padding: 15px;
                    background: var(--primary-color);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-weight: 500;
                    border: 1px solid rgba(255,255,255,0.1);
                }
                .calc-btn:hover {
                    opacity: 0.8;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }
                .calc-btn:active {
                    transform: translateY(0);
                }
            </style>
        `;
    }

    getTerminalHTML() {
        return `
            <div style="height: 100%; display: flex; flex-direction: column; background: #000; color: #0f0; font-family: 'Courier New', monospace;">
                <div style="padding: 10px; border-bottom: 1px solid #333; background: #111;">
                    <strong>EmberFrame Terminal v2.0</strong>
                </div>
                <div id="terminalOutput" style="flex: 1; padding: 10px; overflow-y: auto; font-size: 14px; line-height: 1.4;">
                    <div>Welcome to EmberFrame Terminal!</div>
                    <div>Type 'help' for available commands.</div>
                    <div style="margin-top: 10px;"></div>
                </div>
                <div style="padding: 10px; border-top: 1px solid #333; display: flex; align-items: center;">
                    <span style="color: #0f0; margin-right: 5px;">$</span>
                    <input type="text" id="terminalInput" style="flex: 1; background: transparent; border: none; color: #0f0; font-family: inherit; font-size: 14px; outline: none;" placeholder="Enter command..." autofocus>
                </div>
            </div>
        `;
    }

    getImageViewerHTML() {
        return `
            <div style="height: 100%; display: flex; flex-direction: column;">
                <div style="padding: 10px; border-bottom: 1px solid var(--border-color);">
                    <button class="toolbar-btn" onclick="desktop.imageViewerOpen()">
                        <i class="fas fa-folder-open"></i> Open Image
                    </button>
                    <button class="toolbar-btn" onclick="desktop.imageViewerPrevious()" id="prevBtn" disabled>
                        <i class="fas fa-chevron-left"></i> Previous
                    </button>
                    <button class="toolbar-btn" onclick="desktop.imageViewerNext()" id="nextBtn" disabled>
                        <i class="fas fa-chevron-right"></i> Next
                    </button>
                    <input type="file" id="imageInput" accept="image/*" style="display: none;">
                </div>
                <div id="imageContainer" style="flex: 1; display: flex; align-items: center; justify-content: center; background: #000; position: relative; overflow: hidden;">
                    <div style="text-align: center; color: #888;">
                        <i class="fas fa-image" style="font-size: 48px; margin-bottom: 15px;"></i>
                        <div>No image loaded</div>
                        <button class="toolbar-btn" onclick="desktop.imageViewerOpen()" style="margin-top: 15px;">
                            <i class="fas fa-folder-open"></i> Open Image
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // File Manager Methods
    async initFileManager(appId) {
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${this.apiBase}/files/?path=${encodeURIComponent(this.currentPath)}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.displayFiles(data.files || []);
                this.updatePathDisplay();
                this.updateBackButton();
            } else {
                throw new Error('Failed to load files');
            }
        } catch (error) {
            console.error('File manager error:', error);
            document.getElementById('fileGrid').innerHTML = '<div style="text-align: center; color: var(--error-color); grid-column: 1/-1; padding: 40px;">Error loading files</div>';
        }
    }

    displayFiles(files) {
        const fileGrid = document.getElementById('fileGrid');
        if (!files || files.length === 0) {
            fileGrid.innerHTML = '<div style="text-align: center; color: #888; grid-column: 1/-1; padding: 40px;"><i class="fas fa-folder-open" style="font-size: 48px; margin-bottom: 15px; opacity: 0.5;"></i><div>No files found</div></div>';
            return;
        }

        fileGrid.innerHTML = files.map(file => `
            <div class="file-item" data-file="${file.name}" data-type="${file.type}" ondblclick="desktop.fileDoubleClick('${file.name}', '${file.type}')">
                <div class="file-icon">
                    <i class="fas ${this.getFileIcon(file)}"></i>
                </div>
                <div class="file-name" title="${file.name}">${this.truncateFileName(file.name)}</div>
                ${file.size ? `<div style="font-size: 0.7rem; opacity: 0.7; margin-top: 2px;">${this.formatFileSize(file.size)}</div>` : ''}
            </div>
        `).join('');
    }

    getFileIcon(file) {
        if (file.type === 'folder') return 'fa-folder';

        const ext = file.name.split('.').pop()?.toLowerCase() || '';
        const iconMap = {
            'txt': 'fa-file-text',
            'md': 'fa-file-text',
            'doc': 'fa-file-word',
            'docx': 'fa-file-word',
            'pdf': 'fa-file-pdf',
            'jpg': 'fa-file-image',
            'jpeg': 'fa-file-image',
            'png': 'fa-file-image',
            'gif': 'fa-file-image',
            'svg': 'fa-file-image',
            'mp3': 'fa-file-audio',
            'wav': 'fa-file-audio',
            'mp4': 'fa-file-video',
            'avi': 'fa-file-video',
            'zip': 'fa-file-archive',
            'rar': 'fa-file-archive',
            'js': 'fa-file-code',
            'html': 'fa-file-code',
            'css': 'fa-file-code',
            'py': 'fa-file-code',
            'json': 'fa-file-code'
        };

        return iconMap[ext] || 'fa-file';
    }

    truncateFileName(name, maxLength = 12) {
        if (name.length <= maxLength) return name;
        const ext = name.split('.').pop();
        const baseName = name.substring(0, name.lastIndexOf('.'));
        const truncatedBase = baseName.substring(0, maxLength - ext.length - 4);
        return `${truncatedBase}...${ext}`;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
    }

    fileDoubleClick(fileName, fileType) {
        if (fileType === 'folder') {
            this.navigateToFolder(fileName);
        } else {
            this.openFile(fileName);
        }
    }

    navigateToFolder(folderName) {
        this.fileHistory.push(this.currentPath);
        this.currentPath = this.currentPath === '/' ? `/${folderName}` : `${this.currentPath}/${folderName}`;
        this.initFileManager('filemanager');
    }

    fileManagerBack() {
        if (this.fileHistory.length > 0) {
            this.currentPath = this.fileHistory.pop();
            this.initFileManager('filemanager');
        }
    }

    updatePathDisplay() {
        const pathInput = document.getElementById('pathInput');
        if (pathInput) {
            pathInput.value = this.currentPath || '/';
        }
    }

    updateBackButton() {
        const backBtn = document.getElementById('backBtn');
        if (backBtn) {
            backBtn.disabled = this.fileHistory.length === 0;
        }
    }

    async fileManagerRefresh() {
        await this.initFileManager('filemanager');
        this.showNotification('Files refreshed', 'success');
    }

    fileManagerUpload() {
        document.getElementById('fileInput').click();
        document.getElementById('fileInput').onchange = (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                this.handleFileUpload(files);
            }
        };
    }

    async handleFileUpload(files) {
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });
        formData.append('path', this.currentPath);

        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${this.apiBase}/files/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification(`Uploaded ${result.count} file(s)`, 'success');
                await this.fileManagerRefresh();
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Failed to upload files', 'error');
        }
    }

    fileManagerNewFolder() {
        const name = prompt('Enter folder name:');
        if (name && name.trim()) {
            this.createFolder(name.trim());
        }
    }

    async createFolder(name) {
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${this.apiBase}/files/folder`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `path=${encodeURIComponent(this.currentPath)}&name=${encodeURIComponent(name)}`
            });

            if (response.ok) {
                this.showNotification(`Created folder: ${name}`, 'success');
                await this.fileManagerRefresh();
            } else {
                throw new Error('Failed to create folder');
            }
        } catch (error) {
            console.error('Create folder error:', error);
            this.showNotification('Failed to create folder', 'error');
        }
    }

    // Window Management
    makeDraggable(windowEl) {
        const header = windowEl.querySelector('.window-header');
        let isDragging = false;
        let startX, startY, startLeft, startTop;

        header.addEventListener('mousedown', (e) => {
            if (e.target.closest('.window-control')) return; // Don't drag on controls

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = parseInt(windowEl.style.left);
            startTop = parseInt(windowEl.style.top);

            const windowId = windowEl.id.replace('window-', '');
            this.focusWindow(windowId);

            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            const newLeft = Math.max(0, Math.min(startLeft + deltaX, window.innerWidth - windowEl.offsetWidth));
            const newTop = Math.max(0, Math.min(startTop + deltaY, window.innerHeight - windowEl.offsetHeight - 60));

            windowEl.style.left = newLeft + 'px';
            windowEl.style.top = newTop + 'px';
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
            document.body.style.userSelect = '';
        });
    }

    makeResizable(windowEl) {
        const resizeHandle = document.createElement('div');
        resizeHandle.style.cssText = `
            position: absolute;
            bottom: 0;
            right: 0;
            width: 20px;
            height: 20px;
            cursor: se-resize;
            background: transparent;
            z-index: 10;
        `;
        windowEl.appendChild(resizeHandle);

        let isResizing = false;
        let startX, startY, startWidth, startHeight;

        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = parseInt(windowEl.style.width);
            startHeight = parseInt(windowEl.style.height);
            e.stopPropagation();
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            const newWidth = Math.max(300, startWidth + deltaX);
            const newHeight = Math.max(200, startHeight + deltaY);

            windowEl.style.width = newWidth + 'px';
            windowEl.style.height = newHeight + 'px';
        });

        document.addEventListener('mouseup', () => {
            isResizing = false;
            document.body.style.userSelect = '';
        });
    }

    focusWindow(windowId) {
        const window = this.windows.get(windowId);
        if (window && !window.classList.contains('minimized')) {
            window.style.zIndex = ++this.windowZIndex;
            this.activeWindow = windowId;

            // Update taskbar
            document.querySelectorAll('.taskbar-item').forEach(item => {
                item.classList.remove('active');
            });

            const taskbarItem = document.querySelector(`[data-window="${windowId}"]`);
            if (taskbarItem) {
                taskbarItem.classList.add('active');
            }
        }
    }

    closeWindow(windowId) {
        const window = this.windows.get(windowId);
        if (window) {
            // Animate window closing
            window.style.transition = 'all 0.3s ease';
            window.style.opacity = '0';
            window.style.transform = 'scale(0.8)';

            setTimeout(() => {
                window.remove();
                this.windows.delete(windowId);

                // Remove from taskbar
                const taskbarItem = document.querySelector(`[data-window="${windowId}"]`);
                if (taskbarItem) {
                    taskbarItem.remove();
                }

                console.log(`🗑️ Closed app: ${windowId}`);
            }, 300);
        }
    }

    minimizeWindow(windowId) {
        const window = this.windows.get(windowId);
        if (window) {
            window.classList.add('minimized');

            // Update taskbar item
            const taskbarItem = document.querySelector(`[data-window="${windowId}"]`);
            if (taskbarItem) {
                taskbarItem.classList.remove('active');
                taskbarItem.onclick = () => {
                    window.classList.remove('minimized');
                    this.focusWindow(windowId);
                    taskbarItem.onclick = null;
                };
            }
        }
    }

    toggleMaximize(windowId) {
        const window = this.windows.get(windowId);
        if (window) {
            window.classList.toggle('maximized');
        }
    }

    addToTaskbar(windowId, app) {
        const taskbarItems = document.getElementById('taskbarItems');
        const item = document.createElement('div');
        item.className = 'taskbar-item';
        item.dataset.window = windowId;
        item.innerHTML = `
            <i class="${app.icon}"></i>
            <span style="margin-left: 8px;">${app.name}</span>
        `;

        item.addEventListener('click', () => {
            if (this.windows.get(windowId).classList.contains('minimized')) {
                this.windows.get(windowId).classList.remove('minimized');
            }
            this.focusWindow(windowId);
        });

        taskbarItems.appendChild(item);
    }

    // System Methods
    showContextMenu(x, y) {
        const contextMenu = document.getElementById('contextMenu');
        contextMenu.style.display = 'block';

        // Ensure menu doesn't go off screen
        const menuWidth = contextMenu.offsetWidth;
        const menuHeight = contextMenu.offsetHeight;
        const maxX = window.innerWidth - menuWidth;
        const maxY = window.innerHeight - menuHeight;

        contextMenu.style.left = Math.min(x, maxX) + 'px';
        contextMenu.style.top = Math.min(y, maxY) + 'px';
    }

    hideContextMenu() {
        document.getElementById('contextMenu').style.display = 'none';
    }

    handleContextMenuAction(action) {
        switch (action) {
            case 'refresh':
                window.location.reload();
                break;
            case 'paste':
                if (this.clipboardData) {
                    this.showNotification('Paste functionality coming soon!');
                }
                break;
            case 'properties':
                this.showSystemProperties();
                break;
        }
        this.hideContextMenu();
    }

    showSystemProperties() {
        this.showNotification('System Properties: EmberFrame V2 Desktop');
    }

    showUserMenu() {
        const menu = `
            <div style="position: fixed; top: 20px; right: 20px; background: var(--window-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 15px; z-index: 2000; min-width: 200px; backdrop-filter: blur(20px);">
                <div style="margin-bottom: 15px; text-align: center;">
                    <i class="fas fa-user-circle" style="font-size: 48px; color: var(--primary-color);"></i>
                    <div style="margin-top: 10px; font-weight: bold;">${this.user?.username || 'User'}</div>
                    <div style="font-size: 0.8rem; opacity: 0.7;">${this.user?.email || ''}</div>
                </div>
                <div style="border-top: 1px solid var(--border-color); padding-top: 15px;">
                    <button class="toolbar-btn" onclick="desktop.openApp('settings')" style="width: 100%; margin-bottom: 10px;">
                        <i class="fas fa-cog"></i> Settings
                    </button>
                    <button class="toolbar-btn" onclick="desktop.logout()" style="width: 100%; background: var(--error-color);">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </button>
                </div>
            </div>
        `;

        // Remove existing menu
        const existingMenu = document.querySelector('.user-menu');
        if (existingMenu) {
            existingMenu.remove();
        }

        const menuDiv = document.createElement('div');
        menuDiv.className = 'user-menu';
        menuDiv.innerHTML = menu;
        document.body.appendChild(menuDiv);

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (menuDiv.parentElement) {
                menuDiv.remove();
            }
        }, 5000);

        // Hide on click outside
        document.addEventListener('click', function hideUserMenu(e) {
            if (!menuDiv.contains(e.target) && !document.getElementById('userIcon').contains(e.target)) {
                menuDiv.remove();
                document.removeEventListener('click', hideUserMenu);
            }
        });
    }

    toggleStartMenu() {
        // TODO: Implement start menu
        this.showNotification('Start menu coming soon!');
    }

    toggleNotificationCenter() {
        // TODO: Implement notification center
        this.showNotification('Notification center coming soon!');
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notificationContainer');
        const notification = document.createElement('div');
        const id = Date.now();

        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                <span style="flex: 1;">${message}</span>
                <button class="notification-close" onclick="this.closest('.notification').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        container.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.animation = 'slideOutRight 0.3s ease-out forwards';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);

        console.log(`📢 Notification: ${message}`);
    }

    updateTime() {
        const timeDisplay = document.getElementById('timeDisplay');
        const now = new Date();

        const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const date = now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });

        timeDisplay.innerHTML = `
            <div class="time">${time}</div>
            <div class="date" style="font-size: 0.7rem; opacity: 0.8;">${date}</div>
        `;

        setTimeout(() => this.updateTime(), 1000);
    }

    setupWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/notifications`);

            this.ws.onopen = () => {
                console.log('🔌 WebSocket connected');
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.showNotification(data.message, data.type || 'info');
                } catch (error) {
                    console.error('WebSocket message error:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.setupWebSocket(), 5000);
            };
        } catch (error) {
            console.error('WebSocket setup failed:', error);
        }
    }

    handleKeyboardShortcuts(e) {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key.toLowerCase()) {
                case 'f':
                    e.preventDefault();
                    this.openApp('filemanager');
                    break;
                case 't':
                    e.preventDefault();
                    this.openApp('terminal');
                    break;
                case 's':
                    e.preventDefault();
                    this.openApp('settings');
                    break;
                case 'e':
                    e.preventDefault();
                    this.openApp('texteditor');
                    break;
            }
        }

        // Alt+Tab for window switching
        if (e.altKey && e.key === 'Tab') {
            e.preventDefault();
            this.switchWindow();
        }
    }

    switchWindow() {
        const windows = Array.from(this.windows.keys());
        if (windows.length === 0) return;

        const currentIndex = windows.indexOf(this.activeWindow);
        const nextIndex = (currentIndex + 1) % windows.length;
        this.focusWindow(windows[nextIndex]);
    }

    async loadUserPreferences() {
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${this.apiBase}/users/preferences`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const preferences = await response.json();
                this.applyPreferences(preferences);
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
    }

    applyPreferences(preferences) {
        // Apply theme
        if (preferences.theme) {
            document.body.className = preferences.theme;
        }

        // Apply other preferences
        console.log('✅ User preferences applied');
    }

    async saveSettings() {
        try {
            const preferences = {
                theme: document.getElementById('themeSelect')?.value || 'ember-blue',
                notifications_enabled: document.getElementById('notificationsEnabled')?.checked || true,
                sound_enabled: document.getElementById('soundEnabled')?.checked || true
            };

            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${this.apiBase}/users/preferences`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(preferences)
            });

            if (response.ok) {
                this.showNotification('Settings saved successfully!', 'success');
                this.applyPreferences(preferences);
            } else {
                throw new Error('Failed to save settings');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Failed to save settings', 'error');
        }
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            localStorage.clear();
            if (this.ws) {
                this.ws.close();
            }
            this.showNotification('Logging out...', 'success');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1000);
        }
    }

    // Calculator Methods
    initCalculator(appId) {
        this.calcDisplay = '0';
        this.calcPrevious = null;
        this.calcOperation = null;
        this.calcWaitingForOperand = false;
        this.updateCalcDisplay();
    }

    calcInput(value) {
        const display = document.getElementById('calcDisplay');

        if (this.calcWaitingForOperand) {
            this.calcDisplay = value;
            this.calcWaitingForOperand = false;
        } else {
            this.calcDisplay = this.calcDisplay === '0' ? value : this.calcDisplay + value;
        }

        this.updateCalcDisplay();
    }

    calcOperation(nextOperation) {
        const inputValue = parseFloat(this.calcDisplay);

        if (this.calcPrevious === null) {
            this.calcPrevious = inputValue;
        } else if (this.calcOperation) {
            const currentValue = this.calcPrevious || 0;
            const newValue = this.calculate(currentValue, inputValue, this.calcOperation);

            this.calcDisplay = String(newValue);
            this.calcPrevious = newValue;
            this.updateCalcDisplay();
        }

        this.calcWaitingForOperand = true;
        this.calcOperation = nextOperation;
    }

    calcEquals() {
        const inputValue = parseFloat(this.calcDisplay);

        if (this.calcPrevious !== null && this.calcOperation) {
            const newValue = this.calculate(this.calcPrevious, inputValue, this.calcOperation);
            this.calcDisplay = String(newValue);
            this.calcPrevious = null;
            this.calcOperation = null;
            this.calcWaitingForOperand = true;
            this.updateCalcDisplay();
        }
    }

    calcClear() {
        this.calcDisplay = '0';
        this.calcPrevious = null;
        this.calcOperation = null;
        this.calcWaitingForOperand = false;
        this.updateCalcDisplay();
    }

    calcClearEntry() {
        this.calcDisplay = '0';
        this.updateCalcDisplay();
    }

    calcBackspace() {
        if (this.calcDisplay.length > 1) {
            this.calcDisplay = this.calcDisplay.slice(0, -1);
        } else {
            this.calcDisplay = '0';
        }
        this.updateCalcDisplay();
    }

    calculate(firstOperand, secondOperand, operation) {
        switch (operation) {
            case '+':
                return firstOperand + secondOperand;
            case '-':
                return firstOperand - secondOperand;
            case '*':
                return firstOperand * secondOperand;
            case '/':
                return secondOperand !== 0 ? firstOperand / secondOperand : 0;
            default:
                return secondOperand;
        }
    }

    updateCalcDisplay() {
        const display = document.getElementById('calcDisplay');
        if (display) {
            display.textContent = this.calcDisplay;
        }
    }

    // Text Editor Methods
    initTextEditor(appId) {
        const textarea = document.getElementById('textEditor');
        const fontSizeSelect = document.getElementById('fontSizeSelect');

        if (textarea) {
            textarea.addEventListener('input', () => {
                this.updateTextEditorStats();
            });
        }

        if (fontSizeSelect) {
            fontSizeSelect.addEventListener('change', (e) => {
                if (textarea) {
                    textarea.style.fontSize = e.target.value + 'px';
                }
            });
        }

        this.updateTextEditorStats();
    }

    updateTextEditorStats() {
        const textarea = document.getElementById('textEditor');
        const lineCount = document.getElementById('lineCount');
        const charCount = document.getElementById('charCount');

        if (textarea && lineCount && charCount) {
            const lines = textarea.value.split('\n').length;
            const chars = textarea.value.length;

            lineCount.textContent = lines;
            charCount.textContent = chars;
        }
    }

    textEditorNew() {
        const textarea = document.getElementById('textEditor');
        if (textarea && (textarea.value === '' || confirm('Clear current document?'))) {
            textarea.value = '';
            this.updateTextEditorStats();
            this.showNotification('New document created', 'success');
        }
    }

    textEditorSave() {
        const textarea = document.getElementById('textEditor');
        if (textarea) {
            const content = textarea.value;
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'document.txt';
            a.click();
            URL.revokeObjectURL(url);
            this.showNotification('Document saved', 'success');
        }
    }

    textEditorOpen() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.md';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const textarea = document.getElementById('textEditor');
                    if (textarea) {
                        textarea.value = e.target.result;
                        this.updateTextEditorStats();
                        this.showNotification('File opened', 'success');
                    }
                };
                reader.readAsText(file);
            }
        };
        input.click();
    }
}

// Initialize desktop
let desktop;
document.addEventListener('DOMContentLoaded', () => {
    desktop = new EmberFrameDesktop();
    window.desktop = desktop; // Make globally accessible
});

// Add global CSS animations
const styleSheet = document.createElement('style');
styleSheet.textContent = `
    @keyframes slideOutRight {
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
`;
document.head.appendChild(styleSheet);