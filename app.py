/**
 * NFT Examination System - Funcionalidad Específica
 * Integración con PROFINS XXIV Framework
 * Mantiene toda la funcionalidad original adaptada al nuevo framework
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

    // =================== INICIALIZACIÓN ===================
    initializeExamForm() {
        const examForm = document.getElementById('exam-form');
        if (!examForm) return;

        // Configurar fecha y hora de inicio
        this.setTimeStamps();
        
        // Configurar eventos de formulario
        examForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Configurar validación en tiempo real
        this.setupRealTimeValidation();
        
        // Configurar chips de términos jurídicos
        this.setupTermChips();
        
        console.log('✅ Formulario de examen inicializado');
    }

    setupRealTimeValidation() {
        // Validación para botones radio
        const radioButtons = document.querySelectorAll('input[type="radio"]');
        radioButtons.forEach(radio => {
            radio.addEventListener('change', () => {
                this.updateQuestionProgress();
                this.updateOverallProgress();
            });
        });

        // Validación para textareas
        const textareas = document.querySelectorAll('textarea[name*="_reason"]');
        textareas.forEach(textarea => {
            // Contador de caracteres
            this.setupCharacterCounter(textarea);
            
            // Validación en tiempo real
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
        // Agregar chips de términos jurídicos después de cada textarea
        const textareas = document.querySelectorAll('textarea[name*="_reason"]');
        textareas.forEach(textarea => {
            const container = textarea.parentElement;
            const chipContainer = document.createElement('div');
            chipContainer.className = 'term-chips mt-3';
            chipContainer.innerHTML = `
                <small class="text-muted d-block mb-2">💡 Términos jurídicos sugeridos:</small>
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
        
        // Disparar eventos para actualizar contadores
        textarea.dispatchEvent(new Event('input'));
        
        // Mostrar notificación usando el framework
        if (window.Profins && window.Profins.showNotification) {
            window.Profins.showNotification(`Término "${term}" insertado`, 'info');
        }
    }

    // =================== PROGRESO Y VALIDACIÓN ===================
    updateOverallProgress() {
        let totalCompleted = 0;
        
        // Contar preguntas completadas
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
        
        // Actualizar círculo de progreso principal
        this.updateProgressRing(percentage);
        
        // Actualizar estado del botón de envío
        this.updateSubmitButton(totalCompleted === this.totalQuestions);
    }

    updateProgressRing(percentage) {
        const progressRing = document.getElementById('progress-ring');
        if (progressRing) {
            progressRing.setAttribute('data-progress', percentage);
            
            // Si el framework tiene método para animar el ring
            if (window.AdvancedComponentsManager && window.AdvancedComponentsManager.animateProgressRing) {
                window.AdvancedComponentsManager.animateProgressRing(progressRing);
            }
            
            // Actualizar texto del progreso
            const progressText = document.getElementById('progress-text');
            if (progressText) {
                progressText.textContent = `${percentage}%`;
            }
        }
    }

    updateQuestionProgress() {
        // Actualizar progreso por caso individual si existe
        for (let caseId = 1; caseId <= 5; caseId++) {
            let caseCompleted = 0;
            
            for (let qIndex = 0; qIndex < 2; qIndex++) {
                const radioChecked = document.querySelector(`input[name="q_${caseId}_${qIndex}_bool"]:checked`);
                const textarea = document.querySelector(`textarea[name="q_${caseId}_${qIndex}_reason"]`);
                
                if (radioChecked && textarea && textarea.value.trim().length >= this.validationRules.minCharacters) {
                    caseCompleted++;
                }
            }
            
            // Actualizar badge del caso si existe
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
        
        // Aplicar clases del framework para validación
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

    // =================== AUTO-GUARDADO ===================
    initializeAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.saveProgress();
        }, 30000); // Cada 30 segundos

        // Guardar al cambiar pestañas/ventanas
        window.addEventListener('beforeunload', () => {
            this.saveProgress();
        });
    }

    saveProgress() {
        const formData = this.collectFormData();
        if (Object.keys(formData).length === 0) return;

        // Guardar en sessionStorage (compatible con el examen)
        sessionStorage.setItem('nft_exam_progress', JSON.stringify({
            data: formData,
            timestamp: new Date().toISOString(),
            completed: this.completedQuestions
        }));

        // Mostrar notificación de guardado
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
        // Usar el sistema de notificaciones del framework si existe
        if (window.Profins && window.Profins.showNotification) {
            window.Profins.showNotification('Progreso guardado automáticamente', 'success', 2000);
        } else {
            // Fallback: crear notificación simple
            this.createSimpleNotification('💾 Progreso guardado', 'success');
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

    // =================== TIMESTAMPS Y METADATA ===================
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
        // Crear inputs ocultos con timestamps si no existen
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

    // =================== ENVÍO DE FORMULARIO ===================
    handleFormSubmit(e) {
        e.preventDefault();
        
        // Validación final
        if (!this.performFinalValidation()) {
            return;
        }

        // Mostrar loading
        this.showSubmitLoading();
        
        // Agregar timestamp de finalización
        const endTimeInput = document.createElement('input');
        endTimeInput.type = 'hidden';
        endTimeInput.name = 'end_time';
        endTimeInput.value = new Date().toISOString();
        e.target.appendChild(endTimeInput);

        // Limpiar auto-save
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        // Enviar formulario
        setTimeout(() => {
            e.target.submit();
        }, 1000);
    }

    performFinalValidation() {
        let isValid = true;
        const errors = [];

        // Validar todas las preguntas
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
        
        // Usar el modal del framework si existe
        if (window.Profins && window.Profins.showModal) {
            window.Profins.showModal('Validación de Examen', errorMessage);
        } else {
            // Scroll al primer error y mostrar alerta
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

        // Mostrar overlay de loading si el framework lo tiene
        if (window.Profins && window.Profins.showLoading) {
            window.Profins.showLoading('Enviando evaluación...');
        }
    }

    // =================== MÉTODOS PÚBLICOS ===================
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

    // =================== UTILIDADES ===================
    initializeProgressTracking() {
        // Restaurar progreso si existe
        setTimeout(() => {
            this.restoreProgress();
        }, 500);
    }

    initializeValidation() {
        // Validación de formularios usando el framework si existe
        if (window.FormValidator) {
            window.FormValidator.init({
                realTime: true,
                showErrors: true
            });
        }
    }
}

// =================== INICIALIZACIÓN GLOBAL ===================
window.nftExam = new NFTExamSystem();

// Exponer métodos útiles globalmente
window.insertTerm = (textareaName, term) => window.nftExam.insertTerm(textareaName, term);

// Integración con el framework cuando esté listo
document.addEventListener('FrameworkReady', () => {
    console.log('✅ PROFINS XXIV Framework loaded, integrating NFT Exam System...');
    
    // Re-inicializar componentes que dependan del framework
    if (window.AdvancedComponentsManager) {
        window.AdvancedComponentsManager.refreshProgressRings();
    }
});

console.log('✅ NFT Examination System initialized');