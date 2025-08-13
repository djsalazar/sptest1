"""
Core server for the monolithic examination application.

This application serves two primary audiences:

1. **Students** – They access a test page that displays a case study with a
   series of true/false questions. Each question is slightly rephrased at
   runtime to avoid rote copying. Students supply a boolean answer and a
   written justification. The frontend records how long the student
   deliberates per question and whether the student pastes text into any
   answer. When the test is submitted, the application immediately grades
   the submission according to a pre‑defined rubric and returns the score
   alongside actionable feedback. All interactions are stored in a
   SQLite database for later review.

2. **Instructors** – They log in through a simple password‑protected page
   (password defined in the specification: ``S4nPablo2025``) to view all
   submissions, browse individual responses, inspect event logs (for
   example, paste events), and review aggregated statistics.

The application is intentionally straightforward and self‑contained. It
uses only Flask and SQLite for persistence, making it feasible to build
and deploy within a couple of hours. The code also includes a stub for
integrating Anthropic’s Claude API should an API key be provided in the
environment, although the application does not depend on it for core
functionality.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Load environment variables from a .env file if present. This allows
# operators to provide sensitive settings like API keys without
# embedding them directly in the source code or passing them on the
# command line. Only call this at import time so that overriding
# environment variables still take precedence.
from dotenv import load_dotenv

load_dotenv()

import requests
from flask import (Flask, g, redirect, render_template, request, session,
                   url_for)


###############################################################################
# Configuration
###############################################################################

# When set, this environment variable should contain a valid Anthropic API
# key. The ``call_claude`` function uses it to paraphrase questions.
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Instructor password. In a production deployment this should be stored in
# configuration or environment rather than hard‑coded. For this exercise
# we follow the specification.
INSTRUCTOR_PASSWORD = "S4nPablo2025"

# File path to the SQLite database. Stored relative to this file.
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "exam.db"

# Flask setup
app = Flask(__name__)
# Secret key is required for sessions; generate a random value if none
app.secret_key = os.getenv("SECRET_KEY", ''.join(random.choices(string.ascii_letters + string.digits, k=32)))


###############################################################################
# Utility functions
###############################################################################

def get_db() -> sqlite3.Connection:
    """Return a SQLite connection tied to the application context.

    The connection is stored on the Flask `g` object so that it can be
    reused across requests. The database is automatically initialized on
    first access.
    """
    db: Optional[sqlite3.Connection] = getattr(g, '_database', None)
    if db is None:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        g._database = db
        ensure_schema(db)
    return db


@app.teardown_appcontext
def close_connection(exception: Optional[BaseException]) -> None:
    """Close the database connection when the app context tears down."""
    db: Optional[sqlite3.Connection] = getattr(g, '_database', None)
    if db is not None:
        db.close()


def ensure_schema(db: sqlite3.Connection) -> None:
    """
    Create the necessary tables if they do not already exist. The schema
    includes:

    - ``results``: Each test submission from a student. Contains
      identifiers, timestamps, aggregated scores and raw JSON for per‑question
      grading details.
    - ``events``: Logs of notable frontend interactions (question start,
      question end, paste events) for each submission.
    """
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            student_id TEXT,
            case_id INTEGER NOT NULL,
            answers_json TEXT NOT NULL,
            score REAL NOT NULL,
            rubric_json TEXT NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER,
            event_type TEXT NOT NULL,
            event_time TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY (result_id) REFERENCES results(id)
        );
        """
    )
    db.commit()


def call_claude(prompt: str) -> Optional[str]:
    """
    Attempt to paraphrase the given prompt using Anthropic's API. If the
    ``CLAUDE_API_KEY`` environment variable is not set or the request
    fails, return ``None``. This function intentionally does not raise
    exceptions so that the rest of the application can continue running.

    Parameters
    ----------
    prompt: str
        Text to send to the Anthropic API for paraphrasing.

    Returns
    -------
    Optional[str]
        A paraphrased version of the prompt if successful, otherwise ``None``.
    """
    if not CLAUDE_API_KEY:
        return None
    # Construct the API request for Claude. The Anthropic v1 completions
    # endpoint expects a JSON payload with ``prompt`` and ``max_tokens``.
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/complete",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "content-type": "application/json"
            },
            json={
                "prompt": f"Human: Paraphrase the following question while keeping the meaning unchanged: '{prompt}'\nAssistant:",
                "model": "claude-2",
                "max_tokens": 64,
                "temperature": 0.5,
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # The API returns the completion in the ``completion`` field.
            paraphrased = data.get("completion", '').strip()
            return paraphrased if paraphrased else None
    except Exception:
        pass
    return None


def random_rephrase(question: str) -> str:
    """
    Generate a non‑trivial rephrasing of a question. The function first
    attempts to use Anthropic’s API. If that fails or no API key is
    configured, it falls back to a simple templated substitution that
    preserves meaning. The fallback uses a handful of pre‑defined synonyms
    to vary the text without altering its truth conditions.
    """
    # Try to call Anthropic for paraphrasing
    rephrased = call_claude(question)
    if rephrased:
        return rephrased
    # Local fallback: replace phrases with synonyms and adjust word order
    synonyms = {
        "afirma": ["sostiene", "asegura", "declara"],
        "comunidad": ["colectividad", "grupo indígena"],
        "marca": ["signo distintivo", "registro"],
        "patente": ["título", "registro de patente"],
        "puede": ["es posible", "podría"]
    }
    tokens = question.split()
    new_tokens = []
    for tok in tokens:
        base = tok.lower().strip('.,?')
        if base in synonyms and random.random() < 0.5:
            # choose a synonym preserving punctuation and capitalisation
            synonym = random.choice(synonyms[base])
            if tok[0].isupper():
                synonym = synonym.capitalize()
            # preserve trailing punctuation
            punct = '' if tok[-1].isalnum() else tok[-1]
            new_tokens.append(synonym + punct)
        else:
            new_tokens.append(tok)
    # Shuffle the order of some phrases to avoid identical phrasing. We
    # selectively swap two adjacent tokens with a low probability.
    i = 0
    while i < len(new_tokens) - 1:
        if random.random() < 0.1:
            new_tokens[i], new_tokens[i+1] = new_tokens[i+1], new_tokens[i]
            i += 1
        i += 1
    return ' '.join(new_tokens)


def evaluate_answer(user_bool: bool, user_reason: str,
                    correct_bool: bool, case_keywords: List[str]) -> Tuple[float, Dict[str, float]]:
    """
    Compute a numeric score and per‑criterion breakdown for a single
    true/false answer and its justification.

    The rubric allocates points as follows:

    - **Truthfulness (50 pts)**: Awarded if the user's boolean answer
      matches the correct answer.
    - **Argumentation quality (40 pts)**: Based on length, the presence of
      discourse markers, and the inclusion of keywords from the case. The
      score scales up to 40 points.
    - **AI usage penalty (−10 pts)**: Deducted if the answer contains
      obvious indicators of generative AI usage (e.g. names of AI models
      or unnatural phrasing). A penalty cannot push the total below zero.
    - **Paste penalty (−10 pts)**: The paste penalty is not applied here
      because paste detection is handled separately in ``finalise_result``.

    Parameters
    ----------
    user_bool: bool
        The student's selected boolean (True/False).
    user_reason: str
        Free‑form text justification provided by the student.
    correct_bool: bool
        The correct answer for the question.
    case_keywords: List[str]
        A list of keywords relevant to the underlying case. Used to
        gauge whether the student is referencing the case in their
        justification.

    Returns
    -------
    float
        The total score for the answer.
    Dict[str, float]
        A breakdown of scores by criterion.
    """
    scores: Dict[str, float] = {
        "truth": 0.0,
        "argument": 0.0,
        "ai_penalty": 0.0,
    }
    # Truthfulness
    if user_bool == correct_bool:
        scores["truth"] = 50.0

    # Argumentation quality
    reason = user_reason.strip()
    word_count = len(reason.split())
    # Points for length: full marks for 50–150 words, proportional below
    if word_count < 20:
        length_factor = 0.0
    elif word_count <= 150:
        length_factor = (word_count - 20) / 130  # linear scale from 0 to ~1
    else:
        length_factor = 1.0

    # Points for discourse markers
    markers = ["porque", "sin embargo", "por lo tanto", "no obstante", "por consiguiente"]
    marker_hits = sum(1 for m in markers if m in reason.lower())
    marker_factor = min(marker_hits / len(markers), 1.0)

    # Points for keywords
    keyword_hits = sum(1 for kw in case_keywords if kw.lower() in reason.lower())
    keyword_factor = min(keyword_hits / max(len(case_keywords), 1), 1.0)

    argument_score = (length_factor * 0.4 + marker_factor * 0.3 + keyword_factor * 0.3) * 40.0
    scores["argument"] = argument_score

    # AI usage penalty
    ai_indicators = ["chatgpt", "gpt", "inteligencia artificial", "ia generativa", "modelo de lenguaje"]
    if any(ind in reason.lower() for ind in ai_indicators):
        scores["ai_penalty"] = -10.0

    total = max(scores["truth"] + scores["argument"] + scores["ai_penalty"], 0.0)
    return total, scores


###############################################################################
# Case and question definitions
###############################################################################

class Question:
    """Representation of a true/false question tied to a case."""

    def __init__(self, text: str, correct: bool, keywords: List[str]):
        self.text = text
        self.correct = correct
        self.keywords = keywords

    def rephrased(self) -> str:
        """Return a rephrased version of the question."""
        return random_rephrase(self.text)


class Case:
    """Representation of a legal case with associated questions."""

    def __init__(self, case_id: int, title: str, description: str, questions: List[Question]):
        self.case_id = case_id
        self.title = title
        self.description = description
        self.questions = questions


# Define the cases and their questions. For brevity the descriptions and
# keyword lists are simplified. In a real deployment you might load these
# from a JSON file or database.
CASES: Dict[int, Case] = {
    1: Case(
        case_id=1,
        title="Conocimientos Tradicionales y Patentes (México)",
        description=(
            "Una empresa mexicana sintetizó un compuesto químico basado en un conocimiento tradicional "
            "de una comunidad indígena. La empresa no divulgó el origen del recurso ni solicitó el consentimiento "
            "previo de la comunidad. Se cuestiona la patentabilidad y la participación en los beneficios."
        ),
        questions=[
            Question(
                text=(
                    "Aunque el compuesto sintetizado sea nuevo y cumpla con los requisitos de patentabilidad, "
                    "la falta de divulgación del origen del recurso y del consentimiento de la comunidad no afecta la "
                    "concesión de la patente."
                ),
                correct=False,
                keywords=["divulgación", "consentimiento", "comunidad", "patentabilidad"]
            ),
            Question(
                text=(
                    "La comunidad puede reclamar una participación en los beneficios incluso si la patente se concede, "
                    "basándose en principios de equidad y justicia."
                ),
                correct=True,
                keywords=["beneficios", "equidad", "justicia", "comunidad"]
            ),
        ]
    ),
    2: Case(
        case_id=2,
        title="Expresiones Culturales y Marcas (Guatemala)",
        description=(
            "Un comerciante intenta registrar como marca un símbolo sagrado de la cosmovisión maya "
            "para vender productos textiles. La comunidad considera que el uso es ofensivo y contrario "
            "al orden público."
        ),
        questions=[
            Question(
                text=(
                    "Un símbolo sagrado no tiene protección marcaria si no existe una prohibición explícita en la ley "
                    "de marcas, por lo tanto cualquier persona puede registrarlo como marca."
                ),
                correct=False,
                keywords=["símbolo", "sagrado", "orden público", "marca"]
            ),
            Question(
                text=(
                    "La comunidad maya puede pedir la nulidad del registro por considerarlo contrario a las buenas costumbres "
                    "y al orden público."
                ),
                correct=True,
                keywords=["nulidad", "buenas costumbres", "orden público", "comunidad"]
            ),
        ]
    ),
    3: Case(
        case_id=3,
        title="Recursos Genéticos y Biopiratería (México)",
        description=(
            "Una empresa japonesa obtuvo una patente sobre un microorganismo aislado de un cenote mexicano. "
            "México no fue consultado ni compensado. Se analiza la validez de la patente y la posibilidad de "
            "reclamar derechos."
        ),
        questions=[
            Question(
                text=(
                    "México tiene derecho automático a una compensación económica por la patente concedida en Japón solo "
                    "por el hecho de que el recurso genético se originó en México."
                ),
                correct=False,
                keywords=["compensación", "recurso genético", "México", "patente"]
            ),
            Question(
                text=(
                    "México puede impugnar la patente en Japón si demuestra que el microorganismo no es novedoso "
                    "y que su uso estaba documentado en conocimientos tradicionales."
                ),
                correct=True,
                keywords=["impugnar", "novedoso", "conocimientos tradicionales", "México"]
            ),
        ]
    ),
    4: Case(
        case_id=4,
        title="Protección Preventiva y Nombres Geográficos (Guatemala)",
        description=(
            "Un tercero registró como dominio .gt el nombre de un sitio arqueológico reconocido, con el "
            "objetivo de monetizar la reputación del patrimonio cultural. El Ministerio de Cultura pretende intervenir."
        ),
        questions=[
            Question(
                text=(
                    "El Ministerio de Cultura no puede solicitar la cancelación del dominio porque no posee un "
                    "derecho de propiedad intelectual sobre el nombre."
                ),
                correct=False,
                keywords=["Ministerio de Cultura", "cancelación", "dominio", "patrimonio"]
            ),
            Question(
                text=(
                    "Registrar un dominio que reproduce el nombre de un sitio arqueológico para beneficio propio "
                    "puede considerarse una práctica desleal."
                ),
                correct=True,
                keywords=["práctica desleal", "dominio", "patrimonio", "cultural"]
            ),
        ]
    ),
    5: Case(
        case_id=5,
        title="Tratado Internacional y Conocimientos Tradicionales (Guatemala)",
        description=(
            "Una empresa extranjera solicitó patente en Guatemala antes de la entrada en vigor del nuevo Tratado de la "
            "OMPI sobre PI, Recursos Genéticos y Conocimientos Tradicionales. La solicitud no menciona el origen "
            "ni consentimiento."
        ),
        questions=[
            Question(
                text=(
                    "La entrada en vigor del nuevo Tratado de la OMPI hace obligatoria la divulgación del origen "
                    "incluso para solicitudes anteriores a su vigencia."
                ),
                correct=False,
                keywords=["Tratado", "divulgación", "solicitud", "vigencia"]
            ),
            Question(
                text=(
                    "El Estado de Guatemala puede exigir compensación a pesar de que la solicitud no mencione el origen "
                    "ni consentimiento, basándose en principios de equidad y justicia."
                ),
                correct=True,
                keywords=["compensación", "equidad", "justicia", "Guatemala"]
            ),
        ]
    ),
}


###############################################################################
# Routes for students
###############################################################################

@app.route('/')
def index() -> str:
    """Landing page redirects to the test for the first case by default."""
    return redirect(url_for('take_test', case_id=1))


@app.route('/test/<int:case_id>', methods=['GET'])
def take_test(case_id: int) -> str:
    """
    Display the test page for a given case. The questions are rephrased on
    each load to discourage rote memorisation. A unique ``session_id`` is
    generated and stored in the session to associate events and results.
    """
    case = CASES.get(case_id)
    if not case:
        return "Case not found", 404
    # Generate a short session identifier to tie logs and results together
    # across the life of the test. This is not used for security and is
    # distinct from Flask's session ID.
    if 'student_session' not in session:
        session['student_session'] = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    rephrased_questions = [q.rephrased() for q in case.questions]
    return render_template(
        'test.html',
        case=case,
        questions=rephrased_questions,
        session_id=session['student_session']
    )


@app.route('/log_event', methods=['POST'])
def log_event() -> str:
    """
    Receive a frontend log event. Events include 'start_question', 'end_question'
    and 'paste'. Logs are stored in the ``events`` table. The payload must
    include a ``session_id`` corresponding to the current student session.
    The server defers committing the result_id until a test is submitted;
    interim logs are temporarily stored in the session.
    """
    data = request.get_json(silent=True) or {}
    event_type = data.get('event_type')
    details = data.get('details', '')
    timestamp = datetime.utcnow().isoformat()
    # Append to session logs for later association
    logs = session.setdefault('pending_events', [])
    logs.append({
        'event_type': event_type,
        'timestamp': timestamp,
        'details': details,
    })
    session['pending_events'] = logs
    return 'ok'


@app.route('/submit', methods=['POST'])
def submit() -> str:
    """
    Process the student's submission. Compute scores for each question,
    aggregate them, store the result and any pending event logs, then
    render the feedback page.
    """
    case_id = int(request.form.get('case_id', 0))
    case = CASES.get(case_id)
    if not case:
        return "Case not found", 404
    # Retrieve boolean answers and justifications
    answers: List[Dict[str, any]] = []
    total_score = 0.0
    rubric_breakdown: List[Dict[str, any]] = []
    for idx, q in enumerate(case.questions):
        bool_str = request.form.get(f'bool_{idx}', 'false')
        user_bool = bool_str.lower() == 'true'
        user_reason = request.form.get(f'reason_{idx}', '').strip()
        score, breakdown = evaluate_answer(
            user_bool=user_bool,
            user_reason=user_reason,
            correct_bool=q.correct,
            case_keywords=q.keywords
        )
        # If paste events occurred during this question, apply a penalty
        # by reducing the score by 10. Paste events are counted globally per
        # session and applied evenly across all questions.
        answers.append({
            'user_bool': user_bool,
            'user_reason': user_reason,
            'correct': q.correct,
            'score': score,
            'breakdown': breakdown,
        })
        total_score += score
        rubric_breakdown.append(breakdown)
    # Apply paste penalties if any were recorded for this session
    pending_events = session.pop('pending_events', [])
    paste_events = [ev for ev in pending_events if ev.get('event_type') == 'paste']
    paste_penalty = len(paste_events) * 10.0 / max(len(case.questions), 1)
    total_score = max(total_score - paste_penalty, 0.0)
    # Save the result to the database
    db = get_db()
    timestamp = datetime.utcnow().isoformat()
    student_id = session.get('student_session', '')
    answers_json = json.dumps(answers)
    rubric_json = json.dumps({
        'question_breakdown': rubric_breakdown,
        'paste_penalty': paste_penalty,
    })
    cur = db.cursor()
    cur.execute(
        "INSERT INTO results (timestamp, student_id, case_id, answers_json, score, rubric_json) VALUES (?, ?, ?, ?, ?, ?)",
        (timestamp, student_id, case_id, answers_json, total_score, rubric_json)
    )
    result_id = cur.lastrowid
    # Persist logs
    for ev in pending_events:
        cur.execute(
            "INSERT INTO events (result_id, event_type, event_time, details) VALUES (?, ?, ?, ?)",
            (result_id, ev['event_type'], ev['timestamp'], ev.get('details', ''))
        )
    db.commit()
    # Clear session data tied to this test
    session.pop('student_session', None)
    # Render feedback
    return render_template(
        'feedback.html',
        case=case,
        answers=answers,
        total_score=total_score,
        paste_penalty=paste_penalty,
    )


###############################################################################
# Routes for instructors
###############################################################################

@app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    """
    Simple login page for instructors. Accepts a POST with ``password`` and
    establishes a session flag ``instructor`` when the password matches
    ``INSTRUCTOR_PASSWORD``.
    """
    if request.method == 'POST':
        if request.form.get('password') == INSTRUCTOR_PASSWORD:
            session['instructor'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Contraseña incorrecta")
    return render_template('login.html')


def require_instructor(view_func):
    """
    Decorator that ensures the current user is logged in as an instructor.
    Redirects to the login page if not authenticated.
    """
    def wrapped(*args, **kwargs):
        if not session.get('instructor'):
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    wrapped.__name__ = view_func.__name__
    return wrapped


@app.route('/dashboard')
@require_instructor
def dashboard() -> str:
    """
    Display a dashboard summarising all results. Each row includes a
    timestamp, student ID, case title, total score and a link to view
    details. Basic statistics are also provided.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, timestamp, student_id, case_id, score FROM results ORDER BY timestamp DESC"
    )
    rows = cur.fetchall()
    # Build aggregated statistics
    scores = [row['score'] for row in rows]
    average_score = sum(scores) / len(scores) if scores else 0.0
    return render_template(
        'dashboard.html',
        results=rows,
        cases=CASES,
        average_score=average_score,
    )


@app.route('/logout')
def logout() -> str:
    """Log the instructor out and redirect to the login page."""
    session.pop('instructor', None)
    return redirect(url_for('login'))


@app.route('/result/<int:result_id>')
@require_instructor
def view_result(result_id: int) -> str:
    """
    Show details of a single submission including per‑question scores,
    justification texts and event logs.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM results WHERE id = ?", (result_id,))
    result = cur.fetchone()
    if not result:
        return "Resultado no encontrado", 404
    answers = json.loads(result['answers_json'])
    rubric_data = json.loads(result['rubric_json'])
    # Retrieve event logs
    cur.execute(
        "SELECT event_type, event_time, details FROM events WHERE result_id = ? ORDER BY event_time",
        (result_id,)
    )
    events = cur.fetchall()
    return render_template(
        'result.html',
        result=result,
        answers=answers,
        rubric=rubric_data,
        events=events,
        case=CASES.get(result['case_id'])
    )


###############################################################################
# Run the app
###############################################################################

if __name__ == '__main__':
    # Create database directory if necessary
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Launch the Flask development server for local testing. When
    # containerised, the command in the Dockerfile starts the app.
    app.run(host='0.0.0.0', port=8000, debug=False)