# 🎓 Sistema de Evaluación NFTs y Propiedad Intelectual

**Academia LegalTech** - Sistema integral de evaluación académica sobre tokens no fungibles (NFTs) y propiedad intelectual en el contexto jurídico guatemalteco.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-Academic-yellow.svg)](#)

## 📋 Descripción General

Este sistema proporciona una plataforma completa para evaluar el conocimiento jurídico sobre NFTs y propiedad intelectual, utilizando:

- **5 casos de estudio** especializados en NFTs y derecho guatemalteco
- **Evaluación con IA** usando Claude API con rúbrica de 9 criterios
- **Sistema anti-trampa** con detección de copy/paste
- **Panel de instructor** con análisis estadístico detallado
- **Un solo intento por estudiante** para garantizar integridad académica

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
📁 NFT-Evaluation-System/
├── 🐍 app.py                          # Aplicación Flask principal
├── 📄 requirements.txt               # Dependencias Python
├── 🐳 Dockerfile                     # Configuración Docker
├── 📋 docker-compose.yml             # Orquestación de servicios
├── 🗃️ exam.db                        # Base de datos SQLite (generada)
├── 📁 templates/                     # Templates HTML Jinja2
│   ├── 🎨 base.html                  # Template base con framework CSS
│   ├── 📝 student_form.html          # Registro de estudiantes
│   ├── 📋 comprehensive_exam.html    # Examen integral (5 casos)
│   ├── 📊 comprehensive_feedback.html # Resultados para estudiantes
│   ├── 👨‍💼 dashboard.html              # Panel de instructor
│   ├── 🔒 login.html                 # Autenticación instructor
│   ├── 📈 result.html                # Vista individual de resultados
│   ├── 🔍 instructor_comprehensive_result.html # Análisis detallado
│   ├── 📚 rubric.html / info.html    # Información y rúbrica
│   └── ⛔ exam_blocked.html          # Examen cerrado
├── 📁 static/
│   └── ⚡ app.js                     # JavaScript específico NFT
└── 📄 info.html                      # Página independiente de rúbrica
```

### Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|------------|------------|---------|-----------|
| **Backend** | Flask | 3.0.0 | Framework web principal |
| **Base de Datos** | SQLite | 3.x | Almacenamiento de resultados |
| **IA** | Anthropic Claude | 3-Sonnet | Evaluación automática de respuestas |
| **Frontend** | HTML5 + CSS3 + JS | - | Interfaz responsiva moderna |
| **Contenorización** | Docker + Compose | - | Despliegue simplificado |
| **Autenticación** | Flask Sessions | - | Sesiones seguras |

## 🚀 Instalación y Configuración

### Método 1: Docker (Recomendado)

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd nft-evaluation-system

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con sus claves

# 3. Construir y ejecutar
docker-compose up --build

# 4. Acceder al sistema
# Estudiantes: http://localhost:8010
# Instructor: http://localhost:8010/login
```

### Método 2: Instalación Local

```bash
# 1. Crear entorno virtual
python3.10 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
export SECRET_KEY="your-secret-key"
export CLAUDE_API_KEY="your-claude-api-key"  # Opcional

# 4. Ejecutar aplicación
python app.py

# 5. Acceder en http://localhost:8000
```

### Variables de Entorno Requeridas

```env
# .env file
SECRET_KEY=your-flask-secret-key-here
CLAUDE_API_KEY=your-anthropic-claude-api-key-here
```

## 📚 Casos de Estudio NFT

El sistema incluye **5 casos especializados** basados en el documento académico ["NFTs: Un estudio sobre el alcance de la propiedad intelectual en los tokens no fungibles"](https://repositorio.uchile.cl/bitstream/handle/2250/199772/NFTs-un-estudio-sobre-el-alcance-de-la-propiedad-intelectual-en-los-tokens-no-fungibles.pdf) de la Universidad de Chile:

| Caso | Título | Enfoque Jurídico |
|------|--------|------------------|
| **1** | NFT como Título Traslativo de Dominio | Separación obra-soporte, cesión expresa |
| **2** | Smart Contracts y Regalías Automáticas | Validez jurídica de contratos inteligentes |
| **3** | Representación Digital vs Reproducción | Fijación digital y autorización |
| **4** | Uso Público de NFT Musical | Comunicación pública y licencias |
| **5** | NFT y Derechos Constitucionales | Balance cultura vs propiedad intelectual |

## 🤖 Sistema de Evaluación con IA

### Rúbrica de 9 Criterios (Claude API)

Cada justificación es evaluada automáticamente según:

1. **Opinión Propia Fundada** (1-5 pts)
2. **Valores Éticos** (1-5 pts)  
3. **Lenguaje y Terminología Jurídica** (1-5 pts)
4. **Citas y Precisión Normativa** (1-5 pts)
5. **Estructura y Coherencia** (1-5 pts)
6. **Profundidad de Fundamentación** (1-5 pts)
7. **Capacidad Crítica** (1-5 pts)
8. **Presentación y Estilo** (1-5 pts)
9. **Innovación y Creatividad Argumentativa** (1-5 pts)

### Puntuación por Pregunta

```
Total: 3 puntos máximos por pregunta
├── Veracidad (V/F): 1.5 puntos
├── Argumentación IA: 1.5 puntos (promedio 9 criterios)
└── Penalizaciones: hasta -0.75 por copy/paste detectado
```

**Puntuación Total del Examen: 30 puntos (10 preguntas × 3 puntos)**

## 🛡️ Características Anti-Trampa

### Medidas de Seguridad Implementadas

- **Hash único por estudiante**: Previene múltiples intentos
- **Detección de copy/paste**: Algoritmo que identifica contenido pegado
- **Análisis de patrones de texto**: Detecta respuestas no originales
- **Un solo intento**: Sistema de validación estricto
- **Tiempo límite**: Fecha de cierre automático del examen

### Penalizaciones Automáticas

```python
# Detección automática de copy/paste
paste_penalty = paste_attempts * 0.25 + copy_attempts * 0.5  # Hasta -0.75 pts
```

## 👨‍💼 Panel de Instructor

### Funcionalidades del Dashboard

- **📊 Estadísticas en tiempo real**: Promedio, tasa de aprobación, completados
- **🔍 Filtros avanzados**: Por tipo, puntuación, fecha
- **📋 Análisis detallado**: Desglose por caso y criterio IA
- **📤 Exportación**: Datos en CSV para análisis externo
- **👁️ Vista individual**: Análisis completo por estudiante
- **📈 Gráficos**: Visualización de rendimiento académico

### Credenciales de Acceso

```
Usuario: Instructor
Contraseña: organismojudicial
URL: /login
```

## 🗄️ Estructura de Base de Datos

### Tabla `results`
```sql
CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    student_id TEXT,
    student_hash TEXT,          -- Hash único para prevenir duplicados
    case_id INTEGER NOT NULL,   -- 0 = Examen integral
    answers_json TEXT NOT NULL, -- Respuestas completas en JSON
    score REAL NOT NULL,        -- Puntuación final
    rubric_json TEXT NOT NULL,  -- Desglose de evaluación
    start_time TEXT,
    end_time TEXT,
    duration_seconds INTEGER,
    paste_attempts INTEGER DEFAULT 0,
    copy_attempts INTEGER DEFAULT 0,
    total_penalties REAL DEFAULT 0
);
```

### Tabla `events`
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER,
    event_type TEXT NOT NULL,   -- Tipo de evento (exam_completed, paste_detected)
    event_time TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY (result_id) REFERENCES results(id)
);
```

## 🌐 API y Endpoints

### Rutas Públicas (Estudiantes)
```
GET  /                          # Página principal y registro
POST /start_exam               # Procesar registro e iniciar examen
GET  /comprehensive_exam       # Mostrar examen integral
POST /submit_comprehensive     # Enviar respuestas del examen
GET  /rubric                   # Ver rúbrica de evaluación
GET  /info                     # Información del sistema
```

### Rutas Administrativas (Instructor)
```
GET/POST /login               # Autenticación
GET  /dashboard              # Panel principal de administración
GET  /result/<id>            # Ver resultado específico
GET  /logout                 # Cerrar sesión administrativa
```

## 🎨 Framework Frontend

### Componentes UI Utilizados

- **Framework CSS**: Custom PROFINS XXIV Theme
- **Tipografía**: Inter + Lexend Deca (Google Fonts)
- **Iconos**: Font Awesome 6.4.0
- **Componentes**: Cards responsivas, progress rings, dashboards
- **JavaScript**: Vanilla JS con funcionalidades específicas NFT

### Características UI/UX

- ✅ **Responsive Design**: Adaptable a mobile, tablet, desktop
- ✅ **Dark/Light Mode**: Toggle de tema automático
- ✅ **Animaciones**: Transiciones suaves y progressive enhancement
- ✅ **Accesibilidad**: Contraste adecuado, navegación por teclado
- ✅ **Progressive Web App**: Funcionalidad offline básica

## ⚙️ Configuración Avanzada

### Personalizar Fecha Límite del Examen

```python
# En app.py, línea ~45
EXAM_DEADLINE = datetime(2025, 8, 27, 23, 59, 0, tzinfo=GUATEMALA_TZ)
```

### Modificar Casos de Estudio

Los casos están definidos en `app.py` en el diccionario `CASES` (líneas 85-200). Cada caso incluye:

```python
Case(
    case_id=1,
    title="Título del Caso",
    description="Descripción detallada...",
    questions=[
        Question(
            text="Pregunta 1...",
            correct=True/False,
            keywords=["nft", "propiedad", "intelectual"]
        )
    ]
)
```

### Configurar Evaluación IA (Claude)

```python
# Modelo y configuración en evaluate_answer_with_ai()
'model': 'claude-3-sonnet-20240229',
'max_tokens': 2000,
# Prompt personalizado con 9 criterios específicos
```

## 🚀 Despliegue en Producción

### Docker Compose (Recomendado)

```yaml
# docker-compose.yml
services:
  exam_app:
    build: .
    ports:
      - "8010:8000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    restart: unless-stopped
```

### Variables de Entorno Producción

```bash
# Configuración mínima requerida
export SECRET_KEY="production-secret-key-minimum-32-characters"
export CLAUDE_API_KEY="sk-ant-api-key-from-anthropic"  # Opcional pero recomendado
export FLASK_ENV="production"  # Auto-configurado en Docker
```

### Nginx Reverse Proxy (Opcional)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🧪 Testing y Desarrollo

### Datos de Prueba

```bash
# Estudiante de prueba
Nombre: Juan Pérez
ID: TEST001

# Credenciales instructor
Password: organismojudicial
```

### Logs y Debugging

```python
# Activar logs detallados
import logging
logging.basicConfig(level=logging.INFO)
```

## 📊 Métricas y Analytics

### KPIs Disponibles

- **Tasa de Completación**: % de exámenes finalizados
- **Promedio de Puntuación**: Rendimiento general
- **Análisis por Caso**: Dificultad relativa de cada caso NFT
- **Detección de Trampa**: Intentos de copy/paste
- **Tiempo de Resolución**: Duración promedio del examen
- **Evaluación IA**: Desglose por criterios específicos

## 🤝 Contribución y Desarrollo

### Estructura para Nuevas Características

1. **Nuevos casos NFT**: Modificar diccionario `CASES` en `app.py`
2. **Criterios IA adicionales**: Actualizar prompt en `evaluate_answer_with_ai()`
3. **Templates personalizados**: Crear en carpeta `templates/`
4. **Funcionalidades JS**: Agregar a `static/app.js`

### Branching Strategy

```bash
main                    # Producción estable
├── develop            # Desarrollo activo
├── feature/new-cases  # Nuevos casos NFT
└── hotfix/security    # Correcciones críticas
```

## 📄 Licencia y Uso Académico

Este sistema está diseñado para uso académico e investigativo en el contexto de:

- **Instituciones educativas**: Universidades, institutos de derecho
- **Capacitación legal**: Formación en propiedad intelectual
- **Investigación jurídica**: Análisis de NFTs y blockchain law

## 📞 Soporte y Contacto

- **Desarrollo**: LegalTech Guatemala
- **Academia**: Sistema de evaluación especializado
- **Documentación**: Este README y comentarios en código
- **Issues**: Use el sistema de issues del repositorio para reportar bugs

## 🔄 Roadmap

### Versión 1.1 (Próxima)
- [ ] Exportación PDF de resultados
- [ ] Múltiples idiomas (español/inglés)
- [ ] Integración con LMS (Moodle, Canvas)
- [ ] API REST para integraciones externas

### Versión 1.2
- [ ] Machine Learning para detección de plagio
- [ ] Dashboard avanzado con charts dinámicos
- [ ] Notificaciones email automáticas
- [ ] Backup automático de base de datos

---

## 🎯 Quick Start

```bash
# 1. Clonar y configurar
git clone <repo-url> && cd nft-evaluation-system
cp .env.example .env

# 2. Docker up
docker-compose up --build

# 3. Acceder
open http://localhost:8010
```

**¡El sistema está listo para evaluar conocimientos sobre NFTs y Propiedad Intelectual!** 🎓🔗

---

*Desarrollado con ❤️ por LegalTech Guatemala - Academia de Innovación Jurídica*