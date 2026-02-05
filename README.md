# Multi-Business Voice Service

**Version 2.1.0** | Servicio de voz para gestion de reservas y citas usando ElevenLabs Conversational AI y Google Sheets.

Adaptable a cualquier negocio cambiando solo archivos de configuracion.

## Caracteristicas

- **Reservas por voz y texto** - Widget de ElevenLabs con soporte dual
- **Flujo conversacional natural** - Una pregunta a la vez
- **Manejo de situaciones dificiles** - Escalamiento de agresividad con end_call
- **Transferencia a humano** - Opcion de escalar a gerente/encargado
- **Multi-negocio** - Restaurantes, clinicas, spas, peluquerias, etc.
- **Cero codigo** - Solo editas archivos de configuracion

## Arquitectura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Cliente   │────>│  ElevenLabs │────>│   FastAPI   │────>│   Google    │
│  (Voz/Texto)│     │    Agent    │     │   Service   │     │   Sheets    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                      Webhooks            Lee config de:
                       (tools)            config/business.yaml
                                          config/agent_prompt.txt
```

## Negocio Activo

| Negocio | Agente | Asistente |
|---------|--------|-----------|
| **Bella Italia** (restaurante) | `agent_7901kgfexyhvejbsr5ayg5nwxzsm` | Noema |

## Funcionalidades

| Funcion | Descripcion |
|---------|-------------|
| Verificar disponibilidad | Consulta recursos libres por fecha/hora |
| Crear reserva | Registra nueva reserva con datos del cliente |
| Buscar reservas | Encuentra reservas por telefono |
| Modificar reserva | Cambia fecha/hora de reserva existente |
| Cancelar reserva | Cancela una reserva activa |
| Agregar notas | Guarda restricciones, alergias, peticiones |
| Terminar llamada | Finaliza llamadas (agresividad, transferencia) |

## Negocios Soportados

| Negocio | Recursos | Duracion | Ejemplo |
|---------|----------|----------|---------|
| Restaurante | Mesas | 2 horas | Bella Italia |
| Clinica dental | Consultorios | 1 hora | Clinica Dental Sonrisa |
| Peluqueria | Sillas/Estilistas | 30-90 min | - |
| Spa | Cabinas/Salas | 1-2 horas | - |
| Veterinaria | Consultorios | 30 min | - |
| Cancha deportiva | Canchas | 1-2 horas | - |

## Requisitos

- Python 3.10+
- Cuenta de [ElevenLabs](https://elevenlabs.io) con Conversational AI
- Google Cloud Project con Sheets API
- Service Account con acceso al Spreadsheet
- ngrok (desarrollo local)

## Instalacion Rapida

```bash
# Clonar e instalar
git clone https://github.com/tu-usuario/voice-service.git
cd voice-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env con tus credenciales
```

## Configuracion

### 1. Variables de entorno (.env)

```bash
# ElevenLabs
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_AGENT_ID=agent_xxx
ELEVENLABS_VOICE_ID=voice_id_xxx  # Opcional: voz personalizada

# Webhook (ngrok para dev)
WEBHOOK_BASE_URL=https://your-url.ngrok-free.app

# Google
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

### 2. Configuracion del negocio (config/business.yaml)

```yaml
business_name: "Mi Negocio"
business_type: "restaurante"

reservation:
  duration_hours: 2.0
  max_party_size: 20

tables:
  - id: "1"
    name: "Mesa 1"
    capacity: 4
    location: "interior"

messages:
  reservation_confirmed: "Reserva confirmada para {party_size} personas..."
```

### 3. Personalidad del agente (config/agent_prompt.txt)

```
Eres [Nombre], la asistente virtual de [Negocio].

## REGLA DE ORO: UNA PREGUNTA A LA VEZ
NUNCA hagas dos preguntas en el mismo turno.

## IDIOMA
Habla siempre en espanol.
...
```

### 4. Ejecutar scripts de configuracion

```bash
# Crear estructura en Google Sheets
python setup_sheets.py

# Configurar agente en ElevenLabs (prompt + tools)
python configure_elevenlabs.py
```

### 5. Iniciar servicio

```bash
# Terminal 1: ngrok
ngrok http 8000

# Terminal 2: servicio
uvicorn app.main:app --reload --port 8000

# Probar
open index.html
```

## Habilitar Modo Texto

Por defecto el widget es solo voz. Para habilitar texto:

1. Ir a https://elevenlabs.io/app
2. Seleccionar tu agente
3. **Widget** > **Interface** > **"Voice + text"**
4. Guardar

## Estructura del Proyecto

```
voice-service/
├── config/                     # CONFIGURACION (editar)
│   ├── business.yaml           #   Negocio, recursos, mensajes
│   ├── agent_prompt.txt        #   Personalidad del agente
│   └── config_loader.py        #   Carga la configuracion
├── app/                        # CODIGO (no tocar)
│   ├── main.py                 #   FastAPI entry point
│   ├── api/tables.py           #   API endpoints (webhooks)
│   └── services/               #   Google Sheets integration
├── configure_elevenlabs.py     # Script: configura agente
├── setup_sheets.py             # Script: crea estructura Sheets
├── index.html                  # Frontend con widget
└── CLAUDE.md                   # Documentacion tecnica
```

## API Endpoints

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/health/live` | Health check |
| GET | `/widget-api/tables/v1/tables` | Listar recursos |
| POST | `/widget-api/tables/v1/availability` | Verificar disponibilidad |
| POST | `/widget-api/tables/v1/reserve` | Crear reserva |
| POST | `/widget-api/tables/v1/search` | Buscar por telefono |
| POST | `/widget-api/tables/v1/cancel` | Cancelar reserva |
| POST | `/widget-api/tables/v1/modify` | Modificar fecha/hora |
| POST | `/widget-api/tables/v1/update-notes` | Agregar notas |

## ElevenLabs Tools

**Webhook Tools** (configurables):
- `check_table_availability` - Verificar disponibilidad
- `create_reservation` - Crear reserva
- `search_reservations` - Buscar por telefono
- `cancel_reservation` - Cancelar reserva
- `modify_reservation` - Modificar reserva
- `update_notes` - Agregar notas

**System Tools** (ElevenLabs):
- `end_call` - Terminar llamada
- `language_detection` - Detectar idioma

## Adaptar a Nuevo Negocio

```bash
1. Editar config/business.yaml    # nombre, recursos, duracion
2. Editar config/agent_prompt.txt # personalidad del agente
3. Editar .env                    # API keys, IDs
4. Crear Google Sheet + compartir con service account
5. python setup_sheets.py
6. python configure_elevenlabs.py
7. uvicorn app.main:app
```

**No se modifica ningun archivo Python.**

## Deploy (Cloud Run)

```bash
gcloud run deploy voice-service \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --env-vars-file=cloudrun-env.yaml
```

## Changelog

### v2.1.0 (2026-02-05)
- Flujo conversacional natural (una pregunta a la vez)
- Escalamiento de agresividad con end_call
- Transferencia a humano (temporal: end_call)
- Idioma consistente (solo espanol por defecto)
- Voice ID configurable

### v2.0.0 (2026-02-05)
- Sistema multi-negocio (business.yaml + agent_prompt.txt)
- Mensajes configurables con placeholders
- Frontend con widget ElevenLabs

### v1.1.0 (2026-02-04)
- Telefono flexible (sin codigo de pais)
- update_notes tool
- Manejo de clientes molestos

## Documentacion

Ver [CLAUDE.md](CLAUDE.md) para documentacion tecnica completa.

## Licencia

MIT
