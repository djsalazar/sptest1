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
                    "El contrato inteligente carece de efectos jurídicos en Guatemala, ya que "
                    "no cumple con la forma escrita exigida por la Ley de Propiedad Intelectual "
                    "para pactar regalías."
                ),
                correct=False,
                keywords=["smart contract", "forma escrita", "LPI", "regalías", "Ley de Firma Electrónica"]
            ),
            Question(
                text=(
                    "Los smart contracts pueden tener plena validez jurídica en Guatemala bajo "
                    "el principio de equivalencia funcional de la firma electrónica avanzada y "
                    "la autonomía de la voluntad contractual."
                ),
                correct=True,
                keywords=["equivalencia funcional", "firma electrónica avanzada", "autonomía de la voluntad"]
            ),
        ]
    ),
    3: Case(
        case_id=3,
        title="Tokenización de Obra Física Sin Autorización",
        description=(
            "Un marchante de arte emite un NFT que representa un cuadro físico de un autor "
            "guatemalteco vivo, sin autorización del creador, y lo vende en OpenSea. "
            "El comprador alega que como se trata de una 'representación digital' del cuadro "
            "y no la obra física en sí, no hay infracción de derechos de autor."
        ),
        questions=[
            Question(
                text=(
                    "La tokenización de una obra plástica sin autorización constituye infracción "
                    "a los derechos morales y patrimoniales del autor según la legislación guatemalteca."
                ),
                correct=True,
                keywords=["tokenización", "autorización", "derechos morales", "derechos patrimoniales", "art. 9 LPI"]
            ),
            Question(
                text=(
                    "La representación digital de una obra física no requiere autorización del autor "
                    "si se trata únicamente de un NFT y no de la reproducción de la obra original."
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
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 200,
                "messages": [
                    {
                        "role": "user", 
                        "content": f"""Parafrasea la siguiente pregunta legal sobre NFTs manteniendo EXACTAMENTE el mismo significado y estructura lógica. 
Solo cambia algunas palabras por sinónimos y ajusta levemente la redacción, pero conserva la claridad y coherencia:

"{prompt}"

Responde ÚNICAMENTE con la pregunta parafraseada, sin explicaciones adicionales."""
                    }
                ]
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            paraphrased = data["content"][0]["text"].strip()
            
            if paraphrased and len(paraphrased) > 50 and len(paraphrased) < len(prompt) * 2:
                return paraphrased
            else:
                return None
        else:
            print(f"Error API Claude: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Excepción en call_claude: {e}")
        return None


def analyze_argumentation_with_claude(user_reason: str, case_context: str, 
                                    question_text: str, user_bool: bool, correct_bool: bool) -> Dict[str, any]:
    """Use Claude API to analyze argumentation quality for NFTs and IP."""
    
    if not CLAUDE_API_KEY:
        raise Exception("CLAUDE_API_KEY no configurado")
    
    prompt = f"""Eres un profesor experto en NFTs y propiedad intelectual. 
Evalúa la siguiente argumentación de un estudiante usando la rúbrica proporcionada.

CONTEXTO DEL CASO:
{case_context}

PREGUNTA:
{question_text}

RESPUESTA DEL ESTUDIANTE: {"Verdadero" if user_bool else "Falso"}
RESPUESTA CORRECTA: {"Verdadero" if correct_bool else "Falso"}

ARGUMENTACIÓN DEL ESTUDIANTE:
{user_reason}

RÚBRICA DE EVALUACIÓN (escala 1-5 para cada criterio):

1. Comprensión conceptual NFT (1-5) - Demuestra comprensión de NFT vs. obra intelectual
2. Aplicación normativa guatemalteca (1-5) - Aplica correctamente la LPI de Guatemala
3. Distinción soporte-obra (1-5) - Identifica separación entre soporte digital y obra protegida
4. Conocimiento de smart contracts (1-5) - Comprende aspectos jurídicos de contratos inteligentes
5. Derechos patrimoniales y morales (1-5) - Diferencia y aplica derechos morales vs. patrimoniales
6. Marco constitucional (1-5) - Balancea derechos constitucionales (cultura vs. autor)
7. Coherencia argumentativa (1-5) - Presenta argumentos lógicos y coherentes
8. Uso de jurisprudencia/doctrina (1-5) - Referencia apropiada a fuentes doctrinales y legales
9. Aplicación práctica (1-5) - Conecta teoría con situaciones reales de NFTs

INSTRUCCIONES:
1. Evalúa cada criterio con una puntuación de 1-5
2. Calcula el promedio de los 9 criterios y multiplícalo por 5 para obtener la puntuación sobre 5 puntos
3. Proporciona feedback específico y constructivo sobre NFTs y propiedad intelectual

Responde ÚNICAMENTE en este formato JSON:
{{
    "comprension_nft": X,
    "aplicacion_normativa": X,
    "distincion_soporte": X,
    "smart_contracts": X,
    "derechos_patrimoniales": X,
    "marco_constitucional": X,
    "coherencia": X,
    "jurisprudencia": X,
    "aplicacion_practica": X,
    "score": X.X,
    "feedback": "Texto específico sobre NFTs y PI..."
}}"""
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = data["content"][0]["text"].strip()
            
            try:
                analysis = json.loads(response_text)
                return analysis
            except json.JSONDecodeError:
                print(f"Error parsing JSON: {response_text}")
                return {"error": "Invalid JSON response"}
        else:
            print(f"Claude API error: {response.status_code}")
            return {"error": f"API error: {response.status_code}"}
            
    except Exception as e:
        print(f"Exception in analyze_argumentation_with_claude: {e}")
        return {"error": str(e)}


###############################################################################
# Evaluation Functions
###############################################################################

def evaluate_answer_with_ai(user_bool: bool, user_reason: str, correct_bool: bool, 
                           case_context: str, question_text: str) -> Tuple[float, Dict[str, any]]:
    """
    Evaluate answer using AI for NFT and IP argumentation analysis.
    Total per question: 10 points (5 for truth + 5 for argumentation)
    """
    print(f"\n=== EVALUANDO RESPUESTA NFT ===")
    print(f"Pregunta: {question_text[:100]}...")
    print(f"Respuesta usuario: {user_bool} (Correcta: {correct_bool})")
    print(f"Justificación: '{user_reason}'")
    
    scores = {
        "truth": 5.0 if user_bool == correct_bool else 0.0,
        "argument": 0.0,
        "ai_penalty": 0.0,
        "ai_analysis": {},
        "feedback": ""
    }
    
    print(f"Puntos por veracidad: {scores['truth']}/5")
    
    # NFT-specific penalty system
    reason_lower = user_reason.strip().lower()
    reason_length = len(user_reason.strip())
    
    # Penalization for inadequate responses
    invalid_answers = ['si', 'no', 'tal vez', 'no se', 'puede que si', 'puede que no']
    if reason_length < 10 or reason_lower in invalid_answers:
        scores["ai_penalty"] -= 1.0
        print(f"❌ Justificación inadecuada - Penalización: -1.0 puntos")
    elif reason_length < 20:
        scores["ai_penalty"] -= 0.5
        print(f"⚠️ Justificación muy corta - Penalización: -0.5 puntos")
    
    # AI usage detection
    ai_indicators = ["chatgpt", "gpt", "inteligencia artificial", "ia generativa", "modelo de lenguaje", "claude", "bot"]
    if any(ind in reason_lower for ind in ai_indicators):
        scores["ai_penalty"] -= 1.0
        print(f"❌ Uso de IA detectado - Penalización: -1.0 puntos")
    
    # Copy-paste detection
    if reason_length > 500:
        scores["ai_penalty"] -= 0.5
        print(f"⚠️ Respuesta sospechosamente larga - Penalización: -0.5 puntos")
    
    # AI analysis for argumentation
    if CLAUDE_API_KEY and reason_length >= 20:
        try:
            ai_analysis = analyze_argumentation_with_claude(user_reason, case_context, question_text, user_bool, correct_bool)
            
            if "error" not in ai_analysis and "score" in ai_analysis:
                scores["argument"] = min(ai_analysis.get("score", 0.0), 5.0)
                scores["ai_analysis"] = ai_analysis
                scores["feedback"] = ai_analysis.get("feedback", "")
                print(f"✅ Análisis IA completado - Puntos argumentación: {scores['argument']}/5")
            else:
                print(f"❌ Error en análisis IA: {ai_analysis}")
                scores["argument"] = 2.0  # Default score
        except Exception as e:
            print(f"❌ Excepción en análisis IA: {e}")
            scores["argument"] = 2.0
    else:
        scores["argument"] = 2.0 if reason_length >= 50 else 1.0
    
    # Calculate total score
    total_score = scores["truth"] + scores["argument"] + scores["ai_penalty"]
    total_score = max(0.0, min(10.0, total_score))  # Ensure 0-10 range
    
    print(f"📊 Puntuación final: {total_score}/10")
    return total_score, scores


###############################################################################
# Routes for students
###############################################################################

@app.route('/')
def index() -> str:
    """Landing page with student registration form."""
    return render_template('student_form.html')


@app.route('/start_exam', methods=['POST'])
def start_exam() -> str:
    """Process student information and start the comprehensive exam."""
    student_name = request.form.get('student_name', '').strip()
    student_carne = request.form.get('student_carne', '').strip()
    
    if not student_name or not student_carne:
        flash("Por favor complete todos los campos")
        return redirect(url_for('index'))
    
    # Store student info in session
    session['student_name'] = student_name
    session['student_carne'] = student_carne
    session['student_session'] = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    return redirect(url_for('take_comprehensive_exam'))


@app.route('/exam')
def take_comprehensive_exam() -> str:
    """Display all 5 NFT cases with their questions in a single comprehensive exam."""
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
            bool_key = f"case_{case_id}_bool_{q_index}"
            reason_key = f"case_{case_id}_reason_{q_index}"
            
            user_bool_str = request.form.get(bool_key, '').strip()
            user_reason = request.form.get(reason_key, '').strip()
            
            if not user_bool_str or not user_reason:
                flash(f"Pregunta incompleta en Caso {case_id}")
                return redirect(url_for('take_comprehensive_exam'))
            
            user_bool = user_bool_str.lower() == 'true'
            
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
                'instructor_comprehensive_result.html',
                result=result,
                student_name=student_name,
                student_carne=student_carne,
                all_cases_answers=all_cases_answers,
                cases=CASES,
                events=events,
                total_score=result['score'],
                paste_penalty=rubric_data.get('paste_penalty', 0)
            )
        else:
            # Individual case (legacy support)
            return render_template(
                'result.html',
                result=result,
                case=CASES.get(result['case_id']),
                answers_data=answers_data,
                rubric_data=rubric_data
            )
            
    except json.JSONDecodeError:
        return "Error: Datos corruptos", 500


###############################################################################
# App startup
###############################################################################

if __name__ == '__main__':
    print("🚀 Iniciando aplicación NFTs y Propiedad Intelectual...")
    print("🏛️ Organismo Judicial de Guatemala")
    print("🔐 Password de instructor actualizado")
    app.run(host='0.0.0.0', port=8000, debug=True)