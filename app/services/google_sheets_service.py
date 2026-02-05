"""
Google Sheets Service for Table Reservations
Handles all interactions with Google Sheets API for managing tables and reservations.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.config_loader import config

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Singleton service for Google Sheets operations."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if GoogleSheetsService._initialized:
            return

        self.service = None
        self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        self.mesas_sheet = os.getenv("GOOGLE_SHEETS_MESAS_SHEET", "Mesas")
        self.reservas_sheet = os.getenv("GOOGLE_SHEETS_RESERVAS_SHEET", "Reservas")
        self._configured = False

        self._initialize_service()
        GoogleSheetsService._initialized = True

    def _initialize_service(self):
        """Initialize Google Sheets API service."""
        try:
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

            if not service_account_json or not self.spreadsheet_id:
                logger.warning("Google Sheets not configured. Using mock data mode.")
                return

            credentials_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )

            self.service = build("sheets", "v4", credentials=credentials)
            self._configured = True
            logger.info("Google Sheets service initialized successfully")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid service account JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")

    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return self._configured and self.service is not None

    def _get_sheet_data(self, sheet_name: str, range_suffix: str = "") -> List[List[str]]:
        """Get data from a sheet."""
        if not self.is_configured:
            return []

        try:
            range_name = f"{sheet_name}!{range_suffix}" if range_suffix else sheet_name
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            return result.get("values", [])
        except HttpError as e:
            logger.error(f"Error reading from sheet {sheet_name}: {e}")
            return []

    def _append_row(self, sheet_name: str, values: List[Any]) -> bool:
        """Append a row to a sheet."""
        if not self.is_configured:
            return False

        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [values]}
            ).execute()
            return True
        except HttpError as e:
            logger.error(f"Error appending to sheet {sheet_name}: {e}")
            return False

    def _update_cell(self, sheet_name: str, row: int, col: int, value: Any) -> bool:
        """Update a specific cell."""
        if not self.is_configured:
            return False

        try:
            col_letter = chr(ord('A') + col - 1)
            range_name = f"{sheet_name}!{col_letter}{row}"
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": [[value]]}
            ).execute()
            return True
        except HttpError as e:
            logger.error(f"Error updating cell: {e}")
            return False

    def get_all_tables(self) -> List[Dict[str, Any]]:
        """Get all active tables."""
        if not self.is_configured:
            return self._get_mock_tables()

        data = self._get_sheet_data(self.mesas_sheet)
        if len(data) < 2:  # No data or only header
            return []

        headers = data[0]
        tables = []

        for row in data[1:]:
            if len(row) >= 5:
                table = {
                    "id": row[0],
                    "nombre": row[1],
                    "capacidad": int(row[2]) if row[2].isdigit() else 0,
                    "ubicacion": row[3],
                    "activa": row[4].lower() == "si"
                }
                if table["activa"]:
                    tables.append(table)

        return tables

    def get_reservations_for_date(self, date: str) -> List[Dict[str, Any]]:
        """Get all reservations for a specific date."""
        if not self.is_configured:
            return self._get_mock_reservations(date)

        data = self._get_sheet_data(self.reservas_sheet)
        if len(data) < 2:
            return []

        reservations = []
        for idx, row in enumerate(data[1:], start=2):
            if len(row) >= 9 and row[2] == date and row[8].lower() == "confirmada":
                reservations.append({
                    "id": row[0],
                    "mesa_id": row[1],
                    "fecha": row[2],
                    "hora_inicio": row[3],
                    "hora_fin": row[4],
                    "nombre_cliente": row[5],
                    "telefono": row[6],
                    "num_personas": int(row[7]) if row[7].isdigit() else 0,
                    "estado": row[8],
                    "notas": row[9] if len(row) > 9 else "",
                    "row_number": idx
                })

        return reservations

    def check_table_availability(
        self,
        date: str,
        time: str,
        party_size: int,
        duration_hours: float = None
    ) -> Dict[str, Any]:
        """
        Check available tables for given date, time, and party size.
        Returns available tables sorted by capacity (smallest first).
        """
        if duration_hours is None:
            duration_hours = config.duration_hours
        tables = self.get_all_tables()
        reservations = self.get_reservations_for_date(date)

        # Filter tables by capacity
        suitable_tables = [t for t in tables if t["capacidad"] >= party_size]

        if not suitable_tables:
            return {
                "available": False,
                "message": config.msg("no_tables_capacity", party_size=party_size),
                "tables": []
            }

        # Calculate requested time slot
        request_start = self._time_to_minutes(time)
        request_end = request_start + int(duration_hours * 60)

        # Find tables with overlapping reservations
        occupied_table_ids = set()
        for res in reservations:
            res_start = self._time_to_minutes(res["hora_inicio"])
            res_end = self._time_to_minutes(res["hora_fin"])

            # Check for overlap
            if not (request_end <= res_start or request_start >= res_end):
                occupied_table_ids.add(res["mesa_id"])

        # Filter available tables
        available_tables = [
            t for t in suitable_tables
            if t["id"] not in occupied_table_ids
        ]

        # Sort by capacity (prefer smaller tables)
        available_tables.sort(key=lambda t: t["capacidad"])

        if not available_tables:
            return {
                "available": False,
                "message": config.msg("no_availability", party_size=party_size, date=date, time=time),
                "tables": []
            }

        return {
            "available": True,
            "message": config.msg("tables_available", count=len(available_tables)),
            "tables": available_tables,
            "recommended_table": available_tables[0]
        }

    def create_reservation(
        self,
        date: str,
        time: str,
        party_size: int,
        customer_name: str,
        customer_phone: str,
        special_requests: str = "",
        duration_hours: float = None
    ) -> Dict[str, Any]:
        """
        Create a new reservation.
        Automatically assigns the best available table.
        """
        if duration_hours is None:
            duration_hours = config.duration_hours
        # Check availability
        availability = self.check_table_availability(date, time, party_size, duration_hours)

        if not availability["available"]:
            return {
                "success": False,
                "message": availability["message"]
            }

        # Get the recommended table
        table = availability["recommended_table"]

        # Generate reservation ID
        reservation_id = f"RES-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Calculate end time
        end_time = self._add_hours_to_time(time, duration_hours)

        # Create reservation data
        created_at = datetime.now().isoformat()

        if self.is_configured:
            # Append to Google Sheets
            row_data = [
                reservation_id,
                table["id"],
                date,
                time,
                end_time,
                customer_name,
                customer_phone,
                str(party_size),
                "confirmada",
                special_requests,
                created_at
            ]

            success = self._append_row(self.reservas_sheet, row_data)

            if not success:
                return {
                    "success": False,
                    "message": config.msg("sheets_save_error")
                }

        return {
            "success": True,
            "message": config.msg("reservation_confirmed", party_size=party_size, date=date, time=time),
            "reservation": {
                "id": reservation_id,
                "table": table,
                "date": date,
                "time": time,
                "end_time": end_time,
                "party_size": party_size,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "special_requests": special_requests,
                "status": "confirmada"
            }
        }

    def search_by_phone(self, phone: str) -> Dict[str, Any]:
        """Search reservations by phone number."""
        if not self.is_configured:
            return self._mock_search_by_phone(phone)

        data = self._get_sheet_data(self.reservas_sheet)
        if len(data) < 2:
            return {
                "found": False,
                "message": config.msg("no_reservations_found"),
                "reservations": []
            }

        # Normalize phone for comparison
        normalized_phone = self._normalize_phone(phone)

        reservations = []
        for idx, row in enumerate(data[1:], start=2):
            if len(row) >= 9:
                row_phone = self._normalize_phone(row[6])
                if row_phone == normalized_phone and row[8].lower() != "cancelada":
                    reservations.append({
                        "id": row[0],
                        "mesa_id": row[1],
                        "fecha": row[2],
                        "hora_inicio": row[3],
                        "hora_fin": row[4],
                        "nombre_cliente": row[5],
                        "telefono": row[6],
                        "num_personas": int(row[7]) if row[7].isdigit() else 0,
                        "estado": row[8],
                        "notas": row[9] if len(row) > 9 else "",
                        "row_number": idx
                    })

        if not reservations:
            return {
                "found": False,
                "message": config.msg("no_reservations_phone", phone=phone),
                "reservations": []
            }

        # Sort by date (most recent first)
        reservations.sort(key=lambda r: (r["fecha"], r["hora_inicio"]), reverse=True)

        return {
            "found": True,
            "message": config.msg("reservations_found", count=len(reservations)),
            "reservations": reservations
        }

    def cancel_reservation(self, reservation_id: str, phone: str) -> Dict[str, Any]:
        """Cancel a reservation by ID and phone verification."""
        if not self.is_configured:
            return self._mock_cancel_reservation(reservation_id, phone)

        data = self._get_sheet_data(self.reservas_sheet)
        if len(data) < 2:
            return {
                "success": False,
                "message": config.msg("reservation_not_found", reservation_id=reservation_id)
            }

        normalized_phone = self._normalize_phone(phone)

        for idx, row in enumerate(data[1:], start=2):
            if len(row) >= 9 and row[0] == reservation_id:
                row_phone = self._normalize_phone(row[6])

                if row_phone != normalized_phone:
                    return {
                        "success": False,
                        "message": config.msg("phone_mismatch")
                    }

                if row[8].lower() == "cancelada":
                    return {
                        "success": False,
                        "message": config.msg("already_cancelled")
                    }

                # Update status to cancelled (column 9 = I)
                success = self._update_cell(self.reservas_sheet, idx, 9, "cancelada")

                if success:
                    return {
                        "success": True,
                        "message": config.msg("reservation_cancelled", reservation_id=reservation_id),
                        "reservation": {
                            "id": row[0],
                            "fecha": row[2],
                            "hora": row[3],
                            "nombre_cliente": row[5]
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": config.msg("sheets_update_error")
                    }

        return {
            "success": False,
            "message": config.msg("reservation_not_found", reservation_id=reservation_id)
        }

    def modify_reservation(
        self,
        reservation_id: str,
        phone: str,
        new_date: Optional[str] = None,
        new_time: Optional[str] = None,
        duration_hours: float = None
    ) -> Dict[str, Any]:
        """
        Modify an existing reservation's date and/or time.
        Verifies availability before making changes.
        """
        if duration_hours is None:
            duration_hours = config.duration_hours
        if not self.is_configured:
            return self._mock_modify_reservation(reservation_id, phone, new_date, new_time)

        data = self._get_sheet_data(self.reservas_sheet)
        if len(data) < 2:
            return {
                "success": False,
                "message": config.msg("reservation_not_found", reservation_id=reservation_id)
            }

        normalized_phone = self._normalize_phone(phone)

        for idx, row in enumerate(data[1:], start=2):
            if len(row) >= 9 and row[0] == reservation_id:
                row_phone = self._normalize_phone(row[6])

                if row_phone != normalized_phone:
                    return {
                        "success": False,
                        "message": config.msg("phone_mismatch")
                    }

                if row[8].lower() == "cancelada":
                    return {
                        "success": False,
                        "message": config.msg("cannot_modify_cancelled")
                    }

                # Get current values
                current_date = row[2]
                current_time = row[3]
                party_size = int(row[7]) if row[7].isdigit() else 2
                mesa_id = row[1]

                # Determine new values
                target_date = new_date if new_date else current_date
                target_time = new_time if new_time else current_time

                # If nothing changed
                if target_date == current_date and target_time == current_time:
                    return {
                        "success": False,
                        "message": config.msg("no_changes")
                    }

                # Check availability for new slot (excluding current reservation)
                availability = self._check_availability_excluding_reservation(
                    target_date, target_time, party_size, reservation_id, duration_hours
                )

                if not availability["available"]:
                    return {
                        "success": False,
                        "message": config.msg("no_availability_modify", date=target_date, time=target_time, detail=availability['message'])
                    }

                # Calculate new end time
                new_end_time = self._add_hours_to_time(target_time, duration_hours)

                # Update the reservation (columns: C=date, D=time, E=end_time)
                success = True
                if new_date:
                    success = success and self._update_cell(self.reservas_sheet, idx, 3, target_date)
                if new_time:
                    success = success and self._update_cell(self.reservas_sheet, idx, 4, target_time)
                    success = success and self._update_cell(self.reservas_sheet, idx, 5, new_end_time)

                if success:
                    return {
                        "success": True,
                        "message": config.msg("reservation_modified", date=target_date, time=target_time),
                        "reservation": {
                            "id": reservation_id,
                            "fecha_anterior": current_date,
                            "hora_anterior": current_time,
                            "fecha_nueva": target_date,
                            "hora_nueva": target_time,
                            "hora_fin": new_end_time,
                            "nombre_cliente": row[5]
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": config.msg("sheets_modify_error")
                    }

        return {
            "success": False,
            "message": config.msg("reservation_not_found", reservation_id=reservation_id)
        }

    def update_notes(
        self,
        reservation_id: str,
        phone: str,
        notes: str
    ) -> Dict[str, Any]:
        """
        Add or update notes for an existing reservation.
        Notes are APPENDED to existing notes.
        """
        if not self.is_configured:
            return self._mock_update_notes(reservation_id, phone, notes)

        data = self._get_sheet_data(self.reservas_sheet)
        if len(data) < 2:
            return {
                "success": False,
                "message": config.msg("reservation_not_found", reservation_id=reservation_id)
            }

        normalized_phone = self._normalize_phone(phone)

        for idx, row in enumerate(data[1:], start=2):
            if len(row) >= 9 and row[0] == reservation_id:
                row_phone = self._normalize_phone(row[6])

                if row_phone != normalized_phone:
                    return {
                        "success": False,
                        "message": config.msg("phone_mismatch")
                    }

                if row[8].lower() == "cancelada":
                    return {
                        "success": False,
                        "message": config.msg("cannot_add_notes_cancelled")
                    }

                # Get current notes and append new ones
                current_notes = row[9] if len(row) > 9 else ""
                if current_notes:
                    updated_notes = f"{current_notes}. {notes}"
                else:
                    updated_notes = notes

                # Update notes (column 10 = J)
                success = self._update_cell(self.reservas_sheet, idx, 10, updated_notes)

                if success:
                    return {
                        "success": True,
                        "message": config.msg("notes_updated"),
                        "reservation": {
                            "id": row[0],
                            "fecha": row[2],
                            "hora": row[3],
                            "nombre_cliente": row[5],
                            "notas": updated_notes
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": config.msg("sheets_notes_error")
                    }

        return {
            "success": False,
            "message": config.msg("reservation_not_found", reservation_id=reservation_id)
        }

    def _mock_update_notes(self, reservation_id: str, phone: str, notes: str) -> Dict[str, Any]:
        """Mock update notes for testing."""
        if reservation_id == "RES-MOCK001":
            return {
                "success": True,
                "message": "Notas actualizadas (modo demo)",
                "reservation": {
                    "id": reservation_id,
                    "notas": notes
                }
            }
        return {
            "success": False,
            "message": f"Reserva {reservation_id} no encontrada (modo demo)"
        }

    def _check_availability_excluding_reservation(
        self,
        date: str,
        time: str,
        party_size: int,
        exclude_reservation_id: str,
        duration_hours: float = None
    ) -> Dict[str, Any]:
        """Check availability excluding a specific reservation (for modifications)."""
        if duration_hours is None:
            duration_hours = config.duration_hours
        tables = self.get_all_tables()

        # Get all reservations for the date
        data = self._get_sheet_data(self.reservas_sheet)
        reservations = []

        if len(data) >= 2:
            for idx, row in enumerate(data[1:], start=2):
                if len(row) >= 9 and row[2] == date and row[8].lower() == "confirmada":
                    # Exclude the reservation being modified
                    if row[0] != exclude_reservation_id:
                        reservations.append({
                            "id": row[0],
                            "mesa_id": row[1],
                            "hora_inicio": row[3],
                            "hora_fin": row[4],
                        })

        # Filter tables by capacity
        suitable_tables = [t for t in tables if t["capacidad"] >= party_size]

        if not suitable_tables:
            return {
                "available": False,
                "message": config.msg("no_tables_capacity", party_size=party_size)
            }

        # Calculate requested time slot
        request_start = self._time_to_minutes(time)
        request_end = request_start + int(duration_hours * 60)

        # Find occupied tables
        occupied_table_ids = set()
        for res in reservations:
            res_start = self._time_to_minutes(res["hora_inicio"])
            res_end = self._time_to_minutes(res["hora_fin"])

            if not (request_end <= res_start or request_start >= res_end):
                occupied_table_ids.add(res["mesa_id"])

        # Filter available tables
        available_tables = [t for t in suitable_tables if t["id"] not in occupied_table_ids]

        if not available_tables:
            return {
                "available": False,
                "message": config.msg("all_tables_occupied")
            }

        return {
            "available": True,
            "message": config.msg("tables_available", count=len(available_tables))
        }

    def _mock_modify_reservation(
        self,
        reservation_id: str,
        phone: str,
        new_date: Optional[str],
        new_time: Optional[str]
    ) -> Dict[str, Any]:
        """Mock modify for testing."""
        if reservation_id == "RES-MOCK001":
            return {
                "success": True,
                "message": f"Reserva modificada (modo demo)",
                "reservation": {
                    "id": reservation_id,
                    "fecha_anterior": datetime.now().strftime("%Y-%m-%d"),
                    "hora_anterior": "13:00",
                    "fecha_nueva": new_date or datetime.now().strftime("%Y-%m-%d"),
                    "hora_nueva": new_time or "13:00",
                    "nombre_cliente": "Cliente Demo"
                }
            }
        return {
            "success": False,
            "message": f"Reserva {reservation_id} no encontrada (modo demo)"
        }

    # Helper methods
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        try:
            parts = time_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0

    def _add_hours_to_time(self, time_str: str, hours: float) -> str:
        """Add hours to a time string."""
        minutes = self._time_to_minutes(time_str)
        minutes += int(hours * 60)
        hours_result = (minutes // 60) % 24
        mins_result = minutes % 60
        return f"{hours_result:02d}:{mins_result:02d}"

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison."""
        return "".join(c for c in phone if c.isdigit())

    # Mock data methods (used when Sheets is not configured)
    def _get_mock_tables(self) -> List[Dict[str, Any]]:
        """Return mock table data from config for testing."""
        return config.get_mock_tables()

    def _get_mock_reservations(self, date: str) -> List[Dict[str, Any]]:
        """Return mock reservations for testing."""
        # Return some mock reservations for the requested date
        return [
            {
                "id": "RES-MOCK001",
                "mesa_id": "2",
                "fecha": date,
                "hora_inicio": "13:00",
                "hora_fin": "15:00",
                "nombre_cliente": "Cliente Demo",
                "telefono": "+34600000000",
                "num_personas": 3,
                "estado": "confirmada",
                "notas": "",
                "row_number": 2
            }
        ]

    def _mock_search_by_phone(self, phone: str) -> Dict[str, Any]:
        """Mock search for testing."""
        normalized = self._normalize_phone(phone)
        if normalized.endswith("000000"):
            return {
                "found": True,
                "message": "Se encontró 1 reserva (modo demo)",
                "reservations": [{
                    "id": "RES-MOCK001",
                    "mesa_id": "2",
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "hora_inicio": "13:00",
                    "hora_fin": "15:00",
                    "nombre_cliente": "Cliente Demo",
                    "telefono": phone,
                    "num_personas": 3,
                    "estado": "confirmada",
                    "notas": "",
                    "row_number": 2
                }]
            }
        return {
            "found": False,
            "message": f"No se encontraron reservas para {phone} (modo demo)",
            "reservations": []
        }

    def _mock_cancel_reservation(self, reservation_id: str, phone: str) -> Dict[str, Any]:
        """Mock cancel for testing."""
        if reservation_id == "RES-MOCK001":
            return {
                "success": True,
                "message": f"Reserva {reservation_id} cancelada (modo demo)",
                "reservation": {
                    "id": reservation_id,
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "hora": "13:00",
                    "nombre_cliente": "Cliente Demo"
                }
            }
        return {
            "success": False,
            "message": f"Reserva {reservation_id} no encontrada (modo demo)"
        }


# Singleton instance
sheets_service = GoogleSheetsService()
