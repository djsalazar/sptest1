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
and deploy within a couple of hours. The code also includes integration
with Anthropic's Claude API for sophisticated argumentation analysis.
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
                   url_for, flash)




###############################################################################
# Configuration
###############################################################################

# When set, this environment variable should contain a valid Anthropic API
# key. The ``analyze_argumentation_with_claude`` function uses it to analyze arguments.
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

# Debug logging (DESPUÉS de definir las variables)
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Print environment variables at startup
print(f"🔑 CLAUDE_API_KEY configurado: {'Sí' if CLAUDE_API_KEY else 'No'}")
if CLAUDE_API_KEY:
    print(f"🔑 CLAUDE_API_KEY (primeros 10 chars): {CLAUDE_API_KEY[:10]}...")
    print(f"🔑 CLAUDE_API_KEY (longitud): {len(CLAUDE_API_KEY)} caracteres")
else:
    print("❌ CLAUDE_API_KEY no encontrado")
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
    """..."""
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
                "model": "claude-3-5-sonnet-20241022",  # MODELO CORRECTO
                "max_tokens": 200,
                "messages": [
                    {
                        "role": "user", 
                        "content": f"""Parafrasea la siguiente pregunta legal manteniendo EXACTAMENTE el mismo significado y estructura lógica. 
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
            # The new API returns the completion in content[0]["text"]
            paraphrased = data["content"][0]["text"].strip()
            
            # Verificar que la paráfrasis sea coherente (no muy corta ni muy larga)
            if paraphrased and len(paraphrased) > 50 and len(paraphrased) < len(prompt) * 2:
                return paraphrased
            else:
                print(f"Paráfrasis inválida: {paraphrased}")
                return None
        else:
            print(f"Error API Claude: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Excepción en call_claude: {e}")
        return None


def analyze_argumentation_with_claude(user_reason: str, case_context: str, 
                                    question_text: str, user_bool: bool, correct_bool: bool) -> Dict[str, any]:
    """
    Use Claude API to analyze argumentation quality based on detailed rubric.
    """
    print(f"🔄 Preparando llamada a Claude API...")
    
    if not CLAUDE_API_KEY:
        raise Exception("CLAUDE_API_KEY no configurado")
    
    if len(CLAUDE_API_KEY) < 20:
        raise Exception(f"CLAUDE_API_KEY parece inválido (longitud: {len(CLAUDE_API_KEY)})")
    
    prompt = f"""Eres un profesor experto en propiedad intelectual y conocimientos tradicionales. 
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

1. Opinión propia fundada (1-5)
2. Valores éticos (1-5)
3. Lenguaje y terminología (1-5)
4. Citas y precisión normativa (1-5)
5. Estructura y coherencia (1-5)
6. Profundidad y pertinencia (1-5)
7. Capacidad crítica (1-5)
8. Presentación y estilo (1-5)
9. Innovación y creatividad (1-5)

INSTRUCCIONES:
1. Evalúa cada criterio con una puntuación de 1-5
2. Calcula el promedio de los 9 criterios y multiplícalo por 8 para obtener la puntuación sobre 40 puntos
3. Proporciona feedback específico y constructivo
4. Responde ÚNICAMENTE en formato JSON válido:

{{
    "criteria_scores": {{
        "opinion_fundada": 3,
        "valores_eticos": 2,
        "lenguaje_terminologia": 4,
        "citas_precision": 1,
        "estructura_coherencia": 3,
        "profundidad_fundamentacion": 2,
        "capacidad_critica": 2,
        "presentacion_estilo": 4,
        "innovacion_creatividad": 2
    }},
    "total_argument_score": 23.2,
    "feedback": "La argumentación muestra algunos elementos positivos pero requiere mayor fundamentación legal y análisis crítico más profundo..."
}}"""

    try:
        print(f"🌐 Enviando solicitud a Claude...")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",  # MODELO CORRECTO
                "max_tokens": 1500,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            timeout=30
        )
        
        print(f"📡 Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["content"][0]["text"]
            print(f"📄 Contenido recibido: {content[:200]}...")
            
            # Parse the JSON response
            try:
                analysis = json.loads(content)
                print(f"✅ JSON parseado correctamente")
                return analysis
            except json.JSONDecodeError as je:
                print(f"❌ Error parseando JSON: {je}")
                raise Exception(f"Respuesta JSON inválida de Claude: {content[:100]}...")
        else:
            error_text = response.text
            print(f"❌ Error HTTP {response.status_code}: {error_text}")
            raise Exception(f"API request failed with status {response.status_code}: {error_text}")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout en solicitud a Claude")
        raise Exception("Timeout en solicitud a Claude API")
    except requests.exceptions.RequestException as re:
        print(f"🌐 Error de conexión: {re}")
        raise Exception(f"Error de conexión a Claude API: {str(re)}")
    except Exception as e:
        print(f"💥 Error inesperado: {e}")
        raise Exception(f"Error inesperado en Claude API: {str(e)}")


def simple_argument_evaluation(user_reason: str) -> float:
    """Fallback simple evaluation when Claude API is not available."""
    reason = user_reason.strip()
    word_count = len(reason.split())
    
    if word_count < 20:
        length_factor = 0.0
    elif word_count <= 150:
        length_factor = (word_count - 20) / 130
    else:
        length_factor = 1.0
    
    markers = ["porque", "sin embargo", "por lo tanto", "no obstante", "por consiguiente"]
    marker_hits = sum(1 for m in markers if m in reason.lower())
    marker_factor = min(marker_hits / len(markers), 1.0)
    
    return (length_factor * 0.6 + marker_factor * 0.4) * 40.0


def evaluate_answer_with_ai(user_bool: bool, user_reason: str, correct_bool: bool, 
                           case_context: str, question_text: str) -> Tuple[float, Dict[str, any]]:
    """
    Evaluate answer using AI for sophisticated argumentation analysis.
    
    Total per question: 10 points (100 total / 10 questions)
    - Truth: 5 points (50%)
    - Argumentation: 4 points (40%) 
    - Penalties: up to -2 points (20%)
    """
    print(f"\n=== EVALUANDO RESPUESTA ===")
    print(f"Pregunta: {question_text[:100]}...")
    print(f"Respuesta usuario: {user_bool} (Correcta: {correct_bool})")
    print(f"Justificación: '{user_reason}'")
    
    scores = {
        "truth": 5.0 if user_bool == correct_bool else 0.0,  # 5 points max
        "argument": 0.0,
        "ai_penalty": 0.0,
        "ai_analysis": {},
        "feedback": ""
    }
    
    print(f"Puntos por veracidad: {scores['truth']}/5")
    
    # SISTEMA DE PENALIZACIONES MEJORADO
    reason_lower = user_reason.strip().lower()
    reason_length = len(user_reason.strip())
    
    # 1. Penalización por respuestas muy cortas o inválidas
    invalid_answers = ['si', 'no', 'tal vez', 'no se', 'puede que si', 'puede que no', 'la verdad no entiendo', 'puedes ser']
    if reason_length < 10 or reason_lower in invalid_answers:
        scores["ai_penalty"] -= 1.0
        print(f"❌ Justificación inadecuada: '{user_reason}' - Penalización: -1.0 puntos")
    elif reason_length < 20:
        scores["ai_penalty"] -= 0.5
        print(f"⚠️ Justificación muy corta ({reason_length} chars) - Penalización: -0.5 puntos")
    
    # 2. Penalización por uso de IA
    ai_indicators = ["chatgpt", "gpt", "inteligencia artificial", "ia generativa", "modelo de lenguaje", "claude", "bot", "artificial intelligence"]
    if any(ind in reason_lower for ind in ai_indicators):
        scores["ai_penalty"] -= 1.0
        print(f"❌ Uso de IA detectado - Penalización: -1.0 puntos")
    
    # 3. Límite de penalización (no puede bajar de 0)
    if scores["ai_penalty"] < -2.0:
        scores["ai_penalty"] = -2.0
        print(f"⚠️ Penalización limitada a -2.0 puntos máximo")
    
    # If no Claude API key, fall back to simple evaluation
    if not CLAUDE_API_KEY:
        print("❌ No hay CLAUDE_API_KEY - usando evaluación simple")
        simple_score = simple_argument_evaluation(user_reason)
        scores["argument"] = simple_score * 0.1  # Scale to 4 points max (40 -> 4)
        scores["feedback"] = "Evaluación automática básica - Configure CLAUDE_API_KEY para análisis avanzado con IA."
        print(f"Puntos por argumentación (simple): {scores['argument']}/4")
    else:
        # Use Claude API for detailed analysis
        print(f"🤖 Intentando análisis con Claude API...")
        try:
            ai_analysis = analyze_argumentation_with_claude(
                user_reason, case_context, question_text, user_bool, correct_bool
            )
            scores["argument"] = ai_analysis["total_argument_score"] * 0.1  # 40 -> 4 points
            scores["ai_analysis"] = ai_analysis["criteria_scores"]
            scores["feedback"] = ai_analysis["feedback"]
            print(f"✅ Análisis IA exitoso - Puntos: {scores['argument']}/4")
        except Exception as e:
            print(f"❌ Error en Claude API: {e}")
            simple_score = simple_argument_evaluation(user_reason)
            scores["argument"] = simple_score * 0.1
            scores["feedback"] = f"Error en el análisis de IA. Se aplicó evaluación básica automática. Para justificaciones más cortas, considere proporcionar mayor detalle y fundamentación legal."
            print(f"Puntos por argumentación (fallback): {scores['argument']}/4")
    
    # Calcular total (no puede ser negativo)
    total = max(scores["truth"] + scores["argument"] + scores["ai_penalty"], 0.0)
    
    print(f"📊 Puntuación total: {total}/10")
    print(f"   - Veracidad: {scores['truth']}/5")
    print(f"   - Argumentación: {scores['argument']:.1f}/4") 
    print(f"   - Penalizaciones: {scores['ai_penalty']}")
    print("=== FIN EVALUACIÓN ===\n")
    
    return total, scores

def simple_argument_evaluation(user_reason: str) -> float:
    """Fallback simple evaluation when Claude API is not available."""
    reason = user_reason.strip()
    word_count = len(reason.split())
    
    if word_count < 20:
        length_factor = 0.0
    elif word_count <= 150:
        length_factor = (word_count - 20) / 130
    else:
        length_factor = 1.0
    
    markers = ["porque", "sin embargo", "por lo tanto", "no obstante", "por consiguiente"]
    marker_hits = sum(1 for m in markers if m in reason.lower())
    marker_factor = min(marker_hits / len(markers), 1.0)
    
    return (length_factor * 0.6 + marker_factor * 0.4) * 40.0  # Return 40 max, will be scaled down


def random_rephrase(question: str) -> str:
    """
    Generate a non‑trivial rephrasing of a question. The function first
    attempts to use Anthropic's API. If that fails or no API key is
    configured, it returns the original question unchanged to maintain
    coherence and fairness.
    """
    # Try to call Anthropic for paraphrasing
    rephrased = call_claude(question)
    if rephrased:
        print(f"Paráfrasis exitosa: {question[:50]}... -> {rephrased[:50]}...")
        return rephrased
    
    # If Claude API fails, return original question to maintain coherence
    print(f"Usando pregunta original (API falló): {question[:50]}...")
    return question

def test_claude_api() -> bool:
    """
    Test if Claude API is working correctly.
    """
    if not CLAUDE_API_KEY:
        print("❌ No se encontró CLAUDE_API_KEY")
        return False
    
    test_question = "¿Esta es una pregunta de prueba?"
    result = call_claude(test_question)
    
    if result:
        print(f"✅ API de Claude funciona correctamente")
        print(f"   Original: {test_question}")
        print(f"   Parafraseado: {result}")
        return True
    else:
        print("❌ API de Claude no está funcionando")
        return False


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
    """
    Display all 5 cases with their questions in a single comprehensive exam.
    """
    if 'student_name' not in session or 'student_carne' not in session:
        flash("Debe registrarse primero")
        return redirect(url_for('index'))
    
    # Test Claude API on first load
    print("\n=== TESTING CLAUDE API ===")
    claude_working = test_claude_api()
    print("=========================\n")
    
    # Generate rephrased questions for all cases
    all_cases_data = []
    for case_id, case in CASES.items():
        print(f"\n--- Procesando Caso {case_id} ---")
        rephrased_questions = []
        for idx, q in enumerate(case.questions):
            print(f"Pregunta {idx + 1} original: {q.text[:80]}...")
            rephrased = q.rephrased()
            print(f"Pregunta {idx + 1} final: {rephrased[:80]}...")
            rephrased_questions.append(rephrased)
        
        all_cases_data.append({
            'case': case,
            'questions': rephrased_questions
        })
    
    return render_template(
        'comprehensive_exam.html',
        all_cases_data=all_cases_data,
        student_name=session.get('student_name'),
        student_carne=session.get('student_carne'),
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


@app.route('/submit_comprehensive', methods=['POST'])
def submit_comprehensive() -> str:
    """
    Process the comprehensive exam submission for all 5 cases.
    """
    if 'student_name' not in session or 'student_carne' not in session:
        flash("Sesión expirada")
        return redirect(url_for('index'))
    
    # Process all cases
    all_answers = {}
    total_score = 0.0
    all_rubric_breakdown = {}
    
    for case_id, case in CASES.items():
        case_answers = []
        case_rubric = []
        
        for idx, q in enumerate(case.questions):
            field_name = f'case_{case_id}_bool_{idx}'
            reason_name = f'case_{case_id}_reason_{idx}'
            
            bool_str = request.form.get(field_name, 'false')
            user_bool = bool_str.lower() == 'true'
            user_reason = request.form.get(reason_name, '').strip()
            
            # Use AI evaluation for detailed analysis
            score, breakdown = evaluate_answer_with_ai(
                user_bool=user_bool,
                user_reason=user_reason,
                correct_bool=q.correct,
                case_context=case.description,
                question_text=q.text
            )
            
            case_answers.append({
                'user_bool': user_bool,
                'user_reason': user_reason,
                'correct': q.correct,
                'score': score,
                'breakdown': breakdown,
            })
            total_score += score
            case_rubric.append(breakdown)
        
        all_answers[case_id] = case_answers
        all_rubric_breakdown[case_id] = case_rubric
    
    # Apply paste penalties if any were recorded for this session
    pending_events = session.pop('pending_events', [])
    paste_events = [ev for ev in pending_events if ev.get('event_type') == 'paste']
    paste_penalty = len(paste_events) * 0.5  # 0.5 points per paste event
    total_score = max(total_score - paste_penalty, 0.0)
    
    # Save the result to the database
    db = get_db()
    timestamp = datetime.utcnow().isoformat()
    student_id = f"{session.get('student_carne')} - {session.get('student_name')}"
    
    # Create a comprehensive answers JSON
    comprehensive_data = {
        'student_name': session.get('student_name'),
        'student_carne': session.get('student_carne'),
        'all_cases': all_answers
    }
    
    answers_json = json.dumps(comprehensive_data)
    rubric_json = json.dumps({
        'all_cases_breakdown': all_rubric_breakdown,
        'paste_penalty': paste_penalty,
    })
    
    cur = db.cursor()
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
    
    # Clear session data tied to this test
    session.pop('student_session', None)
    
    # Render comprehensive feedback
    return render_template(
        'comprehensive_feedback.html',
        all_cases_data=all_answers,
        cases=CASES,
        total_score=total_score,
        paste_penalty=paste_penalty,
        student_name=session.get('student_name'),
        student_carne=session.get('student_carne')
    )


# Mantener la ruta original para compatibilidad
@app.route('/test/<int:case_id>', methods=['GET'])
def take_test(case_id: int) -> str:
    """Individual case test (for backward compatibility)"""
    return redirect(url_for('index'))

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
    
    try:
        answers_data = json.loads(result['answers_json'])
        rubric_data = json.loads(result['rubric_json'])
        
        # Check if this is a comprehensive exam (case_id = 0) or individual case
        if result['case_id'] == 0:
            # Comprehensive exam - new format
            student_name = answers_data.get('student_name', 'N/A')
            student_carne = answers_data.get('student_carne', 'N/A')
            all_cases_answers = answers_data.get('all_cases', {})
            
            # Retrieve event logs
            cur.execute(
                "SELECT event_type, event_time, details FROM events WHERE result_id = ? ORDER BY event_time",
                (result_id,)
            )
            events = cur.fetchall()
            
            return render_template(
                'instructor_comprehensive_result.html',
                result=result,
                student_name=student_name,
                student_carne=student_carne,
                all_cases_answers=all_cases_answers,
                rubric=rubric_data,
                events=events,
                cases=CASES
            )
        else:
            # Individual case - old format (backward compatibility)
            answers = answers_data if isinstance(answers_data, list) else []
            
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
            
    except Exception as e:
        print(f"Error procesando resultado {result_id}: {e}")
        return f"Error procesando resultado: {str(e)}", 500

###############################################################################
# Run the app
###############################################################################

if __name__ == '__main__':
    # Create database directory if necessary
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Launch the Flask development server for local testing. When
    # containerised, the command in the Dockerfile starts the app.
    app.run(host='0.0.0.0', port=8000, debug=False)