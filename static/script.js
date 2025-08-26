/**
 * Modern JavaScript for NFTs and IP Examination System
 * Organismo Judicial de Guatemala
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 NFT Examination System initialized');
    
    // Initialize all components
    initializeExamForm();
    initializeProgressTracking();
    initializeCopyPasteDetection();
    initializeAutoSave();
    initializeAccessibility();
    initializeNFTSpecificFeatures();
});

/**
 * Initialize main exam form functionality
 */
function initializeExamForm() {
    const examForm = document.getElementById('comprehensive-exam-form');
    if (!examForm) return;
    
    console.log('📝 Initializing exam form...');
    
    examForm.addEventListener('submit', function(e) {
        if (!validateExamSubmission()) {
            e.preventDefault();
            return false;
        }
        
        showSubmissionLoading();
        return true;
    });
    
    // Real-time validation
    const textareas = document.querySelectorAll('textarea[name*="reason"]');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            validateAnswerLength(this);
            updateProgressIndicator();
        });
        
        textarea.addEventListener('blur', function() {
            checkAnswerQuality(this);
        });
    });
    
    // Radio button change handlers
    const radioButtons = document.querySelectorAll('input[type="radio"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', function() {
            updateProgressIndicator();
            highlightAssociatedQuestion(this);
        });
    });
}

/**
 * Validate exam submission before sending
 */
function validateExamSubmission() {
    const issues = [];
    
    // Check all radio buttons are selected
    const radioGroups = getRadioGroups();
    radioGroups.forEach((group, index) => {
        const checked = document.querySelector(`input[name="${group}"]:checked`);
        if (!checked) {
            issues.push(`Debe seleccionar Verdadero o Falso en el Caso ${Math.floor(index/2) + 1}, Pregunta ${(index % 2) + 1}`);
        }
    });
    
    // Check all justifications are adequate
    const textareas = document.querySelectorAll('textarea[name*="reason"]');
    textareas.forEach((textarea, index) => {
        const caseNum = Math.floor(index/2) + 1;
        const qNum = (index % 2) + 1;
        
        if (textarea.value.trim().length < 20) {
            issues.push(`La justificación del Caso ${caseNum}, Pregunta ${qNum} es muy breve (mínimo 20 caracteres)`);
        }
        
        if (containsNFTKeywords(textarea.value) < 1) {
            issues.push(`La justificación del Caso ${caseNum}, Pregunta ${qNum} debe incluir terminología jurídica sobre NFTs`);
        }
    });
    
    if (issues.length > 0) {
        showValidationModal(issues);
        return false;
    }
    
    return showFinalConfirmation();
}

/**
 * Show validation issues to user
 */
function showValidationModal(issues) {
    const modal = document.createElement('div');
    modal.className = 'validation-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>⚠️ Revise su examen</h3>
            </div>
            <div class="modal-body">
                <p>Se encontraron los siguientes problemas:</p>
                <ul>
                    ${issues.map(issue => `<li>${issue}</li>`).join('')}
                </ul>
            </div>
            <div class="modal-footer">
                <button onclick="closeValidationModal()" class="btn btn-primary">
                    Revisar Respuestas
                </button>
            </div>
        </div>
        <div class="modal-backdrop" onclick="closeValidationModal()"></div>
    `;
    
    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('show'), 10);
}

/**
 * Show final confirmation before submission
 */
function showFinalConfirmation() {
    const totalQuestions = document.querySelectorAll('textarea[name*="reason"]').length;
    const answeredQuestions = Array.from(document.querySelectorAll('textarea[name*="reason"]'))
        .filter(t => t.value.trim().length > 20).length;
    
    return confirm(
        `🎓 ¿Está seguro de enviar su examen sobre NFTs y Propiedad Intelectual?\n\n` +
        `📊 Progreso: ${answeredQuestions}/${totalQuestions} preguntas completadas\n` +
        `⏰ Una vez enviado no podrá realizar cambios\n` +
        `🤖 El sistema analizará automáticamente sus respuestas\n\n` +
        `¿Desea continuar?`
    );
}

/**
 * Progress tracking functionality
 */
function initializeProgressTracking() {
    // Create progress bar if not exists
    if (!document.querySelector('.progress-indicator')) {
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-indicator';
        progressBar.innerHTML = `
            <div class="progress-bar"></div>
            <div class="progress-text">0%</div>
        `;
        document.body.prepend(progressBar);
    }
    
    updateProgressIndicator();
    
    // Update progress every 30 seconds
    setInterval(updateProgressIndicator, 30000);
}

/**
 * Update progress indicator
 */
function updateProgressIndicator() {
    const totalFields = getTotalRequiredFields();
    const completedFields = getCompletedFields();
    const percentage = totalFields > 0 ? Math.round((completedFields / totalFields) * 100) : 0;
    
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text');
    
    if (progressBar && progressText) {
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${percentage}%`;
        
        // Update color based on progress
        if (percentage >= 100) {
            progressBar.style.background = 'linear-gradient(90deg, #27ae60, #2ecc71)';
        } else if (percentage >= 50) {
            progressBar.style.background = 'linear-gradient(90deg, #f39c12, #e67e22)';
        } else {
            progressBar.style.background = 'linear-gradient(90deg, #3498db, #2980b9)';
        }
    }
    
    // Update case-specific progress
    updateCaseProgress();
}

/**
 * Copy-paste detection system
 */
function initializeCopyPasteDetection() {
    const textareas = document.querySelectorAll('textarea[name*="reason"]');
    
    textareas.forEach(textarea => {
        let pasteCount = 0;
        let lastPasteTime = 0;
        let typingPattern = [];
        
        // Detect paste events
        textarea.addEventListener('paste', function(e) {
            pasteCount++;
            lastPasteTime = Date.now();
            
            console.warn(`📋 Paste detected in question: ${this.name}`);
            
            if (pasteCount > 2) {
                logSuspiciousActivity('excessive_paste', {
                    field: this.name,
                    count: pasteCount,
                    timestamp: new Date().toISOString()
                });
                
                showPasteWarning(this);
            }
        });
        
        // Analyze typing patterns
        textarea.addEventListener('keydown', function(e) {
            const now = Date.now();
            typingPattern.push(now);
            
            // Keep only last 100 keystrokes
            if (typingPattern.length > 100) {
                typingPattern.shift();
            }
            
            // Detect unnaturally fast typing
            if (typingPattern.length >= 10) {
                const avgInterval = (typingPattern[typingPattern.length - 1] - typingPattern[typingPattern.length - 10]) / 9;
                if (avgInterval < 50) { // Less than 50ms between keystrokes consistently
                    logSuspiciousActivity('fast_typing', {
                        field: this.name,
                        avgInterval: avgInterval,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        });
    });
}

/**
 * Auto-save functionality
 */
function initializeAutoSave() {
    const AUTOSAVE_KEY = 'nft_exam_autosave';
    const AUTOSAVE_INTERVAL = 30000; // 30 seconds
    
    // Load saved data
    loadAutoSave();
    
    // Save periodically
    setInterval(() => {
        saveFormData();
    }, AUTOSAVE_INTERVAL);
    
    // Save on beforeunload
    window.addEventListener('beforeunload', saveFormData);
    
    function saveFormData() {
        const formData = {};
        
        // Save radio selections
        document.querySelectorAll('input[type="radio"]:checked').forEach(radio => {
            formData[radio.name] = radio.value;
        });
        
        // Save textarea values
        document.querySelectorAll('textarea[name*="reason"]').forEach(textarea => {
            if (textarea.value.trim()) {
                formData[textarea.name] = textarea.value;
            }
        });
        
        // Save student info
        const studentName = document.querySelector('input[name="student_name"]');
        const studentCarne = document.querySelector('input[name="student_carne"]');
        
        if (studentName) formData.student_name = studentName.value;
        if (studentCarne) formData.student_carne = studentCarne.value;
        
        // Save to localStorage
        try {
            localStorage.setItem(AUTOSAVE_KEY, JSON.stringify({
                data: formData,
                timestamp: new Date().toISOString(),
                url: window.location.pathname
            }));
        } catch (e) {
            console.warn('Could not save to localStorage:', e);
        }
    }
    
    function loadAutoSave() {
        try {
            const saved = localStorage.getItem(AUTOSAVE_KEY);
            if (!saved) return;
            
            const { data, timestamp, url } = JSON.parse(saved);
            
            // Only load if same page and recent (within 24 hours)
            const savedTime = new Date(timestamp);
            const now = new Date();
            const hoursDiff = (now - savedTime) / (1000 * 60 * 60);
            
            if (url !== window.location.pathname || hoursDiff > 24) {
                localStorage.removeItem(AUTOSAVE_KEY);
                return;
            }
            
            // Restore form data
            Object.keys(data).forEach(name => {
                const element = document.querySelector(`[name="${name}"]`);
                if (element) {
                    if (element.type === 'radio') {
                        if (element.value === data[name]) {
                            element.checked = true;
                        }
                    } else {
                        element.value = data[name];
                    }
                }
            });
            
            console.log('📁 Auto-saved data restored from', timestamp);
            showRestoreNotification(savedTime);
            
        } catch (e) {
            console.warn('Could not load auto-save:', e);
            localStorage.removeItem(AUTOSAVE_KEY);
        }
    }
    
    function showRestoreNotification(savedTime) {
        const notification = document.createElement('div');
        notification.className = 'auto-save-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">💾</span>
                <span class="notification-text">
                    Datos restaurados automáticamente desde ${savedTime.toLocaleString()}
                </span>
                <button onclick="this.parentElement.parentElement.remove()" class="notification-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

/**
 * Accessibility enhancements
 */
function initializeAccessibility() {
    // Add keyboard navigation
    const radioGroups = getRadioGroups();
    radioGroups.forEach(groupName => {
        const radios = document.querySelectorAll(`input[name="${groupName}"]`);
        radios.forEach((radio, index) => {
            radio.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    e.preventDefault();
                    const nextIndex = (index + 1) % radios.length;
                    radios[nextIndex].focus();
                    radios[nextIndex].checked = true;
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    e.preventDefault();
                    const prevIndex = (index - 1 + radios.length) % radios.length;
                    radios[prevIndex].focus();
                    radios[prevIndex].checked = true;
                }
            });
        });
    });
    
    // Add skip navigation
    const skipNav = document.createElement('a');
    skipNav.href = '#main-content';
    skipNav.className = 'skip-nav';
    skipNav.textContent = 'Saltar al contenido principal';
    document.body.prepend(skipNav);
    
    // Ensure proper focus management
    document.querySelectorAll('fieldset').forEach(fieldset => {
        fieldset.addEventListener('focusin', function() {
            this.classList.add('focus-within');
        });
        
        fieldset.addEventListener('focusout', function() {
            setTimeout(() => {
                if (!this.contains(document.activeElement)) {
                    this.classList.remove('focus-within');
                }
            }, 100);
        });
    });
}

/**
 * NFT-specific features
 */
function initializeNFTSpecificFeatures() {
    // Add NFT terminology hints
    addTerminologyHints();
    
    // Add smart contract examples
    addSmartContractExamples();
    
    // Add reference links
    addReferenceLinks();
    
    // Validate NFT-specific content
    initializeNFTContentValidation();
}

/**
 * Add NFT terminology hints to textareas
 */
function addTerminologyHints() {
    const nftTerms = [
        'token no fungible', 'blockchain', 'smart contract', 'tokenización',
        'obra intelectual', 'soporte digital', 'derechos patrimoniales',
        'comunicación pública', 'art. 3 LPI', 'art. 13 LPI', 'ERC-721'
    ];
    
    const textareas = document.querySelectorAll('textarea[name*="reason"]');
    textareas.forEach(textarea => {
        const hintContainer = document.createElement('div');
        hintContainer.className = 'terminology-hints';
        hintContainer.innerHTML = `
            <details>
                <summary>💡 Términos jurídicos sugeridos</summary>
                <div class="hints-content">
                    ${nftTerms.map(term => 
                        `<span class="term-hint" onclick="insertTerm('${textarea.name}', '${term}')">${term}</span>`
                    ).join('')}
                </div>
            </details>
        `;
        
        textarea.parentElement.appendChild(hintContainer);
    });
}

/**
 * Utility functions
 */
function getTotalRequiredFields() {
    const radioGroups = getRadioGroups().length;
    const textareas = document.querySelectorAll('textarea[name*="reason"]').length;
    return radioGroups + textareas;
}

function getCompletedFields() {
    const completedRadios = getRadioGroups().filter(group => 
        document.querySelector(`input[name="${group}"]:checked`)
    ).length;
    
    const completedTextareas = Array.from(document.querySelectorAll('textarea[name*="reason"]'))
        .filter(t => t.value.trim().length >= 20).length;
    
    return completedRadios + completedTextareas;
}

function getRadioGroups() {
    const groups = new Set();
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        groups.add(radio.name);
    });
    return Array.from(groups);
}

function containsNFTKeywords(text) {
    const keywords = [
        'nft', 'token', 'blockchain', 'smart contract', 'obra intelectual',
        'soporte', 'tokenización', 'derechos', 'lpi', 'propiedad intelectual'
    ];
    
    const lowerText = text.toLowerCase();
    return keywords.filter(keyword => lowerText.includes(keyword)).length;
}

function logSuspiciousActivity(type, data) {
    console.warn(`🚨 Suspicious activity detected: ${type}`, data);
    // In a real implementation, this would send to server
}

function showSubmissionLoading() {
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'submission-loading';
    loadingOverlay.innerHTML = `
        <div class="loading-content">
            <div class="spinner"></div>
            <h3>🚀 Enviando Examen</h3>
            <p>Procesando sus respuestas sobre NFTs y Propiedad Intelectual...</p>
            <div class="loading-steps">
                <div class="step active">✓ Validando respuestas</div>
                <div class="step">⏳ Analizando con IA</div>
                <div class="step">📊 Calculando puntuación</div>
                <div class="step">📝 Generando feedback</div>
            </div>
        </div>
    `;
    
    document.body.appendChild(loadingOverlay);
    
    // Animate steps
    let currentStep = 0;
    const steps = loadingOverlay.querySelectorAll('.step');
    const stepInterval = setInterval(() => {
        if (currentStep < steps.length - 1) {
            steps[currentStep].classList.remove('active');
            steps[currentStep].classList.add('completed');
            currentStep++;
            steps[currentStep].classList.add('active');
        } else {
            clearInterval(stepInterval);
        }
    }, 1000);
}

function validateAnswerLength(textarea) {
    const length = textarea.value.trim().length;
    const minLength = 20;
    
    textarea.classList.remove('too-short', 'adequate', 'good');
    
    if (length < minLength) {
        textarea.classList.add('too-short');
        textarea.style.borderColor = '#e74c3c';
    } else if (length < 100) {
        textarea.classList.add('adequate');
        textarea.style.borderColor = '#f39c12';
    } else {
        textarea.classList.add('good');
        textarea.style.borderColor = '#27ae60';
    }
}

function checkAnswerQuality(textarea) {
    const text = textarea.value.trim();
    const nftKeywords = containsNFTKeywords(text);
    
    // Remove existing quality indicators
    const existingIndicator = textarea.parentElement.querySelector('.quality-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }
    
    if (text.length >= 20) {
        const indicator = document.createElement('div');
        indicator.className = 'quality-indicator';
        
        if (nftKeywords >= 3 && text.length >= 100) {
            indicator.innerHTML = '🌟 <strong>Excelente:</strong> Respuesta completa con terminología jurídica apropiada';
            indicator.className += ' excellent';
        } else if (nftKeywords >= 2) {
            indicator.innerHTML = '✅ <strong>Bien:</strong> Incluye términos jurídicos relevantes';
            indicator.className += ' good';
        } else if (nftKeywords >= 1) {
            indicator.innerHTML = '⚠️ <strong>Regular:</strong> Considere incluir más terminología jurídica específica';
            indicator.className += ' warning';
        } else {
            indicator.innerHTML = '❗ <strong>Mejorable:</strong> Incluya términos jurídicos sobre NFTs y PI';
            indicator.className += ' needs-improvement';
        }
        
        textarea.parentElement.appendChild(indicator);
    }
}

function insertTerm(textareaName, term) {
    const textarea = document.querySelector(`[name="${textareaName}"]`);
    if (textarea) {
        const cursorPos = textarea.selectionStart;
        const textBefore = textarea.value.substring(0, cursorPos);
        const textAfter = textarea.value.substring(cursorPos);
        
        textarea.value = textBefore + term + textAfter;
        textarea.selectionStart = textarea.selectionEnd = cursorPos + term.length;
        textarea.focus();
        
        validateAnswerLength(textarea);
        updateProgressIndicator();
    }
}

// Global functions for modal handling
window.closeValidationModal = function() {
    const modal = document.querySelector('.validation-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
};

// Export for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeExamForm,
        validateExamSubmission,
        updateProgressIndicator,
        containsNFTKeywords
    };
}

console.log('✅ NFT Examination System JavaScript loaded successfully');