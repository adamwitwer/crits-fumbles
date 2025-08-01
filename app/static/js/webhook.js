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
        const input = document.getElementById('webhook-url-input');
        
        // Pre-fill with current webhook if available
        if (this.currentWebhookUrl && input) {
            input.value = this.currentWebhookUrl;
        }
        
        if (overlay) {
            overlay.classList.add('active');
            if (input) {
                input.focus();
            }
        }
    }

    closeWebhookModal() {
        const overlay = document.getElementById('webhook-modal-overlay');
        const shareableSection = document.getElementById('shareable-url-section');
        
        if (overlay) {
            overlay.classList.remove('active');
        }
        
        if (shareableSection) {
            shareableSection.style.display = 'none';
        }
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

    updateUI() {
        const configureBtn = document.getElementById('configure-webhook-button');
        const shareBtn = document.getElementById('share-discord-button');
        
        if (this.currentWebhookUrl) {
            // Webhook is configured - show as connected
            if (configureBtn) {
                const buttonText = configureBtn.querySelector('.button-text');
                if (buttonText) {
                    buttonText.textContent = 'Discord Connected';
                }
                configureBtn.classList.add('connected');
            }
        } else {
            // No webhook configured
            if (configureBtn) {
                const buttonText = configureBtn.querySelector('.button-text');
                if (buttonText) {
                    buttonText.textContent = 'Configure Discord';
                }
                configureBtn.classList.remove('connected');
            }
        }
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