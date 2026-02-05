# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Multi-Business Voice Service** - Servicio de voz generico para gestion de reservas/citas usando ElevenLabs Conversational AI y Google Sheets como backend. Adaptable a cualquier negocio cambiando solo archivos de configuracion.

**Current Version**: 2.1.0
**Status**: Funcionando en desarrollo local con ngrok

### Negocio Activo

| Negocio | Agent ID | Spreadsheet | Voice ID |
|---------|----------|-------------|----------|
| **Bella Italia (restaurante)** | `agent_7901kgfexyhvejbsr5ayg5nwxzsm` | `1UZYHP7BsnCVOHxdhSj30b5v2TiR2XdDTGYrRhk-zxGE` | `a5JUEQmqerfl9XqGF6dK` |

### Otros Negocios Configurados (backups)

| Negocio | Agent ID | Config backup |
|---------|----------|---------------|
| Clinica Dental Sonrisa | `agent_4201kgqdrhpnf889adk1qk05zjdm` | `*.dental` (pendiente crear) |

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User speaks   │────>│   ElevenLabs    │────>│  Voice Service  │
│   to agent      │     │     Agent       │     │   (FastAPI)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                               │                         │
                        Webhooks (tools)        Google Sheets API
                               │                         │
        ┌──────────────────────┘                         │
        │                                                │
        v                                                v
 ┌─────────────┐                               ┌──────────────────┐
 │   config/   │                               │  Google Sheets   │
 │             │                               │                  │
 │ business.   │──> nombre, duracion,          │  Mesas/Recursos  │
 │  yaml       │    mesas, mensajes,           │  Reservas/Citas  │
 │             │    tool descriptions          └──────────────────┘
 │ agent_      │
 │  prompt.txt │──> personalidad del agente
 │             │
 │ config_     │
 │  loader.py  │──> singleton que carga todo
 └─────────────┘
```

### Concepto clave: "Tables" es generico

El codigo usa "tables" internamente pero representa **cualquier recurso reservable**:

| Negocio | "Tables" son | duration_hours | party_size |
|---------|-------------|----------------|------------|
| Restaurante | Mesas | 2.0 | 1-20 |
| Dentista | Consultorios | 1.0 | 1-3 |
| Peluqueria | Sillas/Estilistas | 0.5-1.5 | 1 |
| Veterinaria | Consultorios | 0.5 | 1 |
| Spa | Cabinas/Salas | 1.0-2.0 | 1-4 |
| Cancha deportiva | Canchas | 1.0-2.0 | 2-22 |

## Multi-Business Configuration System

### Adaptar a un nuevo negocio (sin tocar codigo Python)

```
1. Editar config/business.yaml    -> nombre, recursos, duracion, mensajes
2. Editar config/agent_prompt.txt -> personalidad del agente de voz
3. Editar .env                    -> API keys, Sheet ID, Agent ID, webhook URL
4. Crear Google Sheet + compartir con service account
5. python setup_sheets.py         -> crea estructura en Google Sheets
6. python configure_elevenlabs.py -> actualiza agente con prompt + tools
7. uvicorn app.main:app           -> servicio listo
```

### Archivos que se editan vs. archivos que nunca se tocan

```
 EDITAR (config):                    NUNCA TOCAR (codigo):
 ├── config/business.yaml            ├── app/main.py
 ├── config/agent_prompt.txt         ├── app/api/tables.py
 ├── .env                            ├── app/services/google_sheets_service.py
 └── index.html (agent-id)           └── config/config_loader.py
```

### config/business.yaml

Configuracion maestra del negocio:
- `business_name` / `business_type` - nombre y tipo
- `reservation.duration_hours` - duracion de cada reserva/cita
- `reservation.max_party_size` - max personas por reserva
- `tables[]` - lista de recursos (mesas, consultorios, sillas, etc.)
- `tool_descriptions` - textos de los tools para ElevenLabs
- `messages` - 22 mensajes del sistema con placeholders `{variable}`

### config/agent_prompt.txt

Texto plano con la personalidad y reglas del agente de voz. Se sube a ElevenLabs via `configure_elevenlabs.py`.

### config/config_loader.py

Singleton que carga la config. Se importa asi:

```python
from config.config_loader import config

config.business_name          # "Bella Italia"
config.duration_hours         # 2.0
config.tables                 # lista de recursos (9 mesas)
config.tool_descriptions      # dict de descripciones
config.agent_prompt           # texto del prompt (7473 chars en v2.1)
config.msg("key", var=value)  # mensaje formateado
config.get_mock_tables()      # tablas para mock mode
```

## Common Commands

### Development

```bash
# Start service locally
cd /Users/A1064331/Desktop/pruebas/servicio_voz/voice-service
uvicorn app.main:app --reload --port 8000

# Start ngrok tunnel (in separate terminal)
ngrok http 8000

# Setup Google Sheets structure (reads tables from business.yaml)
python setup_sheets.py

# Configure ElevenLabs agent (updates prompt + creates tools)
python configure_elevenlabs.py

# List current ElevenLabs tools
python configure_elevenlabs.py list

# Test config loading
python -c "from config.config_loader import config; print(config.business_name)"
```

### Testing API

```bash
# Health check
curl http://localhost:8000/health/live

# List resources (tables/consultorios/etc)
curl http://localhost:8000/widget-api/tables/v1/tables

# Check availability
curl -X POST http://localhost:8000/widget-api/tables/v1/availability \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-02-10","time":"10:00","party_size":1}'

# Create reservation/appointment
curl -X POST http://localhost:8000/widget-api/tables/v1/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-02-10",
    "time": "10:00",
    "party_size": 1,
    "customer_name": "Maria Garcia",
    "customer_phone": "6145551234",
    "special_requests": "Limpieza dental"
  }'

# Search reservations by phone
curl -X POST http://localhost:8000/widget-api/tables/v1/search \
  -H "Content-Type: application/json" \
  -d '{"phone":"6145551234"}'

# Cancel reservation
curl -X POST http://localhost:8000/widget-api/tables/v1/cancel \
  -H "Content-Type: application/json" \
  -d '{"reservation_id":"RES-xxx","phone":"6145551234"}'

# Modify reservation
curl -X POST http://localhost:8000/widget-api/tables/v1/modify \
  -H "Content-Type: application/json" \
  -d '{"reservation_id":"RES-xxx","phone":"6145551234","new_date":"2026-02-11","new_time":"11:00"}'

# Update notes
curl -X POST http://localhost:8000/widget-api/tables/v1/update-notes \
  -H "Content-Type: application/json" \
  -d '{"reservation_id":"RES-xxx","phone":"6145551234","notes":"Alergia a penicilina"}'
```

### Deployment (Cloud Run)

```bash
docker build -t voice-service .
docker run -p 8080:8080 --env-file .env voice-service

gcloud run deploy voice-service \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --env-vars-file=cloudrun-env.yaml
```

## Configuration

### Environment Variables (.env)

```bash
# ElevenLabs
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_AGENT_ID=agent_xxx
ELEVENLABS_VOICE_ID=voice_id_xxx  # Optional: custom voice

# Webhook URL (ngrok for dev, Cloud Run URL for prod)
WEBHOOK_BASE_URL=https://your-url.ngrok-free.app

# Google Service Account (JSON string)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# Google Sheets
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_SHEETS_MESAS_SHEET=Mesas
GOOGLE_SHEETS_RESERVAS_SHEET=Reservas
```

### Google Sheets Structure

Created automatically by `setup_sheets.py` from `config/business.yaml`.

**Hoja "Mesas"** (recursos reservables):
| ID | Nombre | Capacidad | Ubicacion | Activa |
|----|--------|-----------|-----------|--------|

**Hoja "Reservas"** (citas/reservas):
| ID | MesaID | Fecha | HoraInicio | HoraFin | NombreCliente | Telefono | NumPersonas | Estado | Notas | CreadoEn |

### ElevenLabs Agent

Agentes se crean via API (`POST /v1/convai/agents/create`) o desde la consola de ElevenLabs. Los tools y prompt se configuran con `configure_elevenlabs.py`.

**Webhook Tools** (configurables en business.yaml):

| Tool | Descripcion |
|------|-------------|
| check_table_availability | Verifica disponibilidad |
| create_reservation | Crea reserva/cita |
| search_reservations | Busca por telefono |
| cancel_reservation | Cancela reserva/cita |
| modify_reservation | Modifica fecha/hora |
| update_notes | Agrega notas (acumulativas) |

**System Tools** (provistos por ElevenLabs):

| Tool | Uso |
|------|-----|
| end_call | Terminar la llamada (agresividad, transferencia, fin natural) |
| language_detection | Detectar idioma del usuario |

### Frontend (Widget)

`index.html` contiene el widget embebido de ElevenLabs. Solo requiere actualizar el `agent-id`:

```html
<elevenlabs-convai agent-id="agent_xxx"></elevenlabs-convai>
```

## Key Files

```
voice-service/
├── config/                          # CONFIGURACION (lo unico que se edita)
│   ├── business.yaml                #   Nombre, duracion, recursos, mensajes, tool descriptions
│   ├── agent_prompt.txt             #   Personalidad del agente de voz
│   ├── config_loader.py             #   Singleton que carga la config
│   └── __init__.py
├── app/                             # CODIGO (no se toca para cambiar de negocio)
│   ├── main.py                      #   FastAPI entry point (lee config)
│   ├── api/
│   │   └── tables.py                #   API router - webhooks para ElevenLabs
│   └── services/
│       └── google_sheets_service.py #   Google Sheets integration (lee config)
├── configure_elevenlabs.py          # Script: configura agente (prompt + tools)
├── setup_sheets.py                  # Script: crea estructura en Google Sheets
├── index.html                       # Frontend con widget de ElevenLabs
├── elevenlabs_tools_config.json     # Referencia de config de tools
├── Dockerfile                       # Docker config para Cloud Run
├── cloudrun-env.yaml                # Cloud Run env vars
├── requirements.txt                 # Python dependencies (incluye pyyaml)
├── .env                             # Variables de entorno locales
└── sheets-credentials.json          # Google Service Account credentials
```

## API Endpoints

### Health
- `GET /health/live` - Liveness check (muestra business_name)
- `GET /health/ready` - Readiness check with dependencies

### Root
- `GET /` - Info del servicio con nombre del negocio y endpoints

### Tables API (`/widget-api/tables/v1/`)
- `GET /` - Documentacion de tools (lee descripciones de config)
- `GET /health` - Estado de conexion a Google Sheets
- `GET /tables` - Lista de recursos (mesas/consultorios/etc)
- `POST /availability` - Verificar disponibilidad
- `POST /reserve` - Crear reserva/cita
- `POST /search` - Buscar por telefono
- `POST /cancel` - Cancelar reserva/cita
- `POST /modify` - Modificar fecha/hora
- `POST /update-notes` - Agregar notas (acumulativas)

## Reservation Logic

1. **Check Availability**:
   - Encuentra recursos con capacidad >= party_size
   - Verifica conflictos de horario (duracion configurable en `business.yaml`)
   - Un recurso NO puede tener dos reservas que se solapen
   - Retorna recursos disponibles ordenados por capacidad (menor primero)

2. **Create Reservation**:
   - Verifica disponibilidad automaticamente
   - Asigna el recurso mas pequeno disponible
   - Genera ID interno (no se muestra al cliente)
   - Calcula hora de fin (inicio + `config.duration_hours`)
   - Escribe en Google Sheets

3. **Search/Cancel/Modify**:
   - Requiere verificacion por telefono
   - Solo afecta reservas no canceladas

4. **Mock Mode**:
   - Se activa cuando `GOOGLE_SERVICE_ACCOUNT_JSON` no esta configurado
   - Lee recursos de `config/business.yaml` via `config.get_mock_tables()`

## Testing Flow

1. Start local service: `uvicorn app.main:app --reload --port 8000`
2. Start ngrok: `ngrok http 8000`
3. Update `WEBHOOK_BASE_URL` in `.env` if URL changed
4. Run `python configure_elevenlabs.py` to update agent prompt + tools
5. Open `index.html` in browser to test voice widget
6. Or test with curl commands

### Habilitar Modo Texto en Widget

Para probar con texto ademas de voz:
1. Ir a https://elevenlabs.io/app
2. Seleccionar el agente activo
3. **Widget** > **Interface** > Cambiar a **"Voice + text"**
4. Guardar cambios

## Current Status

### Funcionalidad Core
- [x] Google Sheets structure configured
- [x] Tables API implemented (6 endpoints + health)
- [x] ElevenLabs tools configured (6 webhooks + end_call + language_detection)
- [x] Mock data mode for offline testing
- [x] Dockerfile ready for Cloud Run
- [x] Table conflict detection working (no double-booking)
- [x] Phone validation relaxed (no country code required)
- [x] Agent configured to NOT mention reservation codes

### Sistema de Configuracion (v2.0)
- [x] **Multi-business config system** (business.yaml + agent_prompt.txt)
- [x] **Config-driven messages** (22 messages with placeholders)
- [x] **Config-driven mock data** (tables from YAML)
- [x] **Programmatic ElevenLabs agent creation** (POST /v1/convai/agents/create)
- [x] **Frontend widget** (index.html with ElevenLabs embed)
- [x] **Voice ID configurable** via ELEVENLABS_VOICE_ID

### Experiencia Conversacional (v2.1)
- [x] **Flujo natural**: Una pregunta a la vez
- [x] **Idioma consistente**: Solo espanol por defecto
- [x] **Escalamiento de agresividad**: 3 niveles antes de end_call
- [x] **Transferencia a humano**: Mensaje + end_call (temporal)
- [x] **Uso de end_call**: Documentado para terminar llamadas

### Pendientes
- [ ] Production deployment
- [ ] Transferencia real a humano (Twilio/webhook)
- [ ] Metricas de llamadas terminadas

## Comparativa: v000 (original) vs v2.0.0 (actual)

### Estructura de carpetas

| | v000 (original) | v2.0.0 (actual) |
|---|---|---|
| **config/** | No existe | **NUEVO** - Sistema de configuracion |
| **config/business.yaml** | - | Configuracion del negocio |
| **config/agent_prompt.txt** | - | Prompt del agente de voz |
| **config/config_loader.py** | - | Singleton que carga la config |
| **index.html** | No existe | **NUEVO** - Frontend con widget |
| **test.html** | Existe | Existe |
| **.git/** | No existe | Existe (repo inicializado) |
| **Backups (.bellaitalia)** | - | .env, business.yaml, agent_prompt.txt |

### Archivos principales (lineas de codigo)

| Archivo | v000 | v2.0.0 | Diferencia |
|---------|------|--------|------------|
| `app/main.py` | 151 | 153 | +2 (import config) |
| `app/api/tables.py` | 468 | 448 | -20 (usa config) |
| `app/services/google_sheets_service.py` | 801 | 803 | +2 (import config) |
| `configure_elevenlabs.py` | 293 | 339 | +46 (lee config, update_prompt) |
| `setup_sheets.py` | 82 | 89 | +7 (lee config) |

### Dependencias (requirements.txt)

| v000 | v2.0.0 |
|------|--------|
| 12 dependencias | 13 dependencias |
| - | **+pyyaml==6.0.1** |

### Diferencias clave en el enfoque

| Aspecto | v000 (original) | v2.0.0 (actual) |
|---------|-----------------|-----------------|
| **Nombre negocio** | Hardcoded "Bella Italia" | Lee de `config.business_name` |
| **Duracion reserva** | Hardcoded `2.0` horas | Lee de `config.duration_hours` |
| **Mensajes sistema** | Hardcoded en espanol | Lee de `config.messages` con placeholders |
| **Mock tables** | Lista hardcoded en codigo | Lee de `config.get_mock_tables()` |
| **Tool descriptions** | Hardcoded en `configure_elevenlabs.py` | Lee de `config.tool_descriptions` |
| **Agent prompt** | No se actualiza via script | Se sube desde `agent_prompt.txt` |
| **Adaptabilidad** | Solo para restaurante | Cualquier negocio (dental, spa, etc.) |
| **Frontend** | Solo `test.html` | `index.html` con widget ElevenLabs |

### Resumen

**v000** = Version especifica para Bella Italia con todo hardcoded en el codigo Python.

**v2.0.0** = Version generica multi-negocio donde:
- Todo lo configurable esta en `config/` (YAML + TXT)
- El codigo Python es generico y no se toca para cambiar de negocio
- Se pueden tener backups de configs para multiples negocios (`.bellaitalia`)
- Incluye frontend con widget de ElevenLabs
- Probado con 2 negocios: restaurante y clinica dental

## Changelog

### v2.1.0 (2026-02-05) - Mejoras de Experiencia Conversacional
1. **Flujo natural**: Una pregunta a la vez (REGLA DE ORO)
2. **Idioma consistente**: Solo espanol, italiano solo si el cliente lo pide
3. **Escalamiento de agresividad**: 3 niveles antes de usar end_call
4. **Transferencia a humano**: Mensaje + end_call (TODO: integrar transferencia real)
5. **Uso de end_call**: Documentado para terminar llamadas apropiadamente
6. **Prompt simplificado**: De 9505 chars a 7473 chars, mas directo y claro

### v2.0.0 (2026-02-05) - Multi-Business Config System
1. **config/business.yaml**: Configuracion maestra (nombre, duracion, recursos, mensajes, tool descriptions)
2. **config/agent_prompt.txt**: Prompt del agente de voz como archivo de texto
3. **config/config_loader.py**: Singleton `config` con `msg()` helper para mensajes formateados
4. **Todos los hardcoded eliminados**: mensajes, duracion, mock data, nombre del negocio
5. **configure_elevenlabs.py**: Ahora actualiza prompt del agente + lee descripciones de config
6. **setup_sheets.py**: Lee definicion de recursos y spreadsheet ID de config/.env
7. **index.html**: Frontend con widget embebido de ElevenLabs
8. **Probado con 2 negocios**: Bella Italia (restaurante) y Clinica Dental Sonrisa

### v1.1.0 (2026-02-04)
1. Telefono flexible (sin codigo de pais)
2. Sin codigo de reservacion visible al cliente
3. Verificacion de conflictos de horario
4. update_notes tool (notas acumulativas)
5. Manejo de clientes molestos

## Plan v2.1.0 - Mejoras de Experiencia Conversacional

### Fecha: 2026-02-05
### Estado: COMPLETADO

### Problemas Detectados en Pruebas
1. Se traba cuando la situacion se pone agresiva
2. No hay forma de terminar la llamada proactivamente
3. Hace muchas preguntas de entrada (no se siente humano)
4. No hay opcion de transferir a humano
5. Mezcla idiomas innecesariamente (italiano/espanol)

### Cambios Planificados

| # | Problema | Solucion | Archivo |
|---|----------|----------|---------|
| 1 | Agresividad | Advertir que terminara la llamada, luego usar `end_call` | agent_prompt.txt |
| 2 | Terminar llamada | Documentar uso del system tool `end_call` | agent_prompt.txt |
| 3 | Muchas preguntas | Flujo natural: UNA pregunta a la vez, esperar respuesta | agent_prompt.txt |
| 4 | Transferir humano | Por ahora: colgar con mensaje. **TODO**: integrar transferencia real | agent_prompt.txt |
| 5 | Mezcla idiomas | Solo espanol, italiano solo si el cliente lo pide | agent_prompt.txt |
| 6 | General | Mejorar naturalidad, pausas, confirmaciones | agent_prompt.txt |

### Detalle de Cambios al Prompt

#### 1. Manejo de Agresividad (ESCALADO)
```
Nivel 1: Empatia -> "Entiendo tu frustracion..."
Nivel 2: Advertencia -> "Si continua asi, tendre que terminar la llamada"
Nivel 3: Terminar -> Usar end_call con mensaje de despedida
```

#### 2. System Tool end_call
- Ya existe como tool del sistema en ElevenLabs
- Usarlo cuando: cliente muy agresivo, solicita terminar, o transferencia a humano

#### 3. Flujo Conversacional Natural
- NUNCA hacer 2+ preguntas seguidas
- Esperar respuesta antes de la siguiente pregunta
- Ejemplo MALO: "Para cuantos? Y que dia?"
- Ejemplo BUENO: "Para cuantas personas seria?" [espera] "Perfecto, y que dia tenian pensado?"

#### 4. Transferencia a Humano
- Cuando el cliente pida hablar con humano o gerente
- **TEMPORAL**: Decir "Lo comunico con el gerente" + end_call
- **TODO PRODUCCION**: Integrar con sistema de transferencia real (Twilio, etc.)

#### 5. Idioma Consistente
- Hablar 100% en espanol
- Expresiones italianas SOLO si el cliente las usa primero
- O si el cliente pide explicitamente que hable en italiano

### Notas de Implementacion

**TODO para produccion:**
- [ ] Integrar transferencia real a humano (webhook o Twilio)
- [ ] Agregar metrica de llamadas terminadas por agresividad
- [ ] Logging de cuando se usa end_call y por que razon

---

## Ideas para Futuras Funcionalidades

### Alta Prioridad

| Funcionalidad | Descripcion | Complejidad |
|---------------|-------------|-------------|
| **Confirmacion por SMS/WhatsApp** | Enviar confirmacion automatica | Media |
| **Recordatorio de reserva** | Notificacion 24h antes | Media |
| **Lista de espera** | Si no hay disponibilidad, anotarse en lista | Media |
| **Horarios del negocio** | Validar que la cita sea en horario de atencion | Baja |
| **Creacion de agente via script** | `python create_agent.py` para crear agente nuevo sin UI | Baja |

### Media Prioridad

| Funcionalidad | Descripcion | Complejidad |
|---------------|-------------|-------------|
| **Multi-idioma** | Atender en varios idiomas | Media |
| **Catalogo de servicios** | Informar sobre servicios, precios | Media |
| **Feedback post-visita** | Recoger opiniones | Media |
| **Dashboard admin** | Panel web para ver reservas | Alta |

### Integraciones Sugeridas

| Servicio | Uso |
|----------|-----|
| **Twilio/WhatsApp Business** | Confirmaciones y recordatorios |
| **Google Calendar** | Sincronizar citas con calendario |
| **Stripe/OpenPay** | Depositos para reservas |
| **Google Analytics** | Metricas de uso del asistente |
