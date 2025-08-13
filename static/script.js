/*
 * Frontend interaction logging for the exam application.
 *
 * The script records three categories of events:
 *  1. `start_question`: triggered when a question field gains focus for
 *     the first time. It carries the question index in the details.
 *  2. `end_question`: triggered when focus leaves a question field after
 *     editing. It also records the question index.
 *  3. `paste`: triggered when the user pastes text into a justification
 *     textarea. The question index is recorded in the details as well.
 *
 * All events are queued and posted to the server via fetch calls to
 * `/log_event`. Because the network may be unavailable in this environment
 * (e.g. offline evaluation) the fetch requests ignore errors.
 */

document.addEventListener('DOMContentLoaded', () => {
    const sessionId = window.examSessionId || '';
    if (sessionId) {
        // Track whether each question has already been started.
        const startedQuestions = {};
        // Attach event listeners to textareas for paste and focus/blur logging.
        document.querySelectorAll('fieldset.question-block').forEach(fieldset => {
            const idx = fieldset.getAttribute('data-question-index');
            const textarea = fieldset.querySelector('textarea');
            if (!textarea) return;
            textarea.addEventListener('focus', () => {
                if (!startedQuestions[idx]) {
                    startedQuestions[idx] = true;
                    logEvent('start_question', { question_index: idx });
                }
            });
            textarea.addEventListener('blur', () => {
                logEvent('end_question', { question_index: idx });
            });
            textarea.addEventListener('paste', () => {
                logEvent('paste', { question_index: idx });
            });
        });
    }

    // Apply dynamic score colors for AI analysis
    applyScoreColors();

    function logEvent(type, details) {
        fetch('/log_event', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                event_type: type,
                details: JSON.stringify(details)
            })
        }).catch(() => {
            // Ignore errors; logging is best‑effort.
        });
    }

    function applyScoreColors() {
        // Apply color classes to score elements based on their content
        document.querySelectorAll('.score').forEach(scoreEl => {
            const scoreText = scoreEl.textContent.trim();
            const scoreMatch = scoreText.match(/(\d+)\/5/);
            if (scoreMatch) {
                const score = parseInt(scoreMatch[1]);
                // Remove existing score classes
                scoreEl.classList.remove('score-1', 'score-2', 'score-3', 'score-4', 'score-5');
                // Add appropriate score class
                scoreEl.classList.add(`score-${score}`);
            }
        });
    }
});