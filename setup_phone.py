#!/usr/bin/env python3
"""
Setup Phone Number for Voice Service.
Connects Twilio phone numbers to ElevenLabs agents.

Usage:
    python setup_phone.py status          # Show current phone configuration
    python setup_phone.py list-owned      # List phone numbers in Twilio account
    python setup_phone.py list-available  # List numbers available to purchase
    python setup_phone.py import          # Import Twilio number to ElevenLabs
    python setup_phone.py remove          # Remove phone number from ElevenLabs

All configuration is read from environment variables (.env file).
"""
import os
import sys
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1/convai"


def check_config():
    """Verify all required configuration is present."""
    missing = []
    if not TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if not TWILIO_PHONE_NUMBER:
        missing.append("TWILIO_PHONE_NUMBER")
    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    if not ELEVENLABS_AGENT_ID:
        missing.append("ELEVENLABS_AGENT_ID")

    if missing:
        print("Error: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nAdd them to your .env file.")
        return False
    return True


def get_twilio_client():
    """Get Twilio client (lazy import)."""
    try:
        from twilio.rest import Client
        return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except ImportError:
        print("Error: twilio package not installed.")
        print("Run: pip install twilio")
        sys.exit(1)


def list_owned_numbers():
    """List phone numbers owned in Twilio account."""
    print("\n=== Twilio Phone Numbers ===\n")

    client = get_twilio_client()
    numbers = client.incoming_phone_numbers.list()

    if not numbers:
        print("No phone numbers found in your Twilio account.")
        print("\nTo buy a number:")
        print("  1. Go to https://console.twilio.com/")
        print("  2. Phone Numbers > Manage > Buy a number")
        print("  Or use: python setup_phone.py list-available")
        return

    print(f"Found {len(numbers)} number(s):\n")
    for num in numbers:
        status = "ACTIVE" if num.status == "in-use" else num.status.upper()
        print(f"  {num.phone_number}")
        print(f"    SID: {num.sid}")
        print(f"    Friendly Name: {num.friendly_name}")
        print(f"    Status: {status}")
        print(f"    Capabilities: Voice={num.capabilities.get('voice', False)}, SMS={num.capabilities.get('sms', False)}")
        print()


def list_available_numbers(country="US", area_code=None, limit=10):
    """List phone numbers available to purchase."""
    print(f"\n=== Available Phone Numbers ({country}) ===\n")

    client = get_twilio_client()

    try:
        kwargs = {"limit": limit}
        if area_code:
            kwargs["area_code"] = area_code

        numbers = client.available_phone_numbers(country).local.list(**kwargs)

        if not numbers:
            print(f"No numbers available for {country}" + (f" area code {area_code}" if area_code else ""))
            return

        print(f"Found {len(numbers)} available number(s):\n")
        for num in numbers:
            print(f"  {num.phone_number}")
            print(f"    Region: {num.region}")
            print(f"    Capabilities: Voice={num.capabilities.get('voice', False)}, SMS={num.capabilities.get('sms', False)}")
            print()

        print("To buy a number, use the Twilio console or API.")

    except Exception as e:
        print(f"Error listing available numbers: {e}")


def get_elevenlabs_phone_numbers():
    """Get phone numbers configured in ElevenLabs."""
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    response = requests.get(f"{ELEVENLABS_API_BASE}/phone-numbers", headers=headers)

    if response.status_code == 200:
        data = response.json()
        # API returns a list directly, normalize to dict format
        if isinstance(data, list):
            return {"phone_numbers": data}
        return data
    return None


def show_status():
    """Show current phone configuration status."""
    print("\n" + "=" * 60)
    print("Phone Configuration Status")
    print("=" * 60)

    # Twilio config
    print("\n[Twilio Configuration]")
    print(f"  Account SID: {TWILIO_ACCOUNT_SID[:10]}...{TWILIO_ACCOUNT_SID[-4:] if TWILIO_ACCOUNT_SID else 'NOT SET'}")
    print(f"  Auth Token:  {'*' * 20 if TWILIO_AUTH_TOKEN else 'NOT SET'}")
    print(f"  Phone Number: {TWILIO_PHONE_NUMBER or 'NOT SET'}")

    # ElevenLabs config
    print("\n[ElevenLabs Configuration]")
    print(f"  API Key: {ELEVENLABS_API_KEY[:10]}...{ELEVENLABS_API_KEY[-4:] if ELEVENLABS_API_KEY else 'NOT SET'}")
    print(f"  Agent ID: {ELEVENLABS_AGENT_ID or 'NOT SET'}")

    # Check ElevenLabs phone numbers
    print("\n[ElevenLabs Phone Numbers]")
    result = get_elevenlabs_phone_numbers()

    if result is None:
        print("  Error: Could not fetch phone numbers from ElevenLabs")
    elif not result.get("phone_numbers"):
        print("  No phone numbers connected to ElevenLabs")
        print(f"\n  To import {TWILIO_PHONE_NUMBER}:")
        print("    python setup_phone.py import")
    else:
        numbers = result.get("phone_numbers", [])
        print(f"  Found {len(numbers)} number(s):")
        for num in numbers:
            phone = num.get("phone_number", "Unknown")
            phone_id = num.get("phone_number_id", "")
            provider = num.get("provider", "unknown")
            label = num.get("label", "")

            # Agent can be in assigned_agent object or agent_id field
            assigned = num.get("assigned_agent", {})
            if assigned:
                agent_id = assigned.get("agent_id", "")
                agent_name = assigned.get("agent_name", "")
                agent_str = f"{agent_name} ({agent_id})" if agent_name else agent_id
            else:
                agent_str = num.get("agent_id", "No agent assigned")

            is_current = phone == TWILIO_PHONE_NUMBER
            marker = " <-- CURRENT" if is_current else ""

            print(f"\n    {phone}{marker}")
            print(f"      ID: {phone_id}")
            print(f"      Label: {label}")
            print(f"      Agent: {agent_str}")
            print(f"      Provider: {provider}")
            print(f"      Inbound: {num.get('supports_inbound', False)}, Outbound: {num.get('supports_outbound', False)}")

    print()


def import_phone_number():
    """Import Twilio phone number to ElevenLabs and associate with agent."""
    print("\n=== Importing Phone Number to ElevenLabs ===\n")

    if not check_config():
        return False

    print(f"Phone Number: {TWILIO_PHONE_NUMBER}")
    print(f"Agent ID: {ELEVENLABS_AGENT_ID}")
    print()

    # Check if already imported
    existing = get_elevenlabs_phone_numbers()
    if existing:
        for num in existing.get("phone_numbers", []):
            if num.get("phone_number") == TWILIO_PHONE_NUMBER:
                print(f"Phone number {TWILIO_PHONE_NUMBER} is already imported.")
                print(f"  Phone ID: {num.get('phone_number_id')}")
                print(f"  Agent ID: {num.get('agent_id')}")

                # Check if needs to be reassigned to different agent
                if num.get("agent_id") != ELEVENLABS_AGENT_ID:
                    print(f"\n  Note: Currently assigned to different agent.")
                    print(f"  To reassign, remove and re-import.")
                return True

    # Import to ElevenLabs
    print("Sending import request to ElevenLabs...")

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    # ElevenLabs API expects: phone_number, label, sid, token
    payload = {
        "phone_number": TWILIO_PHONE_NUMBER,
        "label": f"Voice Service - {TWILIO_PHONE_NUMBER}",
        "sid": TWILIO_ACCOUNT_SID,
        "token": TWILIO_AUTH_TOKEN,
        "agent_id": ELEVENLABS_AGENT_ID
    }

    response = requests.post(
        f"{ELEVENLABS_API_BASE}/phone-numbers/create",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201]:
        result = response.json()
        phone_id = result.get('phone_number_id', 'N/A')
        print("\nPhone number imported.")
        print(f"  Phone Number ID: {phone_id}")

        # Assign agent to phone number
        print(f"\nAssigning agent {ELEVENLABS_AGENT_ID}...")
        patch_resp = requests.patch(
            f"{ELEVENLABS_API_BASE}/phone-numbers/{phone_id}",
            headers=headers,
            json={"agent_id": ELEVENLABS_AGENT_ID}
        )

        if patch_resp.status_code == 200:
            patch_result = patch_resp.json()
            agent_info = patch_result.get('assigned_agent', {})
            print(f"  Agent assigned: {agent_info.get('agent_name', 'Unknown')} ({agent_info.get('agent_id', 'N/A')})")
            print(f"\nSuccess! You can now receive calls at {TWILIO_PHONE_NUMBER}")
            print("The call will be handled by your ElevenLabs agent.")
        else:
            print(f"  Warning: Could not assign agent: {patch_resp.status_code}")
            print(f"  {patch_resp.text}")
            print(f"\nPhone imported but agent not assigned. Manually assign in ElevenLabs dashboard.")

        return True
    else:
        print(f"\nError importing phone number: {response.status_code}")
        print(f"Response: {response.text}")

        # Try alternative endpoint /phone-numbers (without /create)
        print("\nTrying alternative endpoint...")

        response2 = requests.post(
            f"{ELEVENLABS_API_BASE}/phone-numbers",
            headers=headers,
            json=payload
        )

        if response2.status_code in [200, 201]:
            result = response2.json()
            print("\nSuccess! Phone number imported.")
            print(f"  Phone Number ID: {result.get('phone_number_id', 'N/A')}")
            print(f"  Agent ID: {result.get('agent_id', ELEVENLABS_AGENT_ID)}")
            print(f"\nYou can now receive calls at {TWILIO_PHONE_NUMBER}")
            return True
        else:
            print(f"\nAlternative also failed: {response2.status_code}")
            print(f"Response: {response2.text}")
            return False


def remove_phone_number():
    """Remove phone number from ElevenLabs."""
    print("\n=== Removing Phone Number from ElevenLabs ===\n")

    # Find the phone number ID
    existing = get_elevenlabs_phone_numbers()
    if not existing:
        print("Could not fetch phone numbers from ElevenLabs")
        return False

    phone_id = None
    for num in existing.get("phone_numbers", []):
        if num.get("phone_number") == TWILIO_PHONE_NUMBER:
            phone_id = num.get("phone_number_id")
            break

    if not phone_id:
        print(f"Phone number {TWILIO_PHONE_NUMBER} not found in ElevenLabs")
        return False

    print(f"Phone Number: {TWILIO_PHONE_NUMBER}")
    print(f"Phone ID: {phone_id}")
    print()

    # Confirm
    confirm = input("Are you sure you want to remove this number? (y/N): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return False

    # Delete
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    response = requests.delete(
        f"{ELEVENLABS_API_BASE}/phone-numbers/{phone_id}",
        headers=headers
    )

    if response.status_code in [200, 204]:
        print("\nPhone number removed from ElevenLabs.")
        print("The number is still in your Twilio account.")
        return True
    else:
        print(f"\nError removing phone number: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup phone number for Voice Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_phone.py status              # Show configuration status
  python setup_phone.py list-owned          # List Twilio numbers
  python setup_phone.py list-available      # List numbers to buy (US)
  python setup_phone.py list-available --country MX  # Mexican numbers
  python setup_phone.py import              # Import number to ElevenLabs
  python setup_phone.py remove              # Remove from ElevenLabs
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # status
    subparsers.add_parser("status", help="Show current phone configuration")

    # list-owned
    subparsers.add_parser("list-owned", help="List phone numbers in Twilio account")

    # list-available
    list_avail = subparsers.add_parser("list-available", help="List available numbers to purchase")
    list_avail.add_argument("--country", default="US", help="Country code (default: US)")
    list_avail.add_argument("--area-code", help="Area code filter")
    list_avail.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    # import
    subparsers.add_parser("import", help="Import Twilio number to ElevenLabs")

    # remove
    subparsers.add_parser("remove", help="Remove phone number from ElevenLabs")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "status":
        show_status()
    elif args.command == "list-owned":
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN required")
            return
        list_owned_numbers()
    elif args.command == "list-available":
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN required")
            return
        list_available_numbers(args.country, args.area_code, args.limit)
    elif args.command == "import":
        import_phone_number()
    elif args.command == "remove":
        remove_phone_number()


if __name__ == "__main__":
    main()
