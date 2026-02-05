#!/usr/bin/env python3
"""Configure Google Sheet with tables and reservations structure.
Reads table definitions from config/business.yaml and credentials from environment.
"""
import os
import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

from config.config_loader import config

CREDENTIALS_FILE = "sheets-credentials.json"
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
MESAS_SHEET = os.getenv("GOOGLE_SHEETS_MESAS_SHEET", "Mesas")
RESERVAS_SHEET = os.getenv("GOOGLE_SHEETS_RESERVAS_SHEET", "Reservas")


def main():
    if not SPREADSHEET_ID:
        print("Error: GOOGLE_SHEETS_SPREADSHEET_ID not set in .env")
        return

    with open(CREDENTIALS_FILE, "r") as f:
        creds_info = json.load(f)

    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    sheets = build("sheets", "v4", credentials=creds)

    # Rename first sheet and create reservations sheet
    requests = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "title": MESAS_SHEET},
                "fields": "title"
            }
        },
        {
            "addSheet": {
                "properties": {"title": RESERVAS_SHEET}
            }
        }
    ]

    try:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()
        print(f"Sheets created: {MESAS_SHEET}, {RESERVAS_SHEET}")
    except Exception as e:
        print(f"Note: {e}")

    # Build table data from config
    mesas = [["ID", "Nombre", "Capacidad", "Ubicacion", "Activa"]]
    for t in config.tables:
        mesas.append([t["id"], t["name"], str(t["capacity"]), t["location"], "si"])

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{MESAS_SHEET}!A1",
        valueInputOption="RAW",
        body={"values": mesas}
    ).execute()
    print(f"Added {len(mesas) - 1} tables to '{MESAS_SHEET}'")

    # Add reservations headers
    reservas = [["ID", "MesaID", "Fecha", "HoraInicio", "HoraFin", "NombreCliente", "Telefono", "NumPersonas", "Estado", "Notas", "CreadoEn"]]

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{RESERVAS_SHEET}!A1",
        valueInputOption="RAW",
        body={"values": reservas}
    ).execute()
    print(f"Added headers to '{RESERVAS_SHEET}'")

    print(f"\nSUCCESS! Spreadsheet configured for {config.business_name}.")
    print(f"URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == "__main__":
    main()
