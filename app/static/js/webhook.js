// Webhook configuration functionality
export class WebhookManager {
    constructor() {
        this.currentWebhookUrl = null;
        this.init();
    }

    init() {
        // Check for webhook URL in current page URL
        this.loadWebhookFromURL();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Update UI based on webhook status
        this.updateUI();
    }

    setupEventListeners() {
        const configureBtn = document.getElementById('configure-webhook-button');
        const closeBtn = document.getElementById('webhook-modal-close-button');
        const saveBtn = document.getElementById('save-webhook-button');
        const clearBtn = document.getElementById('clear-webhook-button');
        const copyBtn = document.getElementById('copy-url-button');
        const useUrlBtn = document.getElementById('use-url-button');
        const copyCurrentBtn = document.getElementById('copy-current-url-button');
        const generateNewBtn = document.getElementById('generate-new-webhook-button');
        const overlay = document.getElementById('webhook-modal-overlay');

        if (configureBtn) {
            configureBtn.addEventListener('click', () => this.openWebhookModal());
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeWebhookModal());
        }
        
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveWebhook());
        }
        
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearWebhook());
        }
        
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyShareableURL());
        }
        
        if (useUrlBtn) {
            useUrlBtn.addEventListener('click', () => this.useShareableURL());
        }
        
        if (copyCurrentBtn) {
            copyCurrentBtn.addEventListener('click', () => this.copyCurrentURL());
        }
        
        if (generateNewBtn) {
            generateNewBtn.addEventListener('click', () => this.generateNewWebhook());
        }
        
        if (overlay) {
            overlay.addEventListener('click', (event) => {
                if (event.target === overlay) {
                    this.closeWebhookModal();
                }
            });
        }
    }

    loadWebhookFromURL() {
        // Check URL fragment first (more secure)
        const fragment = window.location.hash;
        if (fragment.startsWith('#webhook=')) {
            const encodedWebhook = fragment.substring(9); // Remove '#webhook='
            this.currentWebhookUrl = this.decodeWebhookURL(encodedWebhook);
            return;
        }

        // Fallback to URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const encodedWebhook = urlParams.get('webhook');
        if (encodedWebhook) {
            this.currentWebhookUrl = this.decodeWebhookURL(encodedWebhook);
        }
    }

    encodeWebhookURL(webhookUrl) {
        try {
            // Use URL-safe base64 encoding
            return btoa(webhookUrl)
                .replace(/\+/g, '-')
                .replace(/\//g, '_')
                .replace(/=/g, '');
        } catch (error) {
            console.error('Error encoding webhook URL:', error);
            return null;
        }
    }

    decodeWebhookURL(encodedUrl) {
        try {
            // Reverse URL-safe base64 encoding
            let base64 = encodedUrl
                .replace(/-/g, '+')
                .replace(/_/g, '/');
            
            // Add padding if needed
            while (base64.length % 4) {
                base64 += '=';
            }
            
            return atob(base64);
        } catch (error) {
            console.error('Error decoding webhook URL:', error);
            return null;
        }
    }

    validateWebhookURL(url) {
        try {
            const urlObj = new URL(url);
            return (urlObj.hostname === 'discord.com' || urlObj.hostname === 'discordapp.com') && 
                   urlObj.pathname.startsWith('/api/webhooks/');
        } catch (error) {
            return false;
        }
    }

    openWebhookModal() {
        const overlay = document.getElementById('webhook-modal-overlay');
        const configMode = document.getElementById('webhook-config-mode');
        const connectedMode = document.getElementById('webhook-connected-mode');
        const input = document.getElementById('webhook-url-input');
        const mainContent = document.getElementById('main-content');
        
        if (this.currentWebhookUrl) {
            // Show connected mode
            if (configMode) configMode.style.display = 'none';
            if (connectedMode) connectedMode.style.display = 'block';
        } else {
            // Show configuration mode
            if (configMode) configMode.style.display = 'block';
            if (connectedMode) connectedMode.style.display = 'none';
            
            // Pre-fill with current webhook if available (shouldn't happen in this branch, but just in case)
            if (input) {
                input.value = this.currentWebhookUrl || '';
            }
        }
        
        if (overlay) {
            // Set main content as inert to trap focus in modal
            if (mainContent) {
                mainContent.setAttribute('inert', '');
                mainContent.setAttribute('aria-hidden', 'true');
            }
            
            // Also set body class to prevent scrolling and additional focus issues
            document.body.classList.add('modal-open');
            
            overlay.classList.add('active');
            
            // Use requestAnimationFrame to reliably set focus
            requestAnimationFrame(() => {
                if (!this.currentWebhookUrl && input) {
                    input.focus();
                } else {
                    // Focus on close button if in connected mode
                    const closeBtn = document.getElementById('webhook-modal-close-button');
                    if (closeBtn) closeBtn.focus();
                }
            });
        }
    }

    closeWebhookModal() {
        const overlay = document.getElementById('webhook-modal-overlay');
        const shareableSection = document.getElementById('shareable-url-section');
        const useBtn = document.getElementById('use-url-button');
        const mainContent = document.getElementById('main-content');
        
        if (overlay) {
            overlay.classList.remove('active');
        }
        
        if (shareableSection) {
            shareableSection.style.display = 'none';
        }
        
        // Reset the "Use This Link" button state when closing modal
        if (useBtn) {
            useBtn.textContent = 'Use This Link';
            useBtn.disabled = false;
        }
        
        // Remove inert attribute to restore focus to main content
        if (mainContent) {
            mainContent.removeAttribute('inert');
            mainContent.removeAttribute('aria-hidden');
        }
        
        // Remove body class
        document.body.classList.remove('modal-open');
    }

    saveWebhook() {
        const input = document.getElementById('webhook-url-input');
        const shareableSection = document.getElementById('shareable-url-section');
        const shareableOutput = document.getElementById('shareable-url-output');
        
        if (!input) return;
        
        const webhookUrl = input.value.trim();
        
        if (!webhookUrl) {
            alert('Please enter a webhook URL');
            return;
        }
        
        if (!this.validateWebhookURL(webhookUrl)) {
            alert('Please enter a valid Discord webhook URL');
            return;
        }
        
        // Save the webhook URL
        this.currentWebhookUrl = webhookUrl;
        
        // Generate shareable URL
        const encodedWebhook = this.encodeWebhookURL(webhookUrl);
        if (encodedWebhook) {
            const currentOrigin = window.location.origin;
            const currentPath = window.location.pathname;
            const shareableUrl = `${currentOrigin}${currentPath}#webhook=${encodedWebhook}`;
            
            if (shareableOutput) {
                shareableOutput.value = shareableUrl;
            }
            
            if (shareableSection) {
                shareableSection.style.display = 'block';
            }
        }
        
        // Update UI
        this.updateUI();
    }

    clearWebhook() {
        this.currentWebhookUrl = null;
        
        const input = document.getElementById('webhook-url-input');
        const shareableSection = document.getElementById('shareable-url-section');
        
        if (input) {
            input.value = '';
        }
        
        if (shareableSection) {
            shareableSection.style.display = 'none';
        }
        
        // Clear URL fragment
        if (window.location.hash.startsWith('#webhook=')) {
            history.replaceState(null, null, window.location.pathname + window.location.search);
        }
        
        this.updateUI();
    }

    async copyShareableURL() {
        const output = document.getElementById('shareable-url-output');
        const copyBtn = document.getElementById('copy-url-button');
        
        if (!output) return;
        
        try {
            await navigator.clipboard.writeText(output.value);
            
            if (copyBtn) {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }
        } catch (error) {
            // Fallback for older browsers
            output.select();
            document.execCommand('copy');
            
            if (copyBtn) {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }
        }
    }

    useShareableURL() {
        const output = document.getElementById('shareable-url-output');
        const useBtn = document.getElementById('use-url-button');
        
        if (!output || !output.value) return;
        
        // Update button to show loading state
        if (useBtn) {
            const originalText = useBtn.textContent;
            useBtn.textContent = 'Loading...';
            useBtn.disabled = true;
        }
        
        // Close the modal first
        this.closeWebhookModal();
        
        // Brief delay to let the modal close, then navigate
        setTimeout(() => {
            window.location.href = output.value;
        }, 300);
    }

    async copyCurrentURL() {
        const copyBtn = document.getElementById('copy-current-url-button');
        
        if (!this.currentWebhookUrl) {
            console.error('No webhook URL available to copy');
            return;
        }
        
        // Generate the current shareable URL
        const encodedWebhook = this.encodeWebhookURL(this.currentWebhookUrl);
        if (!encodedWebhook) {
            console.error('Failed to encode webhook URL');
            return;
        }
        
        const currentOrigin = window.location.origin;
        const currentPath = window.location.pathname;
        const shareableUrl = `${currentOrigin}${currentPath}#webhook=${encodedWebhook}`;
        
        console.log('Attempting to copy URL:', shareableUrl);
        
        try {
            // Try modern clipboard API first
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(shareableUrl);
                
                if (copyBtn) {
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => {
                        copyBtn.textContent = originalText;
                    }, 2000);
                }
                return;
            }
        } catch (error) {
            console.log('Clipboard API failed, trying fallback:', error);
        }
        
        // Fallback method - create temporary input element
        try {
            const tempInput = document.createElement('input');
            tempInput.value = shareableUrl;
            tempInput.style.position = 'absolute';
            tempInput.style.left = '-9999px';
            document.body.appendChild(tempInput);
            
            tempInput.select();
            tempInput.setSelectionRange(0, tempInput.value.length);
            
            const successful = document.execCommand('copy');
            document.body.removeChild(tempInput);
            
            if (successful) {
                if (copyBtn) {
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => {
                        copyBtn.textContent = originalText;
                    }, 2000);
                }
            } else {
                throw new Error('execCommand failed');
            }
        } catch (fallbackError) {
            console.error('All copy methods failed:', fallbackError);
            
            // Final fallback - show the URL in an alert (not ideal but functional)
            alert(`Copy failed. Please manually copy this URL:\n\n${shareableUrl}`);
            
            if (copyBtn) {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copy failed';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }
        }
    }

    generateNewWebhook() {
        const configMode = document.getElementById('webhook-config-mode');
        const connectedMode = document.getElementById('webhook-connected-mode');
        const input = document.getElementById('webhook-url-input');
        
        // Switch to configuration mode
        if (configMode) configMode.style.display = 'block';
        if (connectedMode) connectedMode.style.display = 'none';
        
        // Pre-fill with current webhook URL for editing
        if (input && this.currentWebhookUrl) {
            input.value = this.currentWebhookUrl;
            input.focus();
            input.select(); // Select all for easy replacement
        }
    }

    updateUI() {
        // Update status indicator dot
        const statusDot = document.getElementById('discord-status-dot');
        
        if (statusDot) {
            if (this.currentWebhookUrl) {
                statusDot.classList.add('connected');
            } else {
                statusDot.classList.remove('connected');
            }
        }
        
        // The share button visibility is handled in main.js based on webhook status and results
    }

    getCurrentWebhookURL() {
        return this.currentWebhookUrl;
    }

    hasWebhook() {
        return !!this.currentWebhookUrl;
    }
}

// Create global instance
window.webhookManager = new WebhookManager();