/**
 * NFT Examination System - Funcionalidad Específica
 * Integración con PROFINS XXIV Framework
 */

class NFTExamSystem {
    constructor() {
        this.totalQuestions = 10;
        this.completedQuestions = 0;
        this.autoSaveInterval = null;
        this.validationRules = {
            minCharacters: 50,
            nftKeywords: ['NFT', 'token', 'blockchain', 'smart contract', 'propiedad intelectual', 'derechos', 'copyright', 'licencia']
        };
        
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeExamForm();
            this.initializeProgressTracking();
            this.initializeAutoSave();
            this.initializeValidation();
            this.initializeTimeStamps();
        });
    }

    initializeExamForm() {
        const examForm = document.getElementById('exam-form');
        if (!examForm) return;

        this.setTimeStamps();
        examForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        this.setupRealTimeValidation();
        this.setupTermChips();
        
        console.log('Formulario de examen inicializado');
    }

    setupRealTimeValidation() {
        const radioButtons = document.querySelectorAll('input[type="radio"]');
        radioButtons.forEach(radio => {
            radio.addEventListener('change', () => {
                this.updateQuestionProgress();
                this.updateOverallProgress();
            });
        });

        const textareas = document.querySelectorAll('textarea[name*="_reason"]');
        textareas.forEach(textarea => {
            this.setupCharacterCounter(textarea);
            
            textarea.addEventListener('input', () => {
                this.validateTextarea(textarea);
                this.updateQuestionProgress();
                this.updateOverallProgress();
            });
        });
    }

    setupCharacterCounter(textarea) {
        const container = textarea.parentElement;
        const counter = document.createElement('div');
        counter.className = 'character-counter mt-2';
        counter.innerHTML = `<small class="text-muted"><span class="current-count">0</span>/${this.validationRules.minCharacters} caracteres mínimos</small>`;
        container.appendChild(counter);

        textarea.addEventListener('input', () => {
            const currentCount = textarea.value.length;
            const counterSpan = counter.querySelector('.current-count');
            counterSpan.textContent = currentCount;
            
            if (currentCount >= this.validationRules.minCharacters) {
                counter.className = 'character-counter mt-2 text-success';
            } else {
                counter.className = 'character-counter mt-2 text-muted';
            }
        });
    }

    setupTermChips() {
        const textareas = document.querySelectorAll('textarea[name*="_reason"]');
        textareas.forEach(textarea => {
            const container = textarea.parentElement;
            const chipContainer = document.createElement('div');
            chipContainer.className = 'term-chips mt-3';
            chipContainer.innerHTML = `
                <small class="text-muted d-block mb-2">Términos jurídicos sugeridos:</small>
                <div class="d-flex flex-wrap gap-2">
                    ${this.validationRules.nftKeywords.map(term => 
                        `<span class="badge badge-outline badge-sm" style="cursor: pointer;" onclick="nftExam.insertTerm('${textarea.name}', '${term}')">${term}</span>`
                    ).join('')}
                </div>
            `;
            container.appendChild(chipContainer);
        });
    }

    insertTerm(textareaName, term) {
        const textarea = document.querySelector(`[name="${textareaName}"]`);
        if (!textarea) return;

        const cursorPos = textarea.selectionStart;
        const textBefore = textarea.value.substring(0, cursorPos);
        const textAfter = textarea.value.substring(cursorPos);
        
        textarea.value = textBefore + term + textAfter;
        textarea.selectionStart = textarea.selectionEnd = cursorPos + term.length;
        textarea.focus();
        
        textarea.dispatchEvent(new Event('input'));
        
        if (window.Profins && window.Profins.showNotification) {
            window.Profins.showNotification(`Término "${term}" insertado`, 'info');
        }
    }

    updateOverallProgress() {
        let totalCompleted = 0;
        
        for (let caseId = 1; caseId <= 5; caseId++) {
            for (let qIndex = 0; qIndex < 2; qIndex++) {
                const radioChecked = document.querySelector(`input[name="q_${caseId}_${qIndex}_bool"]:checked`);
                const textarea = document.querySelector(`textarea[name="q_${caseId}_${qIndex}_reason"]`);
                
                if (radioChecked && textarea && textarea.value.trim().length >= this.validationRules.minCharacters) {
                    totalCompleted++;
                }
            }
        }

        const percentage = Math.round((totalCompleted / this.totalQuestions) * 100);
        this.completedQuestions = totalCompleted;
        
        this.updateProgressRing(percentage);
        this.updateSubmitButton(totalCompleted === this.totalQuestions);
    }

    updateProgressRing(percentage) {
        const progressRing = document.getElementById('progress-ring');
        if (progressRing) {
            progressRing.setAttribute('data-progress', percentage);
            
            if (window.AdvancedComponentsManager && window.AdvancedComponentsManager.animateProgressRing) {
                window.AdvancedComponentsManager.animateProgressRing(progressRing);
            }
            
            const progressText = document.getElementById('progress-text');
            if (progressText) {
                progressText.textContent = `${percentage}%`;
            }
        }
    }

    updateQuestionProgress() {
        for (let caseId = 1; caseId <= 5; caseId++) {
            let caseCompleted = 0;
            
            for (let qIndex = 0; qIndex < 2; qIndex++) {
                const radioChecked = document.querySelector(`input[name="q_${caseId}_${qIndex}_bool"]:checked`);
                const textarea = document.querySelector(`textarea[name="q_${caseId}_${qIndex}_reason"]`);
                
                if (radioChecked && textarea && textarea.value.trim().length >= this.validationRules.minCharacters) {
                    caseCompleted++;
                }
            }
            
            const caseBadge = document.querySelector(`[data-case-progress="${caseId}"]`);
            if (caseBadge) {
                caseBadge.textContent = `${caseCompleted}/2`;
                caseBadge.className = caseCompleted === 2 ? 'badge badge-success' : 'badge badge-warning';
            }
        }
    }

    validateTextarea(textarea) {
        const value = textarea.value.trim();
        const isValid = value.length >= this.validationRules.minCharacters;
        
        if (isValid) {
            textarea.classList.remove('is-invalid');
            textarea.classList.add('is-valid');
        } else {
            textarea.classList.remove('is-valid');
            if (value.length > 0) {
                textarea.classList.add('is-invalid');
            }
        }
        
        return isValid;
    }

    updateSubmitButton(allCompleted) {
        const submitBtn = document.querySelector('button[type="submit"]');
        if (!submitBtn) return;

        if (allCompleted) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('btn-secondary');
            submitBtn.classList.add('btn-success');
            submitBtn.innerHTML = '<i class="fas fa-check-double me-2"></i>Finalizar y Enviar Evaluación';
        } else {
            submitBtn.disabled = true;
            submitBtn.classList.remove('btn-success');
            submitBtn.classList.add('btn-secondary');
            submitBtn.innerHTML = `<i class="fas fa-clock me-2"></i>Complete todas las preguntas (${this.completedQuestions}/${this.totalQuestions})`;
        }
    }

    initializeAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.saveProgress();
        }, 30000);

        window.addEventListener('beforeunload', () => {
            this.saveProgress();
        });
    }

    saveProgress() {
        const formData = this.collectFormData();
        if (Object.keys(formData).length === 0) return;

        sessionStorage.setItem('nft_exam_progress', JSON.stringify({
            data: formData,
            timestamp: new Date().toISOString(),
            completed: this.completedQuestions
        }));

        this.showAutoSaveNotification();
    }

    collectFormData() {
        const form = document.getElementById('exam-form');
        if (!form) return {};

        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }

    showAutoSaveNotification() {
        if (window.Profins && window.Profins.showNotification) {
            window.Profins.showNotification('Progreso guardado automáticamente', 'success', 2000);
        } else {
            this.createSimpleNotification('Progreso guardado', 'success');
        }
    }

    createSimpleNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    initializeTimeStamps() {
        const examDateElement = document.getElementById('exam-date');
        const startTimeElement = document.getElementById('start-time');
        
        if (examDateElement) {
            examDateElement.textContent = new Date().toLocaleDateString('es-GT');
        }
        
        if (startTimeElement) {
            startTimeElement.textContent = new Date().toLocaleTimeString('es-GT');
        }
    }

    setTimeStamps() {
        const form = document.getElementById('exam-form');
        if (!form) return;

        if (!document.querySelector('input[name="start_time"]')) {
            const startTimeInput = document.createElement('input');
            startTimeInput.type = 'hidden';
            startTimeInput.name = 'start_time';
            startTimeInput.value = new Date().toISOString();
            form.appendChild(startTimeInput);
        }
    }

    handleFormSubmit(e) {
        e.preventDefault();
        
        if (!this.performFinalValidation()) {
            return;
        }

        this.showSubmitLoading();
        
        const endTimeInput = document.createElement('input');
        endTimeInput.type = 'hidden';
        endTimeInput.name = 'end_time';
        endTimeInput.value = new Date().toISOString();
        e.target.appendChild(endTimeInput);

        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        setTimeout(() => {
            e.target.submit();
        }, 1000);
    }

    performFinalValidation() {
        let isValid = true;
        const errors = [];

        for (let caseId = 1; caseId <= 5; caseId++) {
            for (let qIndex = 0; qIndex < 2; qIndex++) {
                const radioChecked = document.querySelector(`input[name="q_${caseId}_${qIndex}_bool"]:checked`);
                const textarea = document.querySelector(`textarea[name="q_${caseId}_${qIndex}_reason"]`);
                
                if (!radioChecked) {
                    errors.push(`Caso ${caseId}, Pregunta ${qIndex + 1}: Seleccione Verdadero o Falso`);
                    isValid = false;
                }
                
                if (!textarea || textarea.value.trim().length < this.validationRules.minCharacters) {
                    errors.push(`Caso ${caseId}, Pregunta ${qIndex + 1}: Justificación muy corta (mínimo ${this.validationRules.minCharacters} caracteres)`);
                    isValid = false;
                }
            }
        }

        if (!isValid) {
            this.showValidationErrors(errors);
        }

        return isValid;
    }

    showValidationErrors(errors) {
        const errorMessage = `
            <div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>Complete las siguientes preguntas:</h6>
                <ul class="mb-0 mt-2">
                    ${errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
            </div>
        `;
        
        if (window.Profins && window.Profins.showModal) {
            window.Profins.showModal('Validación de Examen', errorMessage);
        } else {
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
            const existingAlert = document.querySelector('.validation-alert');
            if (existingAlert) existingAlert.remove();
            
            const alertDiv = document.createElement('div');
            alertDiv.className = 'validation-alert';
            alertDiv.innerHTML = errorMessage;
            
            const mainContent = document.querySelector('.main-content');
            mainContent.insertBefore(alertDiv, mainContent.firstChild);
            
            setTimeout(() => alertDiv.remove(), 10000);
        }
    }

    showSubmitLoading() {
        const submitBtn = document.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Procesando evaluación...';
        }

        if (window.Profins && window.Profins.showLoading) {
            window.Profins.showLoading('Enviando evaluación...');
        }
    }

    restoreProgress() {
        const saved = sessionStorage.getItem('nft_exam_progress');
        if (!saved) return;

        try {
            const { data } = JSON.parse(saved);
            
            Object.entries(data).forEach(([name, value]) => {
                const input = document.querySelector(`[name="${name}"]`);
                if (input) {
                    if (input.type === 'radio' && input.value === value) {
                        input.checked = true;
                    } else if (input.tagName === 'TEXTAREA') {
                        input.value = value;
                    }
                }
            });

            this.updateOverallProgress();
            this.createSimpleNotification('Progreso anterior restaurado', 'info');
            
        } catch (error) {
            console.error('Error al restaurar progreso:', error);
        }
    }

    clearProgress() {
        sessionStorage.removeItem('nft_exam_progress');
    }

    initializeProgressTracking() {
        setTimeout(() => {
            this.restoreProgress();
        }, 500);
    }

    initializeValidation() {
        if (window.FormValidator) {
            window.FormValidator.init({
                realTime: true,
                showErrors: true
            });
        }
    }
}

// Inicialización global
window.nftExam = new NFTExamSystem();

// Exponer métodos útiles globalmente
window.insertTerm = (textareaName, term) => window.nftExam.insertTerm(textareaName, term);

// Integración con el framework cuando esté listo
document.addEventListener('FrameworkReady', () => {
    console.log('PROFINS XXIV Framework loaded, integrating NFT Exam System...');
    
    if (window.AdvancedComponentsManager) {
        window.AdvancedComponentsManager.refreshProgressRings();
    }
});

console.log('NFT Examination System initialized');