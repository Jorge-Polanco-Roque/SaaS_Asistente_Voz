"""
Tables API Router - Server Tools for ElevenLabs Agent
Endpoints for managing table reservations via Google Sheets.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..services.google_sheets_service import sheets_service

router = APIRouter(prefix="/widget-api/tables/v1", tags=["tables"])


# Request Models
class AvailabilityRequest(BaseModel):
    """Request model for checking table availability."""
    date: str = Field(..., description="Date in YYYY-MM-DD format", examples=["2026-02-10"])
    time: str = Field(..., description="Time in HH:MM format", examples=["14:00"])
    party_size: int = Field(..., ge=1, le=20, description="Number of people")
    duration_hours: Optional[float] = Field(2.0, ge=0.5, le=6.0, description="Duration in hours")


class ReserveRequest(BaseModel):
    """Request model for creating a reservation."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in HH:MM format")
    party_size: int = Field(..., ge=1, le=20, description="Number of people")
    customer_name: str = Field(..., min_length=2, max_length=100, description="Customer name")
    customer_phone: str = Field(..., min_length=7, max_length=20, description="Customer phone")
    special_requests: Optional[str] = Field("", max_length=500, description="Special requests or notes")
    duration_hours: Optional[float] = Field(2.0, ge=0.5, le=6.0, description="Duration in hours")


class SearchRequest(BaseModel):
    """Request model for searching reservations."""
    phone: str = Field(..., min_length=7, max_length=20, description="Phone number to search")


class CancelRequest(BaseModel):
    """Request model for cancelling a reservation."""
    reservation_id: str = Field(..., description="Reservation ID (e.g., RES-xxx)")
    phone: str = Field(..., min_length=7, max_length=20, description="Phone for verification")


class ModifyRequest(BaseModel):
    """Request model for modifying a reservation's date/time."""
    reservation_id: str = Field(..., description="Reservation ID (e.g., RES-xxx)")
    phone: str = Field(..., min_length=7, max_length=20, description="Phone for verification")
    new_date: Optional[str] = Field(None, description="New date in YYYY-MM-DD format (optional)")
    new_time: Optional[str] = Field(None, description="New time in HH:MM format (optional)")


class UpdateNotesRequest(BaseModel):
    """Request model for updating reservation notes."""
    reservation_id: str = Field(..., description="Reservation ID (e.g., RES-xxx)")
    phone: str = Field(..., min_length=7, max_length=20, description="Phone for verification")
    notes: str = Field(..., max_length=500, description="New notes to ADD to the reservation")


# Response Models
class TableInfo(BaseModel):
    """Table information."""
    id: str
    nombre: str
    capacidad: int
    ubicacion: str


class AvailabilityResponse(BaseModel):
    """Response for availability check."""
    available: bool
    message: str
    tables: List[TableInfo] = []
    recommended_table: Optional[TableInfo] = None


class ReservationInfo(BaseModel):
    """Reservation details."""
    id: str
    table: Optional[TableInfo] = None
    date: str
    time: str
    end_time: Optional[str] = None
    party_size: int
    customer_name: str
    customer_phone: str
    special_requests: Optional[str] = ""
    status: str


class ReserveResponse(BaseModel):
    """Response for reservation creation."""
    success: bool
    message: str
    reservation: Optional[ReservationInfo] = None


class SearchResponse(BaseModel):
    """Response for reservation search."""
    found: bool
    message: str
    reservations: List[Dict[str, Any]] = []


class CancelResponse(BaseModel):
    """Response for reservation cancellation."""
    success: bool
    message: str
    reservation: Optional[Dict[str, Any]] = None


class ModifyResponse(BaseModel):
    """Response for reservation modification."""
    success: bool
    message: str
    reservation: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    configured: bool
    spreadsheet_id: Optional[str] = None
    sheets: Dict[str, str] = {}


# Endpoints

@router.get("/", response_model=Dict[str, Any])
async def root():
    """
    Get information about available table reservation tools.
    This endpoint provides documentation for ElevenLabs Server Tools configuration.
    """
    return {
        "service": "Table Reservation API",
        "version": "1.0.0",
        "description": "Sistema de reservas de mesas para restaurante usando Google Sheets",
        "tools": {
            "check_table_availability": {
                "endpoint": "POST /widget-api/tables/v1/availability",
                "description": "Verificar disponibilidad de mesas para una fecha, hora y número de personas",
                "parameters": {
                    "date": "Fecha en formato YYYY-MM-DD",
                    "time": "Hora en formato HH:MM",
                    "party_size": "Número de personas (1-20)"
                }
            },
            "create_reservation": {
                "endpoint": "POST /widget-api/tables/v1/reserve",
                "description": "Crear una nueva reserva. Asigna automáticamente la mejor mesa disponible",
                "parameters": {
                    "date": "Fecha en formato YYYY-MM-DD",
                    "time": "Hora en formato HH:MM",
                    "party_size": "Número de personas",
                    "customer_name": "Nombre del cliente",
                    "customer_phone": "Teléfono del cliente",
                    "special_requests": "(opcional) Peticiones especiales"
                }
            },
            "search_reservations": {
                "endpoint": "POST /widget-api/tables/v1/search",
                "description": "Buscar reservas por número de teléfono",
                "parameters": {
                    "phone": "Número de teléfono del cliente"
                }
            },
            "cancel_reservation": {
                "endpoint": "POST /widget-api/tables/v1/cancel",
                "description": "Cancelar una reserva existente",
                "parameters": {
                    "reservation_id": "ID de la reserva (ej: RES-xxx)",
                    "phone": "Teléfono para verificación"
                }
            },
            "modify_reservation": {
                "endpoint": "POST /widget-api/tables/v1/modify",
                "description": "Cambiar fecha y/o hora de una reserva existente",
                "parameters": {
                    "reservation_id": "ID de la reserva (ej: RES-xxx)",
                    "phone": "Teléfono para verificación",
                    "new_date": "(opcional) Nueva fecha en formato YYYY-MM-DD",
                    "new_time": "(opcional) Nueva hora en formato HH:MM"
                }
            }
        }
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health and configuration status of the Google Sheets connection.
    Returns whether the service is properly configured and connected.
    """
    return {
        "status": "healthy" if sheets_service.is_configured else "degraded",
        "configured": sheets_service.is_configured,
        "spreadsheet_id": sheets_service.spreadsheet_id[:10] + "..." if sheets_service.spreadsheet_id else None,
        "sheets": {
            "mesas": sheets_service.mesas_sheet,
            "reservas": sheets_service.reservas_sheet
        }
    }


@router.post("/availability", response_model=AvailabilityResponse)
async def check_availability(request: AvailabilityRequest):
    """
    Check table availability for a given date, time, and party size.

    This is the primary tool for ElevenLabs agent to check if tables are available
    before proceeding with a reservation.

    Returns:
    - available: Whether any tables are available
    - tables: List of available tables
    - recommended_table: The best table to assign (smallest that fits)
    """
    try:
        result = sheets_service.check_table_availability(
            date=request.date,
            time=request.time,
            party_size=request.party_size,
            duration_hours=request.duration_hours
        )

        # Transform tables for response
        tables = [
            TableInfo(
                id=t["id"],
                nombre=t["nombre"],
                capacidad=t["capacidad"],
                ubicacion=t["ubicacion"]
            )
            for t in result.get("tables", [])
        ]

        recommended = None
        if result.get("recommended_table"):
            t = result["recommended_table"]
            recommended = TableInfo(
                id=t["id"],
                nombre=t["nombre"],
                capacidad=t["capacidad"],
                ubicacion=t["ubicacion"]
            )

        return AvailabilityResponse(
            available=result["available"],
            message=result["message"],
            tables=tables,
            recommended_table=recommended
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking availability: {str(e)}")


@router.post("/reserve", response_model=ReserveResponse)
async def create_reservation(request: ReserveRequest):
    """
    Create a new table reservation.

    Automatically assigns the best available table based on party size.
    The smallest table that can accommodate the party will be selected.

    Returns:
    - success: Whether the reservation was created
    - message: Confirmation message or error description
    - reservation: Full reservation details including assigned table
    """
    try:
        result = sheets_service.create_reservation(
            date=request.date,
            time=request.time,
            party_size=request.party_size,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            special_requests=request.special_requests or "",
            duration_hours=request.duration_hours
        )

        reservation = None
        if result.get("reservation"):
            res = result["reservation"]
            table = None
            if res.get("table"):
                t = res["table"]
                table = TableInfo(
                    id=t["id"],
                    nombre=t["nombre"],
                    capacidad=t["capacidad"],
                    ubicacion=t["ubicacion"]
                )

            reservation = ReservationInfo(
                id=res["id"],
                table=table,
                date=res["date"],
                time=res["time"],
                end_time=res.get("end_time"),
                party_size=res["party_size"],
                customer_name=res["customer_name"],
                customer_phone=res["customer_phone"],
                special_requests=res.get("special_requests", ""),
                status=res["status"]
            )

        return ReserveResponse(
            success=result["success"],
            message=result["message"],
            reservation=reservation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating reservation: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_reservations(request: SearchRequest):
    """
    Search for reservations by phone number.

    Returns all active (non-cancelled) reservations associated with the phone number.
    Useful for customers wanting to view or manage their existing reservations.

    Returns:
    - found: Whether any reservations were found
    - reservations: List of matching reservations (sorted by date, most recent first)
    """
    try:
        result = sheets_service.search_by_phone(phone=request.phone)

        return SearchResponse(
            found=result["found"],
            message=result["message"],
            reservations=result.get("reservations", [])
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching reservations: {str(e)}")


@router.post("/cancel", response_model=CancelResponse)
async def cancel_reservation(request: CancelRequest):
    """
    Cancel an existing reservation.

    Requires both the reservation ID and the phone number for verification.
    The phone number must match the one used when creating the reservation.

    Returns:
    - success: Whether the cancellation was successful
    - message: Confirmation or error message
    - reservation: Details of the cancelled reservation
    """
    try:
        result = sheets_service.cancel_reservation(
            reservation_id=request.reservation_id,
            phone=request.phone
        )

        return CancelResponse(
            success=result["success"],
            message=result["message"],
            reservation=result.get("reservation")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling reservation: {str(e)}")


@router.post("/modify", response_model=ModifyResponse)
async def modify_reservation(request: ModifyRequest):
    """
    Modify an existing reservation's date and/or time.

    At least one of new_date or new_time must be provided.
    The system will verify availability before making changes.
    Each reservation has a duration of 2 hours.

    Requires phone verification to ensure only the customer can modify their reservation.

    Returns:
    - success: Whether the modification was successful
    - message: Confirmation or error message
    - reservation: Details showing previous and new date/time
    """
    if not request.new_date and not request.new_time:
        raise HTTPException(
            status_code=400,
            detail="Debe especificar new_date y/o new_time para modificar la reserva"
        )

    try:
        result = sheets_service.modify_reservation(
            reservation_id=request.reservation_id,
            phone=request.phone,
            new_date=request.new_date,
            new_time=request.new_time
        )

        return ModifyResponse(
            success=result["success"],
            message=result["message"],
            reservation=result.get("reservation")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error modifying reservation: {str(e)}")


@router.post("/update-notes", response_model=ModifyResponse)
async def update_notes(request: UpdateNotesRequest):
    """
    Add or update notes for an existing reservation.

    Use this to add dietary restrictions, special requests, or any other notes
    to a reservation DURING the conversation, before hanging up.

    Notes are APPENDED to existing notes, not replaced.

    Returns:
    - success: Whether the update was successful
    - message: Confirmation or error message
    - reservation: Updated reservation details
    """
    try:
        result = sheets_service.update_notes(
            reservation_id=request.reservation_id,
            phone=request.phone,
            notes=request.notes
        )

        return ModifyResponse(
            success=result["success"],
            message=result["message"],
            reservation=result.get("reservation")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating notes: {str(e)}")


# Additional utility endpoints

@router.get("/tables", response_model=List[TableInfo])
async def list_tables():
    """
    Get a list of all active tables in the restaurant.
    Useful for administrative purposes or debugging.
    """
    try:
        tables = sheets_service.get_all_tables()
        return [
            TableInfo(
                id=t["id"],
                nombre=t["nombre"],
                capacidad=t["capacidad"],
                ubicacion=t["ubicacion"]
            )
            for t in tables
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tables: {str(e)}")
