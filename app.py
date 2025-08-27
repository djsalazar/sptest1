from __future__ import annotations

import json
import os
import random
import sqlite3
import string
import time
import hashlib
from datetime import datetime, timezone, timedelta
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

# Exam deadline (Guatemala timezone GMT-6)
GUATEMALA_TZ = timezone(timedelta(hours=-6))
EXAM_DEADLINE = datetime(2025, 8, 27, 23, 59, 0, tzinfo=GUATEMALA_TZ)

# Flask setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", ''.join(random.choices(string.ascii_letters + string.digits, k=32)))

# Debug logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(f"CLAUDE_API_KEY configurado: {'Sí' if CLAUDE_API_KEY else 'No'}")
if CLAUDE_API_KEY:
    print(f"CLAUDE_API_KEY (primeros 10 chars): {CLAUDE_API_KEY[:10]}...")

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
            student_hash TEXT,
            case_id INTEGER NOT NULL,
            answers_json TEXT NOT NULL,
            score REAL NOT NULL,
            rubric_json TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            duration_seconds INTEGER,
            paste_attempts INTEGER DEFAULT 0,
            copy_attempts INTEGER DEFAULT 0,
            total_penalties REAL DEFAULT 0
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
    
    # Add new columns if they don't exist (migration)
    try:
        cursor.execute("ALTER TABLE results ADD COLUMN student_hash TEXT")
        cursor.execute("ALTER TABLE results ADD COLUMN start_time TEXT")
        cursor.execute("ALTER TABLE results ADD COLUMN end_time TEXT")
        cursor.execute("ALTER TABLE results ADD COLUMN duration_seconds INTEGER")
        cursor.execute("ALTER TABLE results ADD COLUMN paste_attempts INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE results ADD COLUMN copy_attempts INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE results ADD COLUMN total_penalties REAL DEFAULT 0")
    except sqlite3.OperationalError:
        # Columns already exist
        pass
    
    db.commit()

###############################################################################
# Utility Functions
###############################################################################

def get_student_hash(student_name: str, student_carne: str) -> str:
    """Generate a hash for student identification to prevent duplicate attempts."""
    combined = f"{student_name.lower().strip()}:{student_carne.strip()}"
    return hashlib.sha256(combined.encode()).hexdigest()

def is_exam_blocked() -> bool:
    """Check if exam is blocked due to deadline."""
    guatemala_now = datetime.now(GUATEMALA_TZ)
    return guatemala_now > EXAM_DEADLINE

def get_guatemala_time() -> datetime:
    """Get current time in Guatemala timezone."""
    return datetime.now(GUATEMALA_TZ)

def has_student_attempted(student_hash: str) -> bool:
    """Check if student has already attempted the exam."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM results WHERE student_hash = ?", (student_hash,))
    count = cur.fetchone()[0]
    return count > 0

def detect_paste_copy_attempts(user_reason: str) -> Tuple[int, int]:
    """Detect potential copy/paste attempts based on text characteristics."""
    paste_indicators = 0
    copy_indicators = 0
    
    # Indicators of pasted content
    if len(user_reason) > 300:  # Very long responses might be pasted
        paste_indicators += 1
    
    # Check for unusual formatting characters
    if any(char in user_reason for char in ['\u2018', '\u2019', '\u201c', '\u201d', '\u2013', '\u2014']):
        paste_indicators += 1
    
    # Check for multiple consecutive spaces or tabs
    if '  ' in user_reason or '\t' in user_reason:
        paste_indicators += 1
    
    # Check for academic/formal language patterns that might indicate copying
    formal_patterns = ['en virtud de', 'por consiguiente', 'no obstante', 'por tanto', 'en consecuencia']
    if sum(1 for pattern in formal_patterns if pattern in user_reason.lower()) >= 2:
        copy_indicators += 1
    
    return paste_indicators, copy_indicators

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
    """Evaluate an answer using AI with detailed 9-criteria rubric. Max 3 points per question (6 per case, 30 total)."""
    
    # Truth component (1.5 points)
    truth_score = 1.5 if user_bool == correct_bool else 0.0
    
    # AI evaluation of argument (1.5 points max)
    argument_score = 1.5
    ai_analysis = {}
    feedback = ""
    
    # Detect copy/paste attempts
    paste_attempts, copy_attempts = detect_paste_copy_attempts(user_reason)
    paste_penalty = paste_attempts * 0.25 + copy_attempts * 0.5  # Up to 0.75 penalty
    
    if CLAUDE_API_KEY:
        try:
            evaluation_prompt = f"""
            SISTEMA DE EVALUACIÓN LEGAL - RÚBRICA ESPECÍFICA NFT Y PROPIEDAD INTELECTUAL

            CONTEXTO DEL CASO: {case_description}
            PREGUNTA EVALUADA: {question_text}
            RESPUESTA DEL ESTUDIANTE: {user_reason}

            Evalúa esta respuesta usando la siguiente rúbrica específica (escala 1-5 para cada criterio):

            1. OPINIÓN PROPIA FUNDADA (1-5):
            1=No presenta opinión o es infundada
            2=Opinión superficial, sin respaldo normativo/doctrinal
            3=Opinión con algún respaldo, pero limitado o irrelevante
            4=Opinión clara y fundamentada en norma, doctrina o jurisprudencia pertinente
            5=Opinión sólida, argumentada y respaldada con múltiples fuentes relevantes y actuales

            2. VALORES ÉTICOS (1-5):
            1=Ignora totalmente los aspectos éticos del caso
            2=Menciona valores de forma tangencial o confusa
            3=Reconoce valores éticos básicos, sin análisis profundo
            4=Analiza valores éticos pertinentes y su relación con el caso
            5=Analiza de forma crítica, equilibrada y profunda los valores éticos, vinculándolos con principios jurídicos y derechos humanos

            3. LENGUAJE Y TERMINOLOGÍA (1-5):
            1=Uso incorrecto de terminología, lenguaje coloquial inapropiado
            2=Uso parcial de términos técnicos, con errores
            3=Lenguaje adecuado pero poco preciso; mezcla términos técnicos y coloquiales
            4=Lenguaje técnico-jurídico claro y correcto, con terminología adecuada
            5=Lenguaje jurídico-forense preciso, adaptado al contexto y al público, sin errores

            4. CITAS Y PRECISIÓN NORMATIVA (1-5):
            1=No cita norma alguna o las cita erróneamente
            2=Citas incompletas o imprecisas
            3=Citas correctas pero sin exactitud plena
            4=Cita correctamente artículos, leyes, tratados o sentencias pertinentes
            5=Cita exacta y puntual (artículo, inciso, nombre completo de ley o tratado), integrando jurisprudencia y doctrina de forma impecable

            5. ESTRUCTURA Y COHERENCIA (1-5):
            1=Argumento desorganizado, incoherente o contradictorio
            2=Estructura débil, con saltos lógicos
            3=Organización aceptable, con transiciones poco claras
            4=Estructura lógica, coherente y bien organizada
            5=Argumentación impecablemente estructurada, con transiciones fluidas y progresión lógica sólida

            6. PROFUNDIDAD Y PERTINENCIA DE LA FUNDAMENTACIÓN (1-5):
            1=Fundamentación ausente o irrelevante
            2=Fundamentación parcial, con fuentes poco pertinentes
            3=Fundamentación aceptable, aunque limitada en alcance o actualidad
            4=Fundamentación sólida y pertinente con fuentes relevantes y actuales
            5=Fundamentación exhaustiva, con doctrina, jurisprudencia y normas actualizadas y aplicables

            7. CAPACIDAD CRÍTICA (1-5):
            1=No hay análisis crítico ni contraste de fuentes
            2=Contrasta superficialmente una sola fuente
            3=Identifica algunas diferencias entre fuentes, sin profundizar
            4=Contrasta y analiza diferencias con sentido crítico
            5=Contrasta de manera profunda, identifica vacíos, ambigüedades y propone soluciones jurídicas innovadoras

            8. PRESENTACIÓN Y ESTILO (1-5):
            1=Redacción confusa, con errores graves
            2=Redacción aceptable pero con errores frecuentes
            3=Redacción clara pero con errores menores
            4=Redacción clara, sin errores significativos
            5=Redacción impecable, sin errores, con formato y estilo de citas uniforme y profesional

            9. INNOVACIÓN Y CREATIVIDAD ARGUMENTATIVA (1-5):
            1=Argumentación repetitiva, sin originalidad
            2=Ideas poco desarrolladas o irrelevantes
            3=Alguna idea novedosa pero sin desarrollo
            4=Soluciones o enfoques novedosos y bien fundamentados
            5=Soluciones creativas, interdisciplinarias y viables, respaldadas sólidamente

            INSTRUCCIONES DE RESPUESTA:
            - Evalúa cada criterio del 1 al 5
            - Calcula el promedio de los 9 criterios
            - El score final será: (promedio/5) * 1.5 para obtener máximo 1.5 puntos
            - Proporciona feedback específico y constructivo

            Responde ÚNICAMENTE en formato JSON válido:
            {{
                "criterios": {{
                    "opinion_fundada": X,
                    "valores_eticos": X,
                    "lenguaje_terminologia": X,
                    "citas_precision": X,
                    "estructura_coherencia": X,
                    "profundidad_fundamentacion": X,
                    "capacidad_critica": X,
                    "presentacion_estilo": X,
                    "innovacion_creatividad": X
                }},
                "promedio_criterios": X.X,
                "score": X.X,
                "feedback": "Análisis específico y constructivo de la respuesta, destacando fortalezas y áreas de mejora..."
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
                    'max_tokens': 2000,
                    'messages': [{'role': 'user', 'content': evaluation_prompt}]
                },
                timeout=20
            )
            
            if response.status_code == 200:
                ai_response = response.json()['content'][0]['text']
                logger.info(f"AI Response: {ai_response}")
                
                try:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        ai_result = json.loads(json_match.group())
                        
                        # Extract detailed criteria
                        criterios = ai_result.get('criterios', {})
                        ai_analysis = {
                            'opinion_fundada': criterios.get('opinion_fundada', 3),
                            'valores_eticos': criterios.get('valores_eticos', 3),
                            'lenguaje_terminologia': criterios.get('lenguaje_terminologia', 3),
                            'citas_precision': criterios.get('citas_precision', 3),
                            'estructura_coherencia': criterios.get('estructura_coherencia', 3),
                            'profundidad_fundamentacion': criterios.get('profundidad_fundamentacion', 3),
                            'capacidad_critica': criterios.get('capacidad_critica', 3),
                            'presentacion_estilo': criterios.get('presentacion_estilo', 3),
                            'innovacion_creatividad': criterios.get('innovacion_creatividad', 3),
                            'promedio_criterios': ai_result.get('promedio_criterios', 3.0)
                        }
                        
                        argument_score = min(1.5, max(0.0, ai_result.get('score', 0.75)))
                        feedback = ai_result.get('feedback', 'Evaluación completada.')
                        
                        logger.info(f"AI Analysis successful: score={argument_score}, criteria={ai_analysis}")
                        
                except Exception as e:
                    logger.error(f"Error parsing AI evaluation: {e}")
                    # Default values if parsing fails
                    argument_score = 0.75
                    ai_analysis = {
                        'opinion_fundada': 3,
                        'valores_eticos': 3,
                        'lenguaje_terminologia': 3,
                        'citas_precision': 3,
                        'estructura_coherencia': 3,
                        'profundidad_fundamentacion': 3,
                        'capacidad_critica': 3,
                        'presentacion_estilo': 3,
                        'innovacion_creatividad': 3,
                        'promedio_criterios': 3.0
                    }
                    feedback = "Error en evaluación automática. Puntuación asignada por defecto."
            else:
                logger.error(f"AI API Error: {response.status_code}")
                argument_score = 0.75
                
        except Exception as e:
            logger.error(f"Error evaluating with AI: {e}")
            argument_score = 0.75
    else:
        # Basic evaluation without AI
        argument_score = 0.75 if len(user_reason.strip()) >= 50 else 0.25
        ai_analysis = {
            'opinion_fundada': 3,
            'valores_eticos': 3,
            'lenguaje_terminologia': 3,
            'citas_precision': 3,
            'estructura_coherencia': 3,
            'profundidad_fundamentacion': 3,
            'capacidad_critica': 3,
            'presentacion_estilo': 3,
            'innovacion_creatividad': 3,
            'promedio_criterios': 3.0
        }
    
    # Calculate total score (max 3 points per question)
    total_score = truth_score + argument_score - paste_penalty
    total_score = max(0.0, min(3.0, total_score))
    
    breakdown = {
        'truth': truth_score,
        'argument': argument_score,
        'paste_penalty': paste_penalty,
        'paste_attempts': paste_attempts,
        'copy_attempts': copy_attempts,
        'feedback': feedback,
        'ai_analysis': ai_analysis
    }
    
    return total_score, breakdown

###############################################################################
# Routes
###############################################################################

@app.route('/')
def index() -> str:
    """Landing page."""
    # Check if exam is blocked
    if is_exam_blocked():
        return render_template('exam_blocked.html', deadline=EXAM_DEADLINE)
    
    return render_template('student_form.html', 
                         exam_deadline=EXAM_DEADLINE,
                         guatemala_time=get_guatemala_time())

@app.route('/rubric')
def rubric() -> str:
    """Show exam rubric and evaluation criteria."""
    return render_template('rubric.html', cases=CASES)

@app.route('/start_exam', methods=['POST'])
def start_exam() -> str:
    """Process student registration and start exam."""
    if is_exam_blocked():
        flash(f"El examen ha expirado. Fecha límite: {EXAM_DEADLINE.strftime('%d/%m/%Y %H:%M')} (Guatemala)")
        return redirect(url_for('index'))
    
    student_name = request.form.get('student_name', '').strip()
    student_carne = request.form.get('student_carne', '').strip()
    
    if not student_name or not student_carne:
        flash("Debe completar todos los campos")
        return redirect(url_for('index'))
    
    # Check for duplicate attempts
    student_hash = get_student_hash(student_name, student_carne)
    if has_student_attempted(student_hash):
        flash("Ya has completado este examen. Solo se permite un intento por estudiante.")
        return redirect(url_for('index'))
    
    # Store in session
    session['student_name'] = student_name
    session['student_carne'] = student_carne
    session['student_hash'] = student_hash
    session['exam_start_time'] = get_guatemala_time().isoformat()
    
    return redirect(url_for('take_comprehensive_exam'))

@app.route('/comprehensive_exam')
def take_comprehensive_exam() -> str:
    """Display comprehensive exam with all cases."""
    if is_exam_blocked():
        flash(f"El examen ha expirado. Fecha límite: {EXAM_DEADLINE.strftime('%d/%m/%Y %H:%M')} (Guatemala)")
        return redirect(url_for('index'))
    
    if 'student_name' not in session or 'student_carne' not in session:
        flash("Debe registrar sus datos primero")
        return redirect(url_for('index'))
    
    # Check for duplicate attempts
    student_hash = session.get('student_hash')
    if has_student_attempted(student_hash):
        flash("Ya has completado este examen. Solo se permite un intento por estudiante.")
        session.clear()
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
        student_carne=session.get('student_carne'),
        exam_deadline=EXAM_DEADLINE
    )

@app.route('/submit_comprehensive', methods=['POST'])
def submit_comprehensive() -> str:
    """Process comprehensive exam submission."""
    if is_exam_blocked():
        flash(f"El examen ha expirado durante su realización. Fecha límite: {EXAM_DEADLINE.strftime('%d/%m/%Y %H:%M')} (Guatemala)")
        return redirect(url_for('index'))
    
    if 'student_name' not in session or 'student_carne' not in session:
        flash("Sesión expirada. Debe registrarse nuevamente.")
        return redirect(url_for('index'))
    
    # Check for duplicate attempts
    student_hash = session.get('student_hash')
    if has_student_attempted(student_hash):
        flash("Ya has completado este examen. Solo se permite un intento por estudiante.")
        session.clear()
        return redirect(url_for('index'))
    
    # Calculate timing
    end_time = get_guatemala_time()
    start_time_str = session.get('exam_start_time')
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=GUATEMALA_TZ)
        duration_seconds = int((end_time - start_time).total_seconds())
    else:
        start_time = end_time
        duration_seconds = 0
    
    timestamp = end_time.isoformat()
    student_name = session.get('student_name')
    student_carne = session.get('student_carne')
    student_id = f"{student_carne} - {student_name}"
    
    # Process all cases
    all_answers = []
    total_score = 0.0
    total_paste_attempts = 0
    total_copy_attempts = 0
    total_penalties = 0.0
    
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
            
            # Accumulate penalties
            total_paste_attempts += breakdown.get('paste_attempts', 0)
            total_copy_attempts += breakdown.get('copy_attempts', 0)
            total_penalties += breakdown.get('paste_penalty', 0)
            
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
            'answers': case_data['answers'],
            'score': case_data['score']
        } for case_data in all_answers}
    })
    
    rubric_json = json.dumps({
        'total_score': total_score,
        'total_penalties': total_penalties,
        'paste_attempts': total_paste_attempts,
        'copy_attempts': total_copy_attempts,
        'max_possible_score': 30.0
    })
    
    cur.execute(
        """
        INSERT INTO results 
        (timestamp, student_id, student_hash, case_id, answers_json, score, rubric_json, 
         start_time, end_time, duration_seconds, paste_attempts, copy_attempts, total_penalties) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (timestamp, student_id, student_hash, 0, answers_json, total_score, rubric_json,
         start_time.isoformat(), end_time.isoformat(), duration_seconds,
         total_paste_attempts, total_copy_attempts, total_penalties)
    )
    result_id = cur.lastrowid
    
    # Log completion event
    cur.execute(
        "INSERT INTO events (result_id, event_type, event_time, details) VALUES (?, ?, ?, ?)",
        (result_id, 'exam_completed', timestamp, f"Duration: {duration_seconds}s, Penalties: {total_penalties:.2f}")
    )
    
    db.commit()
    
    # Clear session data
    session.clear()
    
    return render_template(
        'comprehensive_feedback.html',
        all_cases_data=all_answers,
        cases=CASES,
        total_score=total_score,
        total_penalties=total_penalties,
        paste_attempts=total_paste_attempts,
        copy_attempts=total_copy_attempts,
        duration_minutes=duration_seconds // 60,
        student_name=student_name,
        student_carne=student_carne,
        max_score=30.0
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
        """SELECT id, timestamp, student_id, case_id, score, duration_seconds, 
                  paste_attempts, copy_attempts, total_penalties 
           FROM results ORDER BY timestamp DESC"""
    )
    rows = cur.fetchall()
    
    # Build aggregated statistics
    scores = [row['score'] for row in rows]
    average_score = sum(scores) / len(scores) if scores else 0.0
    passing_rate = len([s for s in scores if s >= 18]) / len(scores) * 100 if scores else 0.0  # 60% of 30
    
    return render_template(
        'dashboard.html',
        results=rows,
        cases=CASES,
        average_score=average_score,
        passing_rate=passing_rate,
        exam_deadline=EXAM_DEADLINE,
        is_exam_blocked=is_exam_blocked(),
        max_score=30.0
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
            
            # CORRECCIÓN: Preparar datos para el template de instructor
            processed_cases_data = []
            for case_id_str, case_data in all_cases_answers.items():
                case_id = int(case_id_str)
                case_obj = CASES.get(case_id)
                if case_obj:
                    processed_cases_data.append({
                        'case': case_obj,
                        'answers': case_data.get('answers', []),
                        'score': case_data.get('score', 0)
                    })
            
            return render_template(
                'instructor_comprehensive_result.html',  # Template específico para instructor
                all_cases_data=processed_cases_data,
                cases=CASES,
                total_score=result['score'],
                events=events,
                student_name=student_name,
                student_carne=student_carne,
                rubric_data=rubric_data,
                result=result,
                max_score=30.0
            )
        else:
            # Individual exam (legacy)
            return render_template(
                'result.html',
                result=result,
                cases=CASES,
                answers=json.loads(result['answers_json']),
                events=[],
                max_score=30.0
            )
    
    except Exception as e:
        logger.error(f"Error processing result {result_id}: {e}")
        return f"Error procesando resultado: {str(e)}", 500

@app.route('/info')
def info():
    """Página de información del sistema."""
    return render_template('info.html', cases=CASES, exam_deadline=EXAM_DEADLINE)

###############################################################################
# Utility Functions and Filters
###############################################################################

def from_json_filter(json_string):
    """Filtro para convertir JSON string a dict en templates"""
    try:
        return json.loads(json_string) if json_string else {}
    except:
        return {}

# Register filters


@app.context_processor
def inject_globals():
    return {
        'now': datetime.now(),
        'guatemala_time': get_guatemala_time(),
        'exam_deadline': EXAM_DEADLINE,
        'is_exam_blocked': is_exam_blocked()
    }


def flatten_filter(nested_list):
    """Filtro personalizado para aplanar listas anidadas en Jinja2"""
    def flatten_recursive(items):
        result = []
        for item in items:
            if isinstance(item, (list, tuple)):
                result.extend(flatten_recursive(item))
            else:
                result.append(item)
        return result
    
    try:
        if nested_list is None:
            return []
        return flatten_recursive(nested_list)
    except:
        return []

def from_json_filter(json_string):
    """Filtro para convertir JSON string a dict en templates"""
    try:
        return json.loads(json_string) if json_string else {}
    except:
        return {}

app.jinja_env.filters['from_json'] = from_json_filter
app.jinja_env.filters['flatten'] = flatten_filter  

###############################################################################
# App startup
###############################################################################

if __name__ == '__main__':
    print("Iniciando aplicación NFTs y Propiedad Intelectual...")
    print("LegalTechGT")
    print(f"Password de instructor: {INSTRUCTOR_PASSWORD}")
    print(f"Fecha límite del examen: {EXAM_DEADLINE.strftime('%d/%m/%Y %H:%M')} (Guatemala)")
    print(f"Estado del examen: {'BLOQUEADO' if is_exam_blocked() else 'ACTIVO'}")
    app.run(host='0.0.0.0', port=8000, debug=True)