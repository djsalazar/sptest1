"""
Core server for the NFTs and Intellectual Property examination application.

Updated for Organismo Judicial de Guatemala with NFT and IP focus.
Password changed to 'organismojudicial'.
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

# Load environment variables from a .env file if present
from dotenv import load_dotenv
load_dotenv()

import requests
from flask import (Flask, g, redirect, render_template, request, session,
                   url_for, flash)

###############################################################################
# Configuration
###############################################################################

# Anthropic API key for Claude integration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Updated instructor password
INSTRUCTOR_PASSWORD = "organismojudicial"

# File path to the SQLite database
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "exam.db"

# Flask setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", ''.join(random.choices(string.ascii_letters + string.digits, k=32)))

# Debug logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(f"🔑 CLAUDE_API_KEY configurado: {'Sí' if CLAUDE_API_KEY else 'No'}")
if CLAUDE_API_KEY:
    print(f"🔑 CLAUDE_API_KEY (primeros 10 chars): {CLAUDE_API_KEY[:10]}...")

###############################################################################
# Data Models
###############################################################################

class Question:
    """Represents a true/false question with rephrasing capabilities."""
    
    def __init__(self, text: str, correct: bool, keywords: List[str]):
        self.text = text
        self.correct = correct
        self.keywords = keywords

    def random_rephrase(self, original_text: str) -> str:
        """Generate random variations to prevent copy-paste."""
        variations = [
            original_text,
            f"Considere lo siguiente: {original_text}",
            f"Analice si es correcto afirmar que: {original_text}",
            f"Desde la perspectiva jurídica: {original_text}"
        ]
        return random.choice(variations)

    def get_text(self) -> str:
        return self.random_rephrase(self.text)

class Case:
    """Representation of a legal case with associated questions."""

    def __init__(self, case_id: int, title: str, description: str, questions: List[Question]):
        self.case_id = case_id
        self.title = title
        self.description = description
        self.questions = questions

# Updated cases focused on NFTs and Intellectual Property
CASES: Dict[int, Case] = {
    1: Case(
        case_id=1,
        title="NFT como Título Traslativo de Dominio",
        description=(
            "Un museo guatemalteco subasta un NFT vinculado a una obra digital inédita. "
            "El comprador sostiene que, por adquirir el NFT, se convierte en 'dueño absoluto' "
            "de los derechos de explotación patrimonial de la obra. El comprador argumenta "
            "que el NFT opera como un título que le transfiere automáticamente todos los "
            "derechos sobre la obra intelectual protegida."
        ),
        questions=[
            Question(
                text=(
                    "El NFT opera jurídicamente como un título traslativo de dominio sobre la "
                    "obra protegida, sin necesidad de cesión expresa según la legislación guatemalteca."
                ),
                correct=False,
                keywords=["NFT", "título traslativo", "cesión expresa", "obra protegida", "art. 3 LPI", "art. 13 LPI"]
            ),
            Question(
                text=(
                    "La compra de un NFT implica automáticamente la adquisición de los derechos "
                    "patrimoniales de la obra intelectual, aplicando el principio de que el soporte "
                    "y la obra son jurídicamente idénticos."
                ),
                correct=False,
                keywords=["derechos patrimoniales", "soporte", "obra intelectual", "separación soporte-obra"]
            ),
        ]
    ),
    2: Case(
        case_id=2,
        title="Smart Contracts y Regalías Automáticas",
        description=(
            "Un artista guatemalteco programa un smart contract ERC-721 que garantiza "
            "regalías del 10% en cada reventa del NFT. El comprador alega que esa cláusula "
            "es inválida porque nunca firmó un contrato físico y que el smart contract "
            "carece de validez jurídica en Guatemala al no cumplir con los requisitos "
            "formales tradicionales."
        ),
        questions=[
            Question(
                text=(
                    "Los smart contracts carecen de validez jurídica en Guatemala porque "
                    "no cumplen con los requisitos formales tradicionales de contratación."
                ),
                correct=False,
                keywords=["smart contracts", "validez jurídica", "requisitos formales", "autonomía de la voluntad"]
            ),
            Question(
                text=(
                    "Las regalías programadas en un smart contract ERC-721 son jurídicamente "
                    "exigibles si se fundamentan en la autonomía de la voluntad contractual "
                    "reconocida por el derecho guatemalteco."
                ),
                correct=True,
                keywords=["regalías", "smart contract", "autonomía de la voluntad", "exigibles"]
            ),
        ]
    ),
    3: Case(
        case_id=3,
        title="Representación Digital vs Reproducción",
        description=(
            "Una galería digital guatemalteca argumenta que al crear NFTs de obras de arte "
            "contemporáneo, no está 'reproduciendo' las obras sino simplemente "
            "'representándolas digitalmente'. Sostienen que la representación digital "
            "en blockchain no constituye una fijación en el sentido del derecho de autor, "
            "por lo que no requieren autorización del titular de derechos."
        ),
        questions=[
            Question(
                text=(
                    "La representación digital de una obra protegida en un NFT constituye "
                    "una reproducción que requiere autorización del titular según el "
                    "derecho guatemalteco."
                ),
                correct=True,
                keywords=["representación digital", "reproducción", "autorización", "art. 9 LPI"]
            ),
            Question(
                text=(
                    "La fijación digital en blockchain no puede considerarse reproducción "
                    "porque no implica una copia física tangible de la obra original."
                ),
                correct=False,
                keywords=["representación digital", "reproducción", "autorización", "fijación digital"]
            ),
        ]
    ),
    4: Case(
        case_id=4,
        title="Uso Público de NFT Musical",
        description=(
            "Un empresario guatemalteco adquiere un NFT de una canción de un artista local "
            "y lo utiliza como pista de ambientación en conciertos públicos remunerados. "
            "El empresario sostiene que la compra del NFT ya le otorga automáticamente "
            "el derecho de comunicación pública de la obra musical."
        ),
        questions=[
            Question(
                text=(
                    "La compra de un NFT de una obra musical incluye implícitamente la licencia "
                    "de comunicación pública según el derecho guatemalteco."
                ),
                correct=False,
                keywords=["comunicación pública", "licencia implícita", "art. 16 LPI", "art. 17 LPI"]
            ),
            Question(
                text=(
                    "Los derechos de comunicación pública son independientes de la propiedad "
                    "del NFT y requieren licencia expresa del titular de derechos patrimoniales."
                ),
                correct=True,
                keywords=["comunicación pública", "licencia expresa", "derechos patrimoniales", "independencia"]
            ),
        ]
    ),
    5: Case(
        case_id=5,
        title="NFT y Derechos Constitucionales",
        description=(
            "Un programador guatemalteco crea y vende NFTs con poemas de autores nacionales "
            "fallecidos hace menos de 50 años, comercializando las obras en plataformas "
            "internacionales. Sostiene que lo hace amparado en el derecho constitucional "
            "de acceso a la cultura (art. 71 CN) y que está promoviendo el patrimonio "
            "cultural guatemalteco."
        ),
        questions=[
            Question(
                text=(
                    "La venta de NFTs de obras literarias protegidas puede justificarse bajo "
                    "el derecho constitucional de acceso a la cultura, prevaleciendo sobre "
                    "los derechos patrimoniales de los herederos."
                ),
                correct=False,
                keywords=["acceso a la cultura", "art. 71 CN", "derechos patrimoniales", "herederos", "art. 42 CN"]
            ),
            Question(
                text=(
                    "Existe un equilibrio constitucional entre el acceso a la cultura y la "
                    "protección del autor, debiendo respetarse los derechos patrimoniales "
                    "durante el término de protección legal."
                ),
                correct=True,
                keywords=["equilibrio constitucional", "protección del autor", "término de protección", "principio de legalidad"]
            ),
        ]
    ),
}

###############################################################################
# Database Functions
###############################################################################

def get_db() -> sqlite3.Connection:
    """Return a SQLite connection tied to the application context."""
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
    """Create the necessary tables if they do not already exist."""
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

###############################################################################
# AI Integration Functions
###############################################################################

def call_claude(prompt: str) -> Optional[str]:
    """Call Claude API for paraphrasing questions."""
    if not CLAUDE_API_KEY:
        return None
    
    try:
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 1000,
                'messages': [
                    {
                        'role': 'user',
                        'content': f"Parafrasea la siguiente pregunta jurídica manteniendo el mismo significado pero con diferentes palabras: {prompt}"
                    }
                ]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()['content'][0]['text']
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
    
    return None

def evaluate_answer_with_ai(user_bool: bool, user_reason: str, correct_bool: bool, 
                           case_description: str, question_text: str) -> Tuple[float, Dict]:
    """Evaluate an answer using AI with detailed rubric."""
    
    # Truth component (5 points)
    truth_score = 5.0 if user_bool == correct_bool else 0.0
    
    # AI evaluation of argument (5 points)
    argument_score = 5.0
    ai_analysis = {}
    feedback = ""
    ai_penalty = 0.0
    
    if CLAUDE_API_KEY:
        try:
            evaluation_prompt = f"""
            Evalúa esta respuesta jurídica sobre NFTs según 9 criterios (escala 1-5):
            
            CASO: {case_description}
            PREGUNTA: {question_text}
            RESPUESTA DEL ESTUDIANTE: {user_reason}
            
            Criterios a evaluar:
            1. Aplicación normativa guatemalteca (1-5) - Aplica correctamente la LPI de Guatemala
            2. Distinción soporte-obra (1-5) - Identifica separación entre soporte digital y obra protegida
            3. Conocimiento de smart contracts (1-5) - Comprende aspectos jurídicos de contratos inteligentes
            4. Derechos patrimoniales y morales (1-5) - Diferencia y aplica derechos morales vs. patrimoniales
            5. Marco constitucional (1-5) - Balancea derechos constitucionales (cultura vs. autor)
            6. Coherencia argumentativa (1-5) - Presenta argumentos lógicos y coherentes
            7. Uso de jurisprudencia/doctrina (1-5) - Referencia apropiada a fuentes doctrinales y legales
            8. Aplicación práctica (1-5) - Conecta teoría con situaciones reales de NFTs
            9. Capacidad crítica jurídica (1-5) - Análisis crítico y fundamentado
            
            Responde SOLO con JSON:
            {{
                "aplicacion_normativa": X,
                "distincion_soporte_obra": X,
                "smart_contracts": X,
                "derechos_patrimoniales_morales": X,
                "marco_constitucional": X,
                "coherencia_argumentativa": X,
                "jurisprudencia_doctrina": X,
                "aplicacion_practica": X,
                "capacidad_critica": X,
                "promedio": X.X,
                "feedback": "comentario breve"
            }}
            """
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': CLAUDE_API_KEY,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-3-sonnet-20240229',
                    'max_tokens': 1500,
                    'messages': [{'role': 'user', 'content': evaluation_prompt}]
                },
                timeout=15
            )
            
            if response.status_code == 200:
                ai_response = response.json()['content'][0]['text']
                try:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        ai_result = json.loads(json_match.group())
                        ai_analysis = ai_result
                        argument_score = ai_result.get('promedio', 2.5) * 5  # Convert to 5-point scale
                        feedback = ai_result.get('feedback', '')
                except Exception as e:
                    logger.error(f"Error parsing AI evaluation: {e}")
                    argument_score = 3.0
                    
        except Exception as e:
            logger.error(f"Error evaluating with AI: {e}")
            argument_score = 3.0
    else:
        # Basic evaluation without AI
        argument_score = 3.0 if len(user_reason.strip()) >= 50 else 1.0
    
    # Calculate total score
    total_score = truth_score + argument_score + ai_penalty
    total_score = max(0.0, min(10.0, total_score))  # Clamp to 0-10
    
    breakdown = {
        'truth': truth_score,
        'argument': argument_score,
        'ai_penalty': ai_penalty,
        'ai_analysis': ai_analysis,
        'feedback': feedback
    }
    
    return total_score, breakdown

###############################################################################
# Routes
###############################################################################

@app.route('/')
def index() -> str:
    """Landing page."""
    return render_template('student_form.html')

@app.route('/start_exam', methods=['POST'])
def start_exam() -> str:
    """Process student registration and start exam."""
    student_name = request.form.get('student_name', '').strip()
    student_carne = request.form.get('student_carne', '').strip()
    
    if not student_name or not student_carne:
        flash("Debe completar todos los campos")
        return redirect(url_for('index'))
    
    # Store in session
    session['student_name'] = student_name
    session['student_carne'] = student_carne
    
    return redirect(url_for('take_comprehensive_exam'))

@app.route('/comprehensive_exam')
def take_comprehensive_exam() -> str:
    """Display comprehensive exam with all cases."""
    if 'student_name' not in session or 'student_carne' not in session:
        flash("Debe registrar sus datos primero")
        return redirect(url_for('index'))
    
    # Prepare all cases with potentially paraphrased questions
    all_cases_data = []
    
    for case_id, case in CASES.items():
        case_questions = []
        for question in case.questions:
            # Try to get paraphrased question, fallback to original
            paraphrased = call_claude(question.text)
            final_question_text = paraphrased if paraphrased else question.get_text()
            case_questions.append(final_question_text)
        
        all_cases_data.append({
            'case': case,
            'questions': case_questions
        })
    
    return render_template(
        'comprehensive_exam.html',
        all_cases_data=all_cases_data,
        student_name=session.get('student_name'),
        student_carne=session.get('student_carne')
    )

@app.route('/submit_comprehensive', methods=['POST'])
def submit_comprehensive() -> str:
    """Process comprehensive exam submission."""
    if 'student_name' not in session or 'student_carne' not in session:
        flash("Sesión expirada. Debe registrarse nuevamente.")
        return redirect(url_for('index'))
    
    timestamp = datetime.now().isoformat()
    student_name = session.get('student_name')
    student_carne = session.get('student_carne')
    student_id = f"{student_carne} - {student_name}"
    
    # Process all cases
    all_answers = []
    total_score = 0.0
    paste_penalty = 0.0
    pending_events = []
    
    for case_id, case in CASES.items():
        case_answers = []
        case_score = 0.0
        
        for q_index, question in enumerate(case.questions):
            bool_key = f"q_{case_id}_{q_index}_bool"
            reason_key = f"q_{case_id}_{q_index}_reason"
            
            user_bool_str = request.form.get(bool_key, '').strip()
            user_reason = request.form.get(reason_key, '').strip()
            
            if not user_bool_str or not user_reason:
                flash(f"Pregunta incompleta en Caso {case_id}")
                return redirect(url_for('take_comprehensive_exam'))
            
            user_bool = user_bool_str == 'True'
            
            # Evaluate answer
            question_score, breakdown = evaluate_answer_with_ai(
                user_bool, user_reason, question.correct, case.description, question.text
            )
            
            case_answers.append({
                'question_text': question.text,
                'user_bool': user_bool,
                'user_reason': user_reason,
                'correct_bool': question.correct,
                'score': question_score,
                'breakdown': breakdown
            })
            
            case_score += question_score
        
        all_answers.append({
            'case': case,
            'answers': case_answers,
            'score': case_score
        })
        
        total_score += case_score
    
    # Store in database
    db = get_db()
    cur = db.cursor()
    
    answers_json = json.dumps({
        'student_name': student_name,
        'student_carne': student_carne,
        'all_cases': {str(case_data['case'].case_id): {
            'answers': case_data['answers']
        } for case_data in all_answers}
    })
    
    rubric_json = json.dumps({'total_score': total_score, 'paste_penalty': paste_penalty})
    
    cur.execute(
        "INSERT INTO results (timestamp, student_id, case_id, answers_json, score, rubric_json) VALUES (?, ?, ?, ?, ?, ?)",
        (timestamp, student_id, 0, answers_json, total_score, rubric_json)  # case_id = 0 for comprehensive
    )
    result_id = cur.lastrowid
    
    # Persist logs
    for ev in pending_events:
        cur.execute(
            "INSERT INTO events (result_id, event_type, event_time, details) VALUES (?, ?, ?, ?)",
            (result_id, ev['event_type'], ev['timestamp'], ev.get('details', ''))
        )
    db.commit()
    
    # Clear session data
    session.pop('student_session', None)
    
    return render_template(
        'comprehensive_feedback.html',
        all_cases_data=all_answers,
        cases=CASES,
        total_score=total_score,
        paste_penalty=paste_penalty,
        student_name=session.get('student_name'),
        student_carne=session.get('student_carne')
    )

###############################################################################
# Routes for instructors
###############################################################################

@app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    """Login page for instructors. Updated password: 'organismojudicial'"""
    if request.method == 'POST':
        if request.form.get('password') == INSTRUCTOR_PASSWORD:
            session['instructor'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Contraseña incorrecta")
    return render_template('login.html')

def require_instructor(view_func):
    """Decorator that ensures the current user is logged in as an instructor."""
    def wrapped(*args, **kwargs):
        if not session.get('instructor'):
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    wrapped.__name__ = view_func.__name__
    return wrapped

@app.route('/dashboard')
@require_instructor
def dashboard() -> str:
    """Display a dashboard summarizing all results."""
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, timestamp, student_id, case_id, score FROM results ORDER BY timestamp DESC"
    )
    rows = cur.fetchall()
    
    # Build aggregated statistics
    scores = [row['score'] for row in rows]
    average_score = sum(scores) / len(scores) if scores else 0.0
    passing_rate = len([s for s in scores if s >= 60]) / len(scores) * 100 if scores else 0.0
    
    return render_template(
        'dashboard.html',
        results=rows,
        cases=CASES,
        average_score=average_score,
        passing_rate=passing_rate,
    )

@app.route('/logout')
def logout() -> str:
    """Log the instructor out and redirect to the login page."""
    session.pop('instructor', None)
    return redirect(url_for('login'))

@app.route('/result/<int:result_id>')
@require_instructor  
def view_result(result_id: int) -> str:
    """Show details of a single submission including per-question scores."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM results WHERE id = ?", (result_id,))
    result = cur.fetchone()
    if not result:
        return "Resultado no encontrado", 404
    
    try:
        answers_data = json.loads(result['answers_json'])
        rubric_data = json.loads(result['rubric_json'])
        
        if result['case_id'] == 0:
            # Comprehensive exam
            student_name = answers_data.get('student_name', 'N/A')
            student_carne = answers_data.get('student_carne', 'N/A')
            all_cases_answers = answers_data.get('all_cases', {})
            
            # Retrieve event logs
            cur.execute(
                "SELECT event_type, event_time, details FROM events WHERE result_id = ?",
                (result_id,)
            )
            events = cur.fetchall()
            
            return render_template(
                'result.html',
                result=result,
                all_cases_answers=all_cases_answers,
                cases=CASES,
                total_score=result['score'],
                events=events,
                student_name=student_name,
                student_carne=student_carne
            )
        else:
            # Individual exam (legacy)
            return render_template(
                'result.html',
                result=result,
                cases=CASES,
                answers=json.loads(result['answers_json']),
                events=[]
            )
    
    except Exception as e:
        logger.error(f"Error processing result {result_id}: {e}")
        return f"Error procesando resultado: {str(e)}", 500

@app.route('/info')
def info():
    """Página de información del sistema."""
    return render_template('info.html')

###############################################################################
# Utility Functions and Filters
###############################################################################

def flatten_filter(nested_list):
    """Flatten nested lists for Jinja2 templates."""
    if not nested_list:
        return []
    
    result = []
    for item in nested_list:
        if isinstance(item, (list, tuple)):
            result.extend(flatten_filter(item))
        else:
            result.append(item)
    return result

def from_json_filter(json_string):
    """Filtro para convertir JSON string a dict en templates"""
    try:
        return json.loads(json_string) if json_string else {}
    except:
        return {}

# Register filters
app.jinja_env.filters['flatten'] = flatten_filter
app.jinja_env.filters['from_json'] = from_json_filter

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

###############################################################################
# App startup
###############################################################################

if __name__ == '__main__':
    print("🚀 Iniciando aplicación NFTs y Propiedad Intelectual...")
    print("🏛️ Organismo Judicial de Guatemala")
    print("🔐 Password de instructor: organismojudicial")
    app.run(host='0.0.0.0', port=8000, debug=True)