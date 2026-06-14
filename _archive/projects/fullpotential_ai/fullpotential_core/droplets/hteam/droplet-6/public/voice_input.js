(function() {
    'use strict';
    
    // Check if Web Speech API is supported
    const isSpeechSupported = () => 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    
    if (!isSpeechSupported()) {
        console.warn('[Voice Input] Web Speech API not supported in this browser');
        return;
    }
    
    console.log('[Voice Input] Script loaded successfully');
    console.log('[Voice Input] Speech API supported: true');
    
    // Initialize speech recognition
    const initRecognition = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        return recognition;
    };
    
    // Store message text globally for click handler
    let globalStoredMessageText = '';
    
    // Global state
    let recognition = null;
    let isRecording = false;
    let voiceButton = null;
    let voiceButtonObserver = null;
    
    // Find input element
    const findInput = () => {
        return document.getElementById('chat-input') ||
               document.querySelector('textarea[placeholder*="message" i]') ||
               document.querySelector('textarea[placeholder*="Type" i]') ||
               document.querySelector('textarea[placeholder*="Enter" i]') ||
               document.querySelector('textarea');
    };
    
    // Create voice button
    const createVoiceButton = () => {
        const btn = document.createElement('button');
        btn.id = 'voice-input-btn';
        btn.type = 'button';
        btn.className = 'voice-input-btn';
        btn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
        `;
        
        btn.onclick = () => {
            const input = findInput();
            if (!input) {
                alert('Input field not found. Please refresh the page.');
                return;
            }
            
            if (!recognition) {
                recognition = initRecognition();
            }
            
            if (isRecording) {
                recognition.stop();
                isRecording = false;
                btn.classList.remove('recording');
            } else {
                isRecording = true;
                btn.classList.add('recording');
                
                recognition.onresult = (e) => {
                    const transcript = e.results[0][0].transcript;
                    console.log('[Voice Input] 🎤 Speech recognized:', transcript);
                    const input = findInput();
                    if (input) {
                        globalStoredMessageText = transcript;
                        
                        // Set value using native value setter to bypass React
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
                        if (nativeInputValueSetter) {
                            nativeInputValueSetter.call(input, transcript);
                        } else {
                            input.value = transcript;
                        }
                        
                        // Trigger comprehensive events to update React state
                        const events = [
                            new Event('input', { bubbles: true, cancelable: true }),
                            new Event('change', { bubbles: true, cancelable: true }),
                            new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'a', code: 'KeyA' }),
                            new KeyboardEvent('keyup', { bubbles: true, cancelable: true, key: 'a', code: 'KeyA' }),
                        ];
                        
                        events.forEach(evt => {
                            input.dispatchEvent(evt);
                        });
                        
                        // Also try to update React's internal state directly
                        const reactFiber = input._reactInternalFiber || input._reactInternalInstance || input.__reactInternalInstance;
                        if (reactFiber) {
                            try {
                                const props = reactFiber.memoizedProps || reactFiber.pendingProps;
                                if (props && props.value !== undefined) {
                                    if (reactFiber.memoizedProps) reactFiber.memoizedProps.value = transcript;
                                    if (reactFiber.pendingProps) reactFiber.pendingProps.value = transcript;
                                }
                            } catch (e) {
                                console.log('[Voice Input] Could not update React fiber:', e);
                            }
                        }
                        
                        // Force enable send button
                        const sendButton = document.getElementById('chat-submit') ||
                                         document.querySelector('button[type="submit"]') ||
                                         document.querySelector('button[aria-label*="send" i]');
                        
                        if (sendButton) {
                            console.log('[Voice Input] Enabling send button...');
                            sendButton.removeAttribute('disabled');
                            sendButton.disabled = false;
                            sendButton.style.pointerEvents = 'auto';
                            sendButton.style.opacity = '1';
                            sendButton.style.cursor = 'pointer';
                            sendButton.classList.remove('disabled');
                            
                            // Also try to update React's disabled state for the button
                            const buttonFiber = sendButton._reactInternalFiber || sendButton._reactInternalInstance || sendButton.__reactInternalInstance;
                            if (buttonFiber) {
                                try {
                                    if (buttonFiber.memoizedProps) buttonFiber.memoizedProps.disabled = false;
                                    if (buttonFiber.pendingProps) buttonFiber.pendingProps.disabled = false;
                                } catch (e) {
                                    console.log('[Voice Input] Could not update button React fiber:', e);
                                }
                            }
                            
                            console.log('[Voice Input] ✅ Send button enabled');
                            
                            // Auto-click send button after a short delay
                            setTimeout(() => {
                                const currentInput = findInput();
                                const currentSendButton = document.getElementById('chat-submit') ||
                                                         document.querySelector('button[type="submit"]');
                                
                                if (currentInput && currentSendButton && !currentSendButton.disabled) {
                                    const inputValue = currentInput.value?.trim() || '';
                                    console.log('[Voice Input] Auto-clicking send button, input value:', inputValue);
                                    
                                    if (inputValue) {
                                        // Try to trigger form submission
                                        const form = currentInput.closest('form');
                                        if (form) {
                                            console.log('[Voice Input] Submitting form...');
                                            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                                        }
                                        
                                        // Also try clicking the button
                                        setTimeout(() => {
                                            currentSendButton.click();
                                        }, 100);
                                    }
                                }
                            }, 500);
                        } else {
                            console.warn('[Voice Input] ⚠️ Send button not found');
                        }
                    }
                };
                
                recognition.onerror = (e) => {
                    isRecording = false;
                    btn.classList.remove('recording');
                    console.error('[Voice Input] Recognition error:', e.error);
                };
                
                recognition.onend = () => {
                    isRecording = false;
                    btn.classList.remove('recording');
                };
                
                recognition.start();
            }
        };
        
        return btn;
    };
    
    // Add voice button to container
    const addVoiceButton = () => {
        // Check if button already exists
        if (document.getElementById('voice-input-btn')) {
            return;
        }
        
        const input = findInput();
        if (!input) {
            return;
        }
        
        // Find the best container - look for form or parent div
        let container = input.closest('form');
        if (!container) {
            container = input.parentElement;
            // Walk up to find a non-input container
            let attempts = 0;
            while (container && attempts < 5) {
                if (container.tagName !== 'TEXTAREA' && container.tagName !== 'INPUT') {
                    break;
                }
                container = container.parentElement;
                attempts++;
            }
        }
        
        if (!container) {
            container = input.parentElement || document.body;
        }
        
        // Create button
        voiceButton = createVoiceButton();
        container.appendChild(voiceButton);
        
        // Make container position relative
        if (window.getComputedStyle(container).position === 'static') {
            container.style.position = 'relative';
        }
        
        console.log('[Voice Input] ✅ Voice input button added');
        
        // Watch for button removal and re-add it
        if (voiceButtonObserver) {
            voiceButtonObserver.disconnect();
        }
        
        voiceButtonObserver = new MutationObserver(() => {
            const button = document.getElementById('voice-input-btn');
            if (!button && findInput()) {
                console.log('[Voice Input] ⚠️ Button removed, re-adding...');
                setTimeout(() => {
                    if (!document.getElementById('voice-input-btn')) {
                        addVoiceButton();
                    }
                }, 100);
            }
        });
        
        voiceButtonObserver.observe(container, {
            childList: true,
            subtree: true
        });
    };
    
    // Watch for input field to appear
    const watchForInput = () => {
        const checkInterval = setInterval(() => {
            const input = findInput();
            if (input && !document.getElementById('voice-input-btn')) {
                addVoiceButton();
                clearInterval(checkInterval);
            }
        }, 500);
        
        setTimeout(() => clearInterval(checkInterval), 30000);
    };
    
    // Also periodically check if button is still there
    setInterval(() => {
        const button = document.getElementById('voice-input-btn');
        const input = findInput();
        if (!button && input) {
            console.log('[Voice Input] ⚠️ Periodic check: Button missing, re-adding...');
            addVoiceButton();
        }
    }, 2000);
    
    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            watchForInput();
            setTimeout(addVoiceButton, 1000);
        });
    } else {
        watchForInput();
        setTimeout(addVoiceButton, 1000);
    }
    
    // Also try after a longer delay
    setTimeout(addVoiceButton, 3000);
})();
