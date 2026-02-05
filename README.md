# Bella Italia Voice Service

Servicio de voz para gestión de reservas de restaurante usando ElevenLabs Conversational AI y Google Sheets como backend.

## Arquitectura

```
Cliente (Voz) → ElevenLabs Agent → Webhooks → FastAPI → Google Sheets
```

## Funcionalidades

- ✅ Verificar disponibilidad de mesas
- ✅ Crear reservaciones
- ✅ Buscar reservas por teléfono
- ✅ Modificar fecha/hora de reservas
- ✅ Cancelar reservaciones
- ✅ Actualizar notas durante la llamada (restricciones, alergias, peticiones)

## Requisitos

- Python 3.11+
- Cuenta de ElevenLabs con Conversational AI
- Google Cloud Project con Sheets API habilitada
- Service Account con acceso al Spreadsheet

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/Jorge-Polanco-Roque/Servicio_Voz.git
cd Servicio_Voz

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

## Configuración

### Variables de entorno (.env)

```bash
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_AGENT_ID=your_agent_id
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_SHEETS_MESAS_SHEET=Mesas
GOOGLE_SHEETS_RESERVAS_SHEET=Reservas
```

### Configurar Google Sheets

```bash
python setup_sheets.py
```

### Configurar ElevenLabs

```bash
python configure_elevenlabs.py
```

## Desarrollo

```bash
# Iniciar servicio
uvicorn app.main:app --reload --port 8000

# Exponer con ngrok (en otra terminal)
ngrok http 8000

# Actualizar webhook URL en .env y reconfigurar ElevenLabs
python configure_elevenlabs.py
```

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /health/live | Health check |
| POST | /widget-api/tables/v1/availability | Verificar disponibilidad |
| POST | /widget-api/tables/v1/reserve | Crear reserva |
| POST | /widget-api/tables/v1/search | Buscar por teléfono |
| POST | /widget-api/tables/v1/cancel | Cancelar reserva |
| POST | /widget-api/tables/v1/modify | Modificar fecha/hora |
| POST | /widget-api/tables/v1/update-notes | Agregar notas |

## Deploy (Cloud Run)

```bash
gcloud run deploy voice-service \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated
```

## Documentación

Ver [CLAUDE.md](CLAUDE.md) para documentación técnica completa.

## Licencia

MIT
