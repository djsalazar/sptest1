from __future__ import annotations

import json
import os
import random
import sqlite3
import string
import time
import hashlib
import secrets
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Load environment variables from a .env file if present
from dotenv import load_dotenv
load_dotenv()

import requests
from flask import (Flask, g, redirect, render_template, request, session,
                   url_for, flash, jsonify)

###############################################################################
# Configuration
###############################################################################

# Anthropic API key for Claude integration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Updated instructor password
INSTRUCTOR_PASSWORD = "organismojudicial"

# File path to the SQLite database (UPDATED FOR PERSISTENCE)
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "exam.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

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

print(f"Iniciando aplicación NFTs y Propiedad Intelectual...")
print(f"LegalTechGT")
print(f"Password de instructor: {INSTRUCTOR_PASSWORD}")
print(f"Fecha límite del examen: {EXAM_DEADLINE.strftime('%d/%m/%Y %H:%M')} (Guatemala)")
guatemala_now = datetime.now(GUATEMALA_TZ)
print(f"Estado del examen: {'BLOQUEADO' if guatemala_now > EXAM_DEADLINE else 'ACTIVO'}")

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

###############################################################################
# Case Definitions
###############################################################################

CASES = {
    1: Case(
        case_id=1,
        title="NFT como Título Traslativo de Dominio",
        description=(
            "María compra un NFT de una obra de arte digital por 2 ETH en OpenSea. El proyecto especifica en sus términos "
            "y condiciones que la compra del NFT NO transfiere derechos de autor, solo otorga una licencia personal "
            "no comercial para uso privado. Sin embargo, María interpreta que al comprar el NFT obtiene la propiedad "
            "de la obra digital y puede usarla comercialmente. Analice la situación desde la perspectiva de la "
            "separación obra-soporte y la cesión de derechos de autor."
        ),
        questions=[
            Question(
                text=(
                    "La compra de un NFT automáticamente transfiere los derechos patrimoniales de autor "
                    "de la obra digital asociada al comprador."
                ),
                correct=False,
                keywords=["derechos patrimoniales", "transferencia automática", "NFT", "cesión expresa"]
            ),
            Question(
                text=(
                    "Los términos y condiciones del proyecto NFT pueden limitar los derechos que adquiere "
                    "el comprador, incluso si el NFT representa una obra protegida por derecho de autor."
                ),
                correct=True,
                keywords=["términos y condiciones", "limitación de derechos", "contrato", "licencia"]
            ),
        ]
    ),
    2: Case(
        case_id=2,
        title="Smart Contracts y Regalías Automáticas",
        description=(
            "Un artista crea una colección de NFTs con un smart contract que incluye regalías automáticas del 10% "
            "para cada reventa. Después de 2 años, los compradores han revendido los NFTs múltiples veces y el "
            "artista ha recibido regalías automáticas por cada transacción. Surge la pregunta: ¿estas regalías "
            "automáticas programadas en blockchain tienen validez jurídica en Guatemala? ¿Qué sucede si un "
            "comprador vende el NFT fuera de la plataforma original sin pagar regalías?"
        ),
        questions=[
            Question(
                text=(
                    "Las regalías automáticas programadas en smart contracts tienen plena validez jurídica "
                    "en Guatemala y son exigibles ante tribunales nacionales."
                ),
                correct=False,
                keywords=["smart contracts", "validez jurídica", "regalías", "enforcement", "Guatemala"]
            ),
            Question(
                text=(
                    "Un smart contract puede establecer obligaciones contractuales válidas, pero su "
                    "enforcement depende del reconocimiento legal del contrato subyacente."
                ),
                correct=True,
                keywords=["obligaciones contractuales", "enforcement", "reconocimiento legal", "contrato subyacente"]
            ),
        ]
    ),
    3: Case(
        case_id=3,
        title="Representación Digital vs Reproducción",
        description=(
            "Carlos posee los derechos de autor de una fotografía. Un tercero crea un NFT de su fotografía sin "
            "autorización y la vende en una plataforma descentralizada. El NFT contiene un hash que apunta a "
            "la imagen almacenada en IPFS. Carlos argumenta que esto constituye reproducción no autorizada y "
            "violación a sus derechos de autor. La defensa del infractor alega que el NFT solo contiene "
            "metadatos y un enlace, no la obra en sí."
        ),
        questions=[
            Question(
                text=(
                    "Crear un NFT que apunta a una obra protegida por derecho de autor, sin autorización "
                    "del titular, constituye siempre una violación al derecho de reproducción."
                ),
                correct=False,
                keywords=["NFT", "reproducción", "autorización", "metadatos", "enlace"]
            ),
            Question(
                text=(
                    "La mera tokenización de una obra (crear NFT con metadatos) sin almacenar la obra "
                    "en blockchain podría no constituir reproducción directa, pero sí otros tipos de "
                    "infracción como aprovechamiento indebido."
                ),
                correct=True,
                keywords=["tokenización", "metadatos", "reproducción directa", "aprovechamiento indebido"]
            ),
        ]
    ),
    4: Case(
        case_id=4,
        title="Uso Público de NFT Musical",
        description=(
            "Una discográfica vende NFTs de canciones populares otorgando a los compradores derechos de "
            "'uso público' para las canciones. Los compradores interpretan esto como autorización para usar "
            "las canciones en streams de Twitch, videos de YouTube, eventos privados y comerciales públicos. "
            "Surge controversia cuando artistas reclaman que estos usos exceden lo autorizado y constituyen "
            "comunicación pública no autorizada."
        ),
        questions=[
            Question(
                text=(
                    "La comunicación pública de una obra musical requiere autorización específica del "
                    "titular, independientemente de si se posee un NFT de la misma."
                ),
                correct=True,
                keywords=["comunicación pública", "autorización específica", "obra musical", "NFT"]
            ),
            Question(
                text=(
                    "Los términos 'uso público' en un contrato de NFT tienen un significado jurídico "
                    "preciso que automáticamente autoriza cualquier tipo de comunicación pública."
                ),
                correct=False,
                keywords=["uso público", "significado jurídico", "comunicación pública", "autorización automática"]
            ),
        ]
    ),
    5: Case(
        case_id=5,
        title="NFT y Derechos Constitucionales",
        description=(
            "Un museo nacional digitaliza obras de arte de dominio público y crea NFTs de las mismas, "
            "vendiendo acceso exclusivo a versiones de alta resolución. Ciudadanos argumentan que esto "
            "limita el acceso público a patrimonio cultural que debería ser libremente disponible, "
            "violando el derecho constitucional de acceso a la cultura (Art. 71 CN). El museo alega que "
            "las obras físicas siguen siendo accesibles y los NFTs solo monetizan versiones digitales "
            "mejoradas."
        ),
        questions=[
            Question(
                text=(
                    "Los derechos de acceso a la cultura prevalecen sobre cualquier intento de "
                    "monetización de obras en dominio público, incluso en versiones digitales mejoradas."
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
    
    # Tabla principal results
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
            total_penalties REAL DEFAULT 0,
            overall_level TEXT DEFAULT 'intermedio',
            general_feedback TEXT
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
    
    # NUEVA TABLA: Evaluaciones detalladas por pregunta
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS question_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER NOT NULL,
            case_id INTEGER NOT NULL,
            question_index INTEGER NOT NULL,
            user_answer_text TEXT,
            user_answer_bool INTEGER,
            correct_answer_bool INTEGER,
            
            -- 9 Criterios (escala 1-5)
            opinion_fundada INTEGER DEFAULT 3,
            valores_eticos INTEGER DEFAULT 3,
            lenguaje_terminologia INTEGER DEFAULT 3,
            citas_precision INTEGER DEFAULT 3,
            estructura_coherencia INTEGER DEFAULT 3,
            profundidad_fundamentacion INTEGER DEFAULT 3,
            capacidad_critica INTEGER DEFAULT 3,
            presentacion_estilo INTEGER DEFAULT 3,
            innovacion_creatividad INTEGER DEFAULT 3,
            
            -- Feedback detallado
            feedback_general TEXT,
            feedback_fortalezas TEXT,
            feedback_mejoras TEXT,
            
            -- Puntajes
            truth_score REAL DEFAULT 0,
            argument_score REAL DEFAULT 0,
            final_score REAL DEFAULT 0,
            
            -- Metadatos IA
            ai_model_used TEXT DEFAULT 'claude-3-sonnet-20240229',
            ai_tokens_used INTEGER DEFAULT 0,
            ai_processing_time_ms INTEGER DEFAULT 0,
            ai_raw_response TEXT,
            
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (result_id) REFERENCES results(id)
        );
        """
    )
    
    # NUEVA TABLA: Tokens de acceso para estudiantes
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS student_access_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT,
            
            FOREIGN KEY (result_id) REFERENCES results(id)
        );
        """
    )
    
    # Migrar columnas existentes de forma segura
    existing_columns = []
    try:
        cursor.execute("PRAGMA table_info(results)")
        existing_columns = [row[1] for row in cursor.fetchall()]
    except:
        pass
    
    migrations = [
        ('student_hash', 'ALTER TABLE results ADD COLUMN student_hash TEXT'),
        ('start_time', 'ALTER TABLE results ADD COLUMN start_time TEXT'),
        ('end_time', 'ALTER TABLE results ADD COLUMN end_time TEXT'),
        ('duration_seconds', 'ALTER TABLE results ADD COLUMN duration_seconds INTEGER'),
        ('paste_attempts', 'ALTER TABLE results ADD COLUMN paste_attempts INTEGER DEFAULT 0'),
        ('copy_attempts', 'ALTER TABLE results ADD COLUMN copy_attempts INTEGER DEFAULT 0'),
        ('total_penalties', 'ALTER TABLE results ADD COLUMN total_penalties REAL DEFAULT 0'),
        ('overall_level', 'ALTER TABLE results ADD COLUMN overall_level TEXT DEFAULT \'intermedio\''),
        ('general_feedback', 'ALTER TABLE results ADD COLUMN general_feedback TEXT'),
    ]
    
    for column_name, sql in migrations:
        if column_name not in existing_columns:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
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

def generate_student_access_token() -> str:
    """Generar token único para acceso del estudiante a sus resultados."""
    return secrets.token_urlsafe(32)

def generate_general_feedback(evaluations: List[Dict], level: str) -> str:
    """Generar feedback general basado en todas las evaluaciones."""
    
    # Calcular promedios por criterio
    criterios = ['opinion_fundada', 'valores_eticos', 'lenguaje_terminologia', 'citas_precision',
                'estructura_coherencia', 'profundidad_fundamentacion', 'capacidad_critica',
                'presentacion_estilo', 'innovacion_creatividad']
    
    promedios = {}
    for criterio in criterios:
        scores = [eval_data.get(criterio, 3) for eval_data in evaluations]
        promedios[criterio] = sum(scores) / len(scores) if scores else 3
    
    # Identificar fortalezas y debilidades
    fortalezas = sorted(promedios.items(), key=lambda x: x[1], reverse=True)[:3]
    debilidades = sorted(promedios.items(), key=lambda x: x[1])[:3]
    
    feedback_lines = []
    
    if level == 'avanzado':
        feedback_lines.append("🎓 **Nivel Avanzado Detectado** - Excelente dominio del tema.")
    elif level == 'basico':
        feedback_lines.append("📚 **Nivel Básico Detectado** - Fundamentos sólidos, continúe estudiando.")
    else:
        feedback_lines.append("📖 **Nivel Intermedio Detectado** - Buen entendimiento general.")
    
    feedback_lines.append(f"\n**Principales fortalezas:**")
    for criterio, score in fortalezas:
        criterio_nombre = criterio.replace('_', ' ').title()
        feedback_lines.append(f"• {criterio_nombre}: {score:.1f}/5.0")
    
    feedback_lines.append(f"\n**Áreas de mejora:**")
    for criterio, score in debilidades:
        criterio_nombre = criterio.replace('_', ' ').title()
        feedback_lines.append(f"• {criterio_nombre}: {score:.1f}/5.0")
    
    return "\n".join(feedback_lines)

###############################################################################
# AI Integration Functions - REAL CLAUDE EVALUATION
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

def evaluate_answer_with_ai_real(user_bool: bool, user_reason: str, correct_bool: bool, 
                                case_description: str, question_text: str, 
                                case_id: int, question_index: int) -> Tuple[float, Dict]:
    """
    Evaluación REAL con Claude API usando rúbrica de 9 criterios.
    Retorna: (score_final, diccionario_completo)
    """
    start_time = time.time()
    
    # Componente de verdad (1.5 puntos)
    truth_score = 1.5 if user_bool == correct_bool else 0.0
    
    # Valores por defecto si falla la IA
    default_result = {
        'opinion_fundada': 3,
        'valores_eticos': 3,
        'lenguaje_terminologia': 3,
        'citas_precision': 3,
        'estructura_coherencia': 3,
        'profundidad_fundamentacion': 3,
        'capacidad_critica': 3,
        'presentacion_estilo': 3,
        'innovacion_creatividad': 3,
        'feedback_general': 'Evaluación sin IA disponible. Puntuación por defecto asignada.',
        'feedback_fortalezas': 'No se pudo analizar con IA.',
        'feedback_mejoras': 'Configure Claude API key para evaluación detallada.',
        'truth_score': truth_score,
        'argument_score': 0.75,
        'final_score': truth_score + 0.75,
        'ai_tokens_used': 0,
        'ai_processing_time_ms': 0,
        'ai_model_used': 'none',
        'ai_raw_response': '{"error": "No API key"}'
    }
    
    if not CLAUDE_API_KEY:
        logger.warning("Claude API key not configured")
        return default_result['final_score'], default_result
    
    # Crear prompt específico para NFTs y Propiedad Intelectual
    evaluation_prompt = f"""
Eres un experto en Derecho de Propiedad Intelectual y tecnologías blockchain, especializado en NFTs. 

CASO JURÍDICO: {case_description}

PREGUNTA EVALUADA: {question_text}

RESPUESTA DEL ESTUDIANTE: {user_reason}

RESPUESTA CORRECTA: {"Verdadero" if correct_bool else "Falso"}
RESPUESTA DEL ESTUDIANTE: {"Verdadero" if user_bool else "Falso"}

EVALÚA esta respuesta usando exactamente estos 9 criterios (escala 1-5):

1. OPINIÓN FUNDADA (1-5): ¿Presenta una opinión jurídica respaldada en doctrina, jurisprudencia o normativa?
2. VALORES ÉTICOS (1-5): ¿Considera principios éticos del derecho de autor, acceso a la cultura, innovación?
3. LENGUAJE JURÍDICO (1-5): ¿Usa terminología legal precisa y apropiada?
4. CITAS Y PRECISIÓN (1-5): ¿Referencia normas, artículos o jurisprudencia relevante?
5. ESTRUCTURA Y COHERENCIA (1-5): ¿La argumentación es lógica y bien organizada?
6. PROFUNDIDAD (1-5): ¿Analiza las implicaciones jurídicas en profundidad?
7. CAPACIDAD CRÍTICA (1-5): ¿Evalúa críticamente los aspectos controvertidos del tema?
8. PRESENTACIÓN (1-5): ¿La redacción es clara y profesional?
9. INNOVACIÓN (1-5): ¿Aporta perspectivas novedosas o soluciones creativas?

ADEMÁS:
- Identifica 2-3 FORTALEZAS específicas de la respuesta
- Identifica 2-3 ÁREAS DE MEJORA específicas
- Da FEEDBACK CONSTRUCTIVO general

Responde SOLO en formato JSON válido:

{{
    "criterios": {{
        "opinion_fundada": [1-5],
        "valores_eticos": [1-5], 
        "lenguaje_terminologia": [1-5],
        "citas_precision": [1-5],
        "estructura_coherencia": [1-5],
        "profundidad_fundamentacion": [1-5],
        "capacidad_critica": [1-5],
        "presentacion_estilo": [1-5],
        "innovacion_creatividad": [1-5]
    }},
    "feedback_general": "Análisis general constructivo y específico...",
    "feedback_fortalezas": "1. Primera fortaleza específica. 2. Segunda fortaleza específica. 3. Tercera fortaleza específica.",
    "feedback_mejoras": "1. Primera área de mejora específica. 2. Segunda área de mejora específica. 3. Tercera área de mejora específica.",
    "promedio_criterios": 0.0,
    "nivel_detectado": "basico|intermedio|avanzado"
}}
"""
    
    try:
        # Llamada a Claude API
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 1200,
                'messages': [{'role': 'user', 'content': evaluation_prompt}]
            },
            timeout=25
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            response_data = response.json()
            ai_response = response_data['content'][0]['text']
            tokens_used = response_data.get('usage', {}).get('output_tokens', 0)
            
            logger.info(f"Claude API response received: {len(ai_response)} chars, {tokens_used} tokens")
            
            # Extraer JSON de la respuesta
            try:
                # Intentar parsear directamente
                if ai_response.strip().startswith('{'):
                    ai_result = json.loads(ai_response.strip())
                else:
                    # Buscar JSON dentro del texto
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_response, re.DOTALL)
                    if json_match:
                        ai_result = json.loads(json_match.group())
                    else:
                        raise ValueError("No JSON encontrado en respuesta")
                
                # Validar criterios
                criterios = ai_result.get('criterios', {})
                validated_criterios = {}
                
                for criterio in ['opinion_fundada', 'valores_eticos', 'lenguaje_terminologia',
                               'citas_precision', 'estructura_coherencia', 'profundidad_fundamentacion',
                               'capacidad_critica', 'presentacion_estilo', 'innovacion_creatividad']:
                    score = criterios.get(criterio, 3)
                    validated_criterios[criterio] = max(1, min(5, int(score))) if isinstance(score, (int, float)) else 3
                
                # Calcular promedio y puntaje de argumento
                promedio = sum(validated_criterios.values()) / len(validated_criterios)
                argument_score = (promedio / 5.0) * 1.5  # Escalar a 1.5 puntos máximo
                final_score = truth_score + argument_score
                
                # Resultado completo
                result = {
                    **validated_criterios,
                    'feedback_general': ai_result.get('feedback_general', 'Sin feedback general')[:2000],
                    'feedback_fortalezas': ai_result.get('feedback_fortalezas', 'Sin fortalezas identificadas')[:1000],
                    'feedback_mejoras': ai_result.get('feedback_mejoras', 'Sin mejoras sugeridas')[:1000],
                    'truth_score': truth_score,
                    'argument_score': argument_score,
                    'final_score': final_score,
                    'promedio_criterios': promedio,
                    'nivel_detectado': ai_result.get('nivel_detectado', 'intermedio'),
                    'ai_tokens_used': tokens_used,
                    'ai_processing_time_ms': processing_time,
                    'ai_model_used': 'claude-3-sonnet-20240229',
                    'ai_raw_response': ai_response[:2000]  # Limitar tamaño
                }
                
                logger.info(f"✅ Evaluación exitosa: {final_score:.2f}/3.0 (promedio criterios: {promedio:.2f})")
                return final_score, result
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing Claude response: {e}")
                logger.error(f"Raw response: {ai_response[:500]}")
                
                # Fallback: extraer información básica
                default_result.update({
                    'ai_tokens_used': tokens_used,
                    'ai_processing_time_ms': processing_time,
                    'ai_raw_response': ai_response[:2000],
                    'feedback_general': f'Error procesando respuesta de IA: {str(e)[:200]}'
                })
                
        else:
            error_msg = f"Claude API error {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            default_result['feedback_general'] = f'Error de API: {error_msg}'
            
    except requests.exceptions.Timeout:
        logger.error("Claude API timeout")
        default_result['feedback_general'] = 'Timeout en evaluación con IA. Intente nuevamente.'
        default_result['ai_processing_time_ms'] = int((time.time() - start_time) * 1000)
        
    except Exception as e:
        logger.error(f"Unexpected error in AI evaluation: {e}")
        default_result['feedback_general'] = f'Error inesperado: {str(e)[:200]}'
        default_result['ai_processing_time_ms'] = int((time.time() - start_time) * 1000)
    
    return default_result['final_score'], default_result

###############################################################################
# Routes for students
###############################################################################

@app.route('/')
def index() -> str:
    """Present the form for students to register for the exam."""
    if is_exam_blocked():
        return render_template('exam_blocked.html', deadline=EXAM_DEADLINE, 
                             guatemala_time=get_guatemala_time())
    
    return render_template('student_form.html', deadline=EXAM_DEADLINE,
                         guatemala_time=get_guatemala_time())

@app.route('/start_exam', methods=['POST'])
def start_exam() -> str:
    """Process the student registration and start the exam."""
    if is_exam_blocked():
        return render_template('exam_blocked.html', deadline=EXAM_DEADLINE,
                             guatemala_time=get_guatemala_time())
    
    student_name = request.form.get('student_name', '').strip()
    student_carne = request.form.get('student_carne', '').strip()
    
    if not student_name or not student_carne:
        flash('Por favor complete todos los campos requeridos.', 'error')
        return redirect(url_for('index'))
    
    # Check for duplicate attempts
    student_hash = get_student_hash(student_name, student_carne)
    if has_student_attempted(student_hash):
        flash('Ya ha completado el examen anteriormente. Solo se permite un intento por estudiante.', 'error')
        return redirect(url_for('index'))
    
    # Store student data in session
    session['student_name'] = student_name
    session['student_carne'] = student_carne
    session['student_hash'] = student_hash
    session['exam_start_time'] = get_guatemala_time().isoformat()
    
    return redirect(url_for('comprehensive_exam'))

@app.route('/comprehensive_exam')
def comprehensive_exam() -> str:
    """Present the comprehensive exam with all 5 cases."""
    if is_exam_blocked():
        return render_template('exam_blocked.html', deadline=EXAM_DEADLINE,
                             guatemala_time=get_guatemala_time())
    
    if 'student_name' not in session:
        flash('Debe registrarse primero antes de tomar el examen.', 'error')
        return redirect(url_for('index'))
    
    # Check for duplicate attempts again (in case of session manipulation)
    if has_student_attempted(session.get('student_hash', '')):
        flash('Ya ha completado el examen anteriormente.', 'error')
        return redirect(url_for('index'))
    
    return render_template('comprehensive_exam.html', 
                         cases=CASES, 
                         student_name=session.get('student_name'),
                         student_carne=session.get('student_carne'))

@app.route('/submit_comprehensive', methods=['POST'])
def submit_comprehensive() -> str:
    """Process the comprehensive exam submission with REAL AI evaluation."""
    if is_exam_blocked():
        return render_template('exam_blocked.html', deadline=EXAM_DEADLINE,
                             guatemala_time=get_guatemala_time())
    
    if 'student_name' not in session:
        flash('Sesión expirada. Debe registrarse nuevamente.', 'error')
        return redirect(url_for('index'))
    
    student_name = session.get('student_name')
    student_carne = session.get('student_carne')
    student_hash = session.get('student_hash')
    start_time_iso = session.get('exam_start_time')
    
    if not all([student_name, student_carne, student_hash, start_time_iso]):
        flash('Datos de sesión incompletos. Reinicie el examen.', 'error')
        return redirect(url_for('index'))
    
    # Check for duplicate submission
    if has_student_attempted(student_hash):
        flash('Ya ha completado el examen anteriormente.', 'error')
        return redirect(url_for('index'))
    
    # Calculate timing
    start_time = datetime.fromisoformat(start_time_iso)
    end_time = get_guatemala_time()
    duration_seconds = int((end_time - start_time).total_seconds())
    timestamp = end_time.isoformat()
    
    # Extract form data
    student_id = f"{student_name} ({student_carne})"
    total_score = 0.0
    total_paste_attempts = 0
    total_copy_attempts = 0
    total_penalties = 0.0
    
    all_answers = []
    all_question_evaluations = []
    
    logger.info(f"🚀 Iniciando evaluación con IA para {student_name}")
    
    # Process each case
    for case_id in CASES:
        case = CASES[case_id]
        case_answers = []
        case_score = 0
        
        for i in range(len(case.questions)):
            question_key = f"case_{case_id}_q{i}"
            answer_key = f"case_{case_id}_a{i}"
            
            user_bool = request.form.get(question_key) == 'true'
            user_reason = request.form.get(answer_key, '').strip()
            correct_bool = case.questions[i].correct
            
            if not user_reason:
                user_reason = "Sin justificación proporcionada."
            
            # EVALUACIÓN REAL CON CLAUDE API
            logger.info(f"🤖 Evaluando Caso {case_id}, Pregunta {i+1} con Claude...")
            question_score, evaluation_data = evaluate_answer_with_ai_real(
                user_bool, user_reason, correct_bool,
                case.description, case.questions[i].text,
                case_id, i
            )
            
            # Agregar datos de la pregunta a la evaluación
            evaluation_data.update({
                'case_id': case_id,
                'question_index': i,
                'user_answer_text': user_reason,
                'user_answer_bool': 1 if user_bool else 0,
                'correct_answer_bool': 1 if correct_bool else 0
            })
            
            all_question_evaluations.append(evaluation_data)
            
            case_answers.append({
                'user_bool': user_bool,
                'user_reason': user_reason,
                'correct': correct_bool,
                'score': question_score,
                'ai_feedback': {
                    'general': evaluation_data.get('feedback_general', ''),
                    'fortalezas': evaluation_data.get('feedback_fortalezas', ''),
                    'mejoras': evaluation_data.get('feedback_mejoras', '')
                }
            })
            
            case_score += question_score
            
            logger.info(f"✅ Pregunta {i+1} Caso {case_id}: {question_score:.2f}/3.0")
        
        all_answers.append({
            'case': case,
            'answers': case_answers,
            'score': case_score
        })
        
        total_score += case_score
    
    # Calcular nivel general del estudiante
    avg_score_per_question = total_score / 10  # 10 preguntas total
    overall_level = 'basico' if avg_score_per_question < 1.8 else ('avanzado' if avg_score_per_question >= 2.4 else 'intermedio')
    
    # Generar feedback general
    general_feedback = generate_general_feedback(all_question_evaluations, overall_level)
    
    logger.info(f"📊 Evaluación completa: {total_score:.1f}/30.0 - Nivel: {overall_level}")
    
    # Guardar en base de datos
    db = get_db()
    cur = db.cursor()
    
    # Guardar resultado principal
    answers_json = json.dumps({
        'student_name': student_name,
        'student_carne': student_carne,
        'all_cases': {str(case_data['case'].case_id): {
            'answers': [{
                'user_bool': ans['user_bool'],
                'user_reason': ans['user_reason'],
                'correct': ans['correct'],
                'score': ans['score']
            } for ans in case_data['answers']],
            'score': case_data['score']
        } for case_data in all_answers}
    })
    
    rubric_json = json.dumps({
        'total_score': total_score,
        'overall_level': overall_level,
        'general_feedback': general_feedback,
        'total_penalties': total_penalties,
        'paste_attempts': total_paste_attempts,
        'copy_attempts': total_copy_attempts,
        'max_possible_score': 30.0
    })
    
    cur.execute(
        """
        INSERT INTO results 
        (timestamp, student_id, student_hash, case_id, answers_json, score, rubric_json, 
         start_time, end_time, duration_seconds, paste_attempts, copy_attempts, total_penalties,
         overall_level, general_feedback) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (timestamp, student_id, student_hash, 0, answers_json, total_score, rubric_json,
         start_time.isoformat(), end_time.isoformat(), duration_seconds,
         total_paste_attempts, total_copy_attempts, total_penalties, overall_level, general_feedback)
    )
    result_id = cur.lastrowid
    
    # Guardar evaluaciones detalladas de cada pregunta
    for eval_data in all_question_evaluations:
        cur.execute(
            """
            INSERT INTO question_evaluations 
            (result_id, case_id, question_index, user_answer_text, user_answer_bool, correct_answer_bool,
             opinion_fundada, valores_eticos, lenguaje_terminologia, citas_precision, estructura_coherencia,
             profundidad_fundamentacion, capacidad_critica, presentacion_estilo, innovacion_creatividad,
             feedback_general, feedback_fortalezas, feedback_mejoras, truth_score, argument_score, final_score,
             ai_model_used, ai_tokens_used, ai_processing_time_ms, ai_raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (result_id, eval_data['case_id'], eval_data['question_index'], 
             eval_data['user_answer_text'], eval_data['user_answer_bool'], eval_data['correct_answer_bool'],
             eval_data['opinion_fundada'], eval_data['valores_eticos'], eval_data['lenguaje_terminologia'],
             eval_data['citas_precision'], eval_data['estructura_coherencia'], eval_data['profundidad_fundamentacion'],
             eval_data['capacidad_critica'], eval_data['presentacion_estilo'], eval_data['innovacion_creatividad'],
             eval_data['feedback_general'], eval_data['feedback_fortalezas'], eval_data['feedback_mejoras'],
             eval_data['truth_score'], eval_data['argument_score'], eval_data['final_score'],
             eval_data['ai_model_used'], eval_data['ai_tokens_used'], eval_data['ai_processing_time_ms'],
             eval_data['ai_raw_response'])
        )
    
    # Generar token de acceso para el estudiante
    access_token = generate_student_access_token()
    cur.execute(
        "INSERT INTO student_access_tokens (result_id, token) VALUES (?, ?)",
        (result_id, access_token)
    )
    
    # Log completion event
    cur.execute(
        "INSERT INTO events (result_id, event_type, event_time, details) VALUES (?, ?, ?, ?)",
        (result_id, 'exam_completed', timestamp, 
         f"Duration: {duration_seconds}s, Penalties: {total_penalties:.2f}, Level: {overall_level}")
    )
    
    db.commit()
    
    # Clear session data
    session.clear()
    
    logger.info(f"💾 Resultados guardados para {student_name} - Token: {access_token[:8]}...")
    
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
        general_feedback=general_feedback,
        overall_level=overall_level,
        result_id=result_id,
        access_token=access_token,
        detailed_evaluations=all_question_evaluations,
        max_score=30.0
    )

@app.route('/rubric')
def rubric() -> str:
    """Display the evaluation rubric."""
    return render_template('rubric.html')

@app.route('/info')
def info() -> str:
    """Display system information."""
    return render_template('info.html')

###############################################################################
# Routes for instructors
###############################################################################

@app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    """Login page for instructors."""
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
                  paste_attempts, copy_attempts, total_penalties, overall_level 
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
    
    # Get detailed evaluations
    cur.execute("""
        SELECT * FROM question_evaluations 
        WHERE result_id = ?
        ORDER BY case_id, question_index
    """, (result_id,))
    
    detailed_evaluations = cur.fetchall()
    
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
            
            return render_template('instructor_comprehensive_result.html',
                                 result=result,
                                 student_name=student_name,
                                 student_carne=student_carne,
                                 all_cases_answers=all_cases_answers,
                                 cases=CASES,
                                 rubric_data=rubric_data,
                                 events=events,
                                 detailed_evaluations=detailed_evaluations)
        else:
            # Single case exam (legacy)
            cur.execute(
                "SELECT event_type, event_time, details FROM events WHERE result_id = ?",
                (result_id,)
            )
            events = cur.fetchall()
            
            return render_template('result.html', 
                                 result=result, 
                                 case=CASES.get(result['case_id']),
                                 events=events,
                                 detailed_evaluations=detailed_evaluations)
                                 
    except json.JSONDecodeError:
        return "Error: Datos de resultado corruptos", 500

###############################################################################
# API Routes
###############################################################################

@app.route('/api/evaluation-details/<int:result_id>')
@require_instructor
def get_evaluation_details(result_id: int):
    """API endpoint para obtener detalles de evaluación por pregunta."""
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        SELECT qe.*, r.student_id 
        FROM question_evaluations qe
        JOIN results r ON qe.result_id = r.id
        WHERE qe.result_id = ?
        ORDER BY qe.case_id, qe.question_index
    """, (result_id,))
    
    evaluations = []
    for row in cur.fetchall():
        evaluations.append({
            'case_id': row['case_id'],
            'question_index': row['question_index'],
            'criterios': {
                'opinion_fundada': row['opinion_fundada'],
                'valores_eticos': row['valores_eticos'],
                'lenguaje_terminologia': row['lenguaje_terminologia'],
                'citas_precision': row['citas_precision'],
                'estructura_coherencia': row['estructura_coherencia'],
                'profundidad_fundamentacion': row['profundidad_fundamentacion'],
                'capacidad_critica': row['capacidad_critica'],
                'presentacion_estilo': row['presentacion_estilo'],
                'innovacion_creatividad': row['innovacion_creatividad']
            },
            'feedback': {
                'general': row['feedback_general'],
                'fortalezas': row['feedback_fortalezas'],
                'mejoras': row['feedback_mejoras']
            },
            'scores': {
                'truth': row['truth_score'],
                'argument': row['argument_score'],
                'final': row['final_score']
            },
            'metadata': {
                'tokens_used': row['ai_tokens_used'],
                'processing_time': row['ai_processing_time_ms'],
                'model_used': row['ai_model_used']
            }
        })
    
    return jsonify({'evaluations': evaluations})

# Ruta para estudiantes acceder a sus resultados
@app.route('/mis-resultados/<token>')
def student_results(token: str):
    """Mostrar resultados al estudiante usando su token de acceso."""
    db = get_db()
    cur = db.cursor()
    
    # Verificar token válido
    cur.execute("""
        SELECT r.*, sat.access_count 
        FROM student_access_tokens sat
        JOIN results r ON sat.result_id = r.id
        WHERE sat.token = ?
    """, (token,))
    
    result = cur.fetchone()
    if not result:
        return render_template('error.html', message="Token inválido o expirado"), 404
    
    # Actualizar contador de acceso
    cur.execute("""
        UPDATE student_access_tokens 
        SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
        WHERE token = ?
    """, (token,))
    db.commit()
    
    # Obtener evaluaciones detalladas
    cur.execute("""
        SELECT * FROM question_evaluations 
        WHERE result_id = ?
        ORDER BY case_id, question_index
    """, (result['id'],))
    
    detailed_evaluations = cur.fetchall()
    
    # Reconstruir datos para el template
    answers_data = json.loads(result['answers_json'])
    all_cases_data = []
    
    for case_id_str, case_info in answers_data.get('all_cases', {}).items():
        case_id = int(case_id_str)
        if case_id in CASES:
            case = CASES[case_id]
            all_cases_data.append({
                'case': case,
                'answers': case_info['answers'],
                'score': case_info['score']
            })
    
    return render_template('comprehensive_feedback.html',
                         all_cases_data=all_cases_data,
                         cases=CASES,
                         total_score=result['score'],
                         student_name=answers_data.get('student_name', 'N/A'),
                         student_carne=answers_data.get('student_carne', 'N/A'),
                         duration_minutes=result['duration_seconds'] // 60 if result['duration_seconds'] else 0,
                         general_feedback=result['general_feedback'],
                         overall_level=result['overall_level'],
                         detailed_evaluations=detailed_evaluations,
                         result_id=result['id'],
                         access_token=token,
                         max_score=30.0)

###############################################################################
# Application Entry Point
###############################################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)