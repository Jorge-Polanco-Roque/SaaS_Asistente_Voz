# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Bella Italia Voice Service** - Servicio de voz para gestión de reservas de restaurante usando ElevenLabs Conversational AI y Google Sheets como backend.

**Current Version**: 1.1.0
**Status**: Funcionando en desarrollo local con ngrok

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User speaks   │────>│   ElevenLabs    │────>│  Voice Service  │
│   to agent      │     │     Agent       │     │   (FastAPI)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                               │                         │
                               │ Webhooks                │ Google Sheets API
                               │                         │
                               └─────────────────────────┼──────────────────┐
                                                         │                  │
                                                         v                  v
                                                   ┌──────────┐      ┌──────────┐
                                                   │  Mesas   │      │ Reservas │
                                                   │ (Sheet)  │      │ (Sheet)  │
                                                   └──────────┘      └──────────┘
```

## Common Commands

### Development

```bash
# Start service locally
cd /Users/A1064331/Desktop/pruebas/servicio_voz/voice-service
uvicorn app.main:app --reload --port 8000

# Start ngrok tunnel (in separate terminal)
ngrok http 8000

# Configure Google Sheets structure
python setup_sheets.py

# Configure ElevenLabs tools
python configure_elevenlabs.py

# List current ElevenLabs tools
python configure_elevenlabs.py list
```

### Testing API

```bash
# Health check
curl http://localhost:8000/health/live

# List tables
curl http://localhost:8000/widget-api/tables/v1/tables

# Check availability
curl -X POST http://localhost:8000/widget-api/tables/v1/availability \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-02-10","time":"14:00","party_size":4}'

# Create reservation
curl -X POST http://localhost:8000/widget-api/tables/v1/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-02-10",
    "time": "14:00",
    "party_size": 4,
    "customer_name": "Juan García",
    "customer_phone": "+34612345678",
    "special_requests": "Mesa junto a la ventana"
  }'

# Search reservations by phone
curl -X POST http://localhost:8000/widget-api/tables/v1/search \
  -H "Content-Type: application/json" \
  -d '{"phone":"+34612345678"}'

# Cancel reservation
curl -X POST http://localhost:8000/widget-api/tables/v1/cancel \
  -H "Content-Type: application/json" \
  -d '{"reservation_id":"RES-xxx","phone":"+34612345678"}'

# Modify reservation
curl -X POST http://localhost:8000/widget-api/tables/v1/modify \
  -H "Content-Type: application/json" \
  -d '{"reservation_id":"RES-xxx","phone":"+34612345678","new_date":"2026-02-11","new_time":"20:00"}'
```

### Deployment (Cloud Run)

```bash
# Build Docker image
docker build -t voice-service .

# Run locally with Docker
docker run -p 8080:8080 --env-file .env voice-service

# Deploy to Cloud Run
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
ELEVENLABS_AGENT_ID=agent_7901kgfexyhvejbsr5ayg5nwxzsm

# Webhook URL (ngrok for dev, Cloud Run URL for prod)
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app

# Google Service Account (JSON string or file path)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# Google Sheets
GOOGLE_SHEETS_SPREADSHEET_ID=1UZYHP7BsnCVOHxdhSj30b5v2TiR2XdDTGYrRhk-zxGE
GOOGLE_SHEETS_MESAS_SHEET=Mesas
GOOGLE_SHEETS_RESERVAS_SHEET=Reservas
```

### Google Sheets Structure

**Spreadsheet URL**: https://docs.google.com/spreadsheets/d/1UZYHP7BsnCVOHxdhSj30b5v2TiR2XdDTGYrRhk-zxGE

**Hoja "Mesas"**:
| ID | Nombre | Capacidad | Ubicacion | Activa |
|----|--------|-----------|-----------|--------|
| 1 | Mesa 1 | 2 | interior | si |
| 2 | Mesa 2 | 2 | interior | si |
| 3 | Mesa 3 | 4 | interior | si |
| 4 | Mesa 4 | 4 | interior | si |
| 5 | Mesa 5 | 6 | interior | si |
| 6 | Mesa Terraza 1 | 4 | terraza | si |
| 7 | Mesa Terraza 2 | 4 | terraza | si |
| 8 | Mesa Terraza 3 | 6 | terraza | si |
| 9 | Mesa Privada | 8 | interior | si |

**Hoja "Reservas"**:
| ID | MesaID | Fecha | HoraInicio | HoraFin | NombreCliente | Telefono | NumPersonas | Estado | Notas | CreadoEn |

### ElevenLabs Tools Configuration

**Agent ID**: `agent_7901kgfexyhvejbsr5ayg5nwxzsm`

| Tool | Description |
|------|-------------|
| check_table_availability | Verifica disponibilidad (SIEMPRE antes de reservar) |
| create_reservation | Crea reserva (NO menciona código al cliente) |
| search_reservations | Busca reservas por teléfono (solo números) |
| cancel_reservation | Cancela reserva (usa search primero) |
| modify_reservation | Modifica fecha/hora (usa search primero) |
| **update_notes** | **Agrega notas durante la llamada (restricciones, alergias, peticiones)** |

**Comportamiento del agente (Noema):**
- NO pedir código de país para teléfono (solo números)
- NO mencionar códigos de reservación al cliente
- Confirmar reservas con: fecha, hora, nombre y número de personas
- SIEMPRE preguntar por restricciones alimenticias/alergias antes de confirmar
- **Usar update_notes MÚLTIPLES VECES durante la llamada** para agregar cualquier información nueva
- Las notas se ACUMULAN (no se reemplazan)
- Si no sabe algo, decirlo honestamente
- Si preguntan algo no relacionado, redirigir amablemente a la reservación

**Manejo de clientes molestos/frustrados:**
- NUNCA quedarse en silencio - siempre responder algo
- Empatía primero: "Entiendo tu frustración, y quiero ayudarte"
- Ofrecer soluciones: "¿Qué puedo hacer para resolver esto?"
- Mantener calma ante agresividad
- Si insultan: "Entiendo que estás molesto. Estoy aquí para ayudarte cuando lo desees."

**Nota:** El filtro de seguridad de ElevenLabs puede bloquear respuestas ante lenguaje muy extremo (insultos fuertes, amenazas). Esto es controlado por ElevenLabs, no por el prompt.

## Key Files

```
voice-service/
├── app/
│   ├── main.py                      # FastAPI entry point
│   ├── api/
│   │   └── tables.py                # Tables API router (webhooks for ElevenLabs)
│   └── services/
│       └── google_sheets_service.py # Google Sheets integration
├── configure_elevenlabs.py          # Script to configure ElevenLabs tools
├── setup_sheets.py                  # Script to setup Google Sheets structure
├── elevenlabs_tools_config.json     # Tools configuration reference
├── Dockerfile                       # Docker config for Cloud Run
├── cloudrun-env.yaml               # Cloud Run env vars
├── requirements.txt                 # Python dependencies
├── .env                            # Local environment variables
└── sheets-credentials.json         # Google Service Account credentials
```

## API Endpoints

### Health
- `GET /health/live` - Liveness check
- `GET /health/ready` - Readiness check with dependencies

### Tables API (`/widget-api/tables/v1/`)
- `GET /` - API documentation
- `GET /health` - Google Sheets connection status
- `GET /tables` - List all tables
- `POST /availability` - Check table availability
- `POST /reserve` - Create reservation
- `POST /search` - Search reservations by phone
- `POST /cancel` - Cancel reservation
- `POST /modify` - Modify reservation date/time
- `POST /update-notes` - **Agregar notas a reserva existente (acumulativas)**

## Reservation Logic

1. **Check Availability** (SIEMPRE antes de reservar):
   - Encuentra mesas con capacidad >= party_size
   - Verifica conflictos de horario (cada reserva dura 2 horas)
   - Una mesa NO puede tener dos reservas que se solapen
   - Retorna mesas disponibles ordenadas por capacidad (menor primero)

2. **Create Reservation**:
   - Primero verifica disponibilidad automáticamente
   - Asigna la mesa más pequeña disponible
   - Genera ID interno (no se muestra al cliente)
   - Calcula hora de fin (inicio + 2 horas)
   - Escribe en Google Sheets

3. **Search/Cancel/Modify**:
   - Requiere verificación por teléfono (solo números, sin código país)
   - Solo afecta reservas no canceladas

**Importante**: El agente NO debe mencionar códigos de reservación al cliente. Solo confirmar con fecha, hora y nombre.

## Testing Flow

1. Start local service: `uvicorn app.main:app --port 5000`
2. Start ngrok: `ngrok http 8000`
3. Update `WEBHOOK_BASE_URL` in `.env` if URL changed
4. Run `python configure_elevenlabs.py` to update tools
5. Test with ElevenLabs agent or curl commands

## Current Status

- [x] Google Sheets structure configured
- [x] Tables API implemented (all 5 endpoints)
- [x] ElevenLabs tools configured
- [x] Mock data mode for offline testing
- [x] Dockerfile ready for Cloud Run
- [x] Table conflict detection working (no double-booking)
- [x] Phone validation relaxed (no country code required)
- [x] Agent configured to NOT mention reservation codes
- [ ] Production deployment

## Recent Changes (2026-02-04)

1. **Teléfono flexible**: Ya no requiere código de país, solo números (mínimo 7 dígitos)
2. **Sin código de reservación**: El agente no menciona IDs de reserva al cliente
3. **Verificación de conflictos**: Una mesa no puede tener dos reservas solapadas
4. **Restricciones alimenticias**: SIEMPRE pregunta antes de confirmar reserva
5. **Notas/peticiones especiales**: Se guardan en campo "special_requests"
6. **Límites claros**: Si no sabe algo, lo dice. Si preguntan algo fuera de tema, redirige a la reservación
7. **update_notes**: Nueva herramienta para agregar notas DURANTE la llamada (múltiples veces)
8. **Notas acumulativas**: Las notas se agregan a las existentes, no se reemplazan
9. **Manejo de clientes molestos**: Empatía, calma, nunca silencio - responder siempre

## Ideas para Futuras Funcionalidades

### Alta Prioridad (Valor inmediato)

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Consulta de menú** | Informar sobre platillos, precios, ingredientes y alérgenos | Media |
| **Horarios del restaurante** | Días/horas de operación, días festivos | Baja |
| **Confirmación por SMS/WhatsApp** | Enviar confirmación automática al crear reserva | Media |
| **Recordatorio de reserva** | Notificación 24h antes de la reserva | Media |
| **Lista de espera** | Si no hay disponibilidad, ofrecer anotarse en lista | Media |

### Media Prioridad (Mejora experiencia)

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Recomendaciones personalizadas** | Sugerir platillos según restricciones/preferencias | Alta |
| **Eventos especiales** | Informar sobre eventos, menús especiales, promociones | Baja |
| **Pedidos para llevar** | Tomar pedidos de comida para recoger | Alta |
| **Ubicación y direcciones** | Cómo llegar, estacionamiento, transporte | Baja |
| **Opiniones/feedback** | Recoger feedback después de la visita | Media |

### Baja Prioridad (Diferenciadores)

| Funcionalidad | Descripción | Complejidad |
|---------------|-------------|-------------|
| **Programa de lealtad** | Puntos, recompensas por visitas frecuentes | Alta |
| **Reserva de eventos privados** | Salones privados, eventos corporativos | Media |
| **Maridaje de vinos** | Sugerir vinos según platillos elegidos | Media |
| **Multiidioma** | Atender en inglés, italiano, etc. | Media |
| **Integración con delivery** | Conectar con UberEats, Rappi, etc. | Alta |

### Integraciones Sugeridas

| Servicio | Uso |
|----------|-----|
| **Twilio/WhatsApp Business** | Confirmaciones y recordatorios |
| **Google Maps API** | Direcciones e indicaciones |
| **Stripe/OpenPay** | Depósitos para reservas grandes |
| **Mailchimp/SendGrid** | Email marketing y confirmaciones |
| **Google Analytics** | Métricas de uso del asistente |
