#!/usr/bin/env python3
"""Configure Google Sheet with tables and reservations structure."""
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_FILE = "sheets-credentials.json"
SPREADSHEET_ID = "1UZYHP7BsnCVOHxdhSj30b5v2TiR2XdDTGYrRhk-zxGE"

def main():
    with open(CREDENTIALS_FILE, "r") as f:
        creds_info = json.load(f)

    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    sheets = build("sheets", "v4", credentials=creds)

    # Rename first sheet to "Mesas" and create "Reservas" sheet
    requests = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "title": "Mesas"},
                "fields": "title"
            }
        },
        {
            "addSheet": {
                "properties": {"title": "Reservas"}
            }
        }
    ]

    try:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()
        print("Sheets created: Mesas, Reservas")
    except Exception as e:
        print(f"Note: {e}")

    # Add Mesas data
    mesas = [
        ["ID", "Nombre", "Capacidad", "Ubicacion", "Activa"],
        ["1", "Mesa 1", "2", "interior", "si"],
        ["2", "Mesa 2", "2", "interior", "si"],
        ["3", "Mesa 3", "4", "interior", "si"],
        ["4", "Mesa 4", "4", "interior", "si"],
        ["5", "Mesa 5", "6", "interior", "si"],
        ["6", "Mesa Terraza 1", "4", "terraza", "si"],
        ["7", "Mesa Terraza 2", "4", "terraza", "si"],
        ["8", "Mesa Terraza 3", "6", "terraza", "si"],
        ["9", "Mesa Privada", "8", "interior", "si"],
    ]

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Mesas!A1",
        valueInputOption="RAW",
        body={"values": mesas}
    ).execute()
    print("Added table data to 'Mesas'")

    # Add Reservas headers
    reservas = [["ID", "MesaID", "Fecha", "HoraInicio", "HoraFin", "NombreCliente", "Telefono", "NumPersonas", "Estado", "Notas", "CreadoEn"]]

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Reservas!A1",
        valueInputOption="RAW",
        body={"values": reservas}
    ).execute()
    print("Added headers to 'Reservas'")

    print(f"\nSUCCESS! Spreadsheet configured.")
    print(f"URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")

if __name__ == "__main__":
    main()
