#!/usr/bin/env python3
"""
Configure ElevenLabs Agent with Table Reservation Tools.
Creates tools in workspace and associates them to the agent.
Reads tool descriptions from config/business.yaml and prompt from config/agent_prompt.txt.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

from config.config_loader import config

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://YOUR_DOMAIN_HERE")

API_BASE = "https://api.elevenlabs.io/v1/convai"
HEADERS = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}


def get_tools_config():
    """Return the tools configuration for table reservations.
    Tool descriptions are read from config/business.yaml.
    """
    descs = config.tool_descriptions
    return [
        {
            "type": "webhook",
            "name": "check_table_availability",
            "description": descs.get("check_availability", "Check table availability"),
            "api_schema": {
                "url": f"{BASE_URL}/widget-api/tables/v1/availability",
                "method": "POST",
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                        "time": {"type": "string", "description": "Hora en formato HH:MM"},
                        "party_size": {"type": "integer", "description": "Numero de personas (1-20)"}
                    },
                    "required": ["date", "time", "party_size"]
                }
            }
        },
        {
            "type": "webhook",
            "name": "create_reservation",
            "description": descs.get("create_reservation", "Create a reservation"),
            "api_schema": {
                "url": f"{BASE_URL}/widget-api/tables/v1/reserve",
                "method": "POST",
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                        "time": {"type": "string", "description": "Hora en formato HH:MM"},
                        "party_size": {"type": "integer", "description": "Numero de personas"},
                        "customer_name": {"type": "string", "description": "Nombre del cliente"},
                        "customer_phone": {"type": "string", "description": "Telefono del cliente (solo numeros, sin codigo de pais)"},
                        "special_requests": {"type": "string", "description": "Peticiones especiales (opcional)"}
                    },
                    "required": ["date", "time", "party_size", "customer_name", "customer_phone"]
                }
            }
        },
        {
            "type": "webhook",
            "name": "search_reservations",
            "description": descs.get("search_reservations", "Search reservations by phone"),
            "api_schema": {
                "url": f"{BASE_URL}/widget-api/tables/v1/search",
                "method": "POST",
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Telefono del cliente (solo numeros)"}
                    },
                    "required": ["phone"]
                }
            }
        },
        {
            "type": "webhook",
            "name": "cancel_reservation",
            "description": descs.get("cancel_reservation", "Cancel a reservation"),
            "api_schema": {
                "url": f"{BASE_URL}/widget-api/tables/v1/cancel",
                "method": "POST",
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {"type": "string", "description": "ID interno de la reserva"},
                        "phone": {"type": "string", "description": "Telefono del cliente"}
                    },
                    "required": ["reservation_id", "phone"]
                }
            }
        },
        {
            "type": "webhook",
            "name": "modify_reservation",
            "description": descs.get("modify_reservation", "Modify a reservation"),
            "api_schema": {
                "url": f"{BASE_URL}/widget-api/tables/v1/modify",
                "method": "POST",
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {"type": "string", "description": "ID interno de la reserva"},
                        "phone": {"type": "string", "description": "Telefono del cliente"},
                        "new_date": {"type": "string", "description": "Nueva fecha YYYY-MM-DD (opcional)"},
                        "new_time": {"type": "string", "description": "Nueva hora HH:MM (opcional)"}
                    },
                    "required": ["reservation_id", "phone"]
                }
            }
        },
        {
            "type": "webhook",
            "name": "update_notes",
            "description": descs.get("update_notes", "Add notes to a reservation"),
            "api_schema": {
                "url": f"{BASE_URL}/widget-api/tables/v1/update-notes",
                "method": "POST",
                "request_body_schema": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {"type": "string", "description": "ID interno de la reserva"},
                        "phone": {"type": "string", "description": "Telefono del cliente"},
                        "notes": {"type": "string", "description": "Notas a agregar (restricciones, alergias, peticiones, etc.)"}
                    },
                    "required": ["reservation_id", "phone", "notes"]
                }
            }
        }
    ]


def get_existing_tools():
    """Get all tools in the workspace."""
    response = requests.get(f"{API_BASE}/tools", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("tools", [])
    return []


def create_tool(tool_config):
    """Create a new tool in the workspace."""
    payload = {"tool_config": tool_config}
    response = requests.post(f"{API_BASE}/tools", headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"  Error creating tool: {response.status_code}")
        print(f"  {response.text}")
        return None


def delete_tool(tool_id):
    """Delete a tool from workspace."""
    response = requests.delete(f"{API_BASE}/tools/{tool_id}", headers=HEADERS)
    return response.status_code == 200


def get_agent():
    """Get current agent configuration."""
    response = requests.get(f"{API_BASE}/agents/{ELEVENLABS_AGENT_ID}", headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return None


def update_agent_prompt():
    """Update the agent's system prompt and voice configuration."""
    prompt_text = config.agent_prompt
    if not prompt_text:
        print("Warning: agent_prompt.txt is empty, skipping prompt update")
        return False

    # Get voice ID from environment (optional)
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")

    payload = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": prompt_text
                }
            }
        }
    }

    # Add voice configuration if voice_id is set
    if voice_id:
        payload["conversation_config"]["tts"] = {
            "voice_id": voice_id
        }
        print(f"Voice ID: {voice_id}")

    response = requests.patch(
        f"{API_BASE}/agents/{ELEVENLABS_AGENT_ID}",
        headers=HEADERS,
        json=payload
    )

    if response.status_code == 200:
        print("Agent prompt updated successfully")
        if voice_id:
            print("Voice configuration updated successfully")
        return True
    else:
        print(f"Failed to update agent prompt: {response.status_code}")
        print(f"  {response.text}")
        return False


def update_agent_tool_ids(tool_ids):
    """Update agent with tool IDs."""
    # Get current agent config
    agent = get_agent()
    if not agent:
        return False

    prompt_config = agent.get("conversation_config", {}).get("agent", {}).get("prompt", {})

    # Keep existing system tools
    existing_tools = prompt_config.get("tools", [])
    system_tools = [t for t in existing_tools if t.get("type") == "system"]

    payload = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "tool_ids": tool_ids,
                    "tools": system_tools  # Keep system tools
                }
            }
        }
    }

    response = requests.patch(
        f"{API_BASE}/agents/{ELEVENLABS_AGENT_ID}",
        headers=HEADERS,
        json=payload
    )

    return response.status_code == 200


def configure_agent():
    """Main function to configure agent with reservation tools and prompt."""
    if not ELEVENLABS_API_KEY:
        print("Error: ELEVENLABS_API_KEY not set")
        return False

    if not ELEVENLABS_AGENT_ID:
        print("Error: ELEVENLABS_AGENT_ID not set")
        return False

    if "YOUR_DOMAIN" in BASE_URL:
        print("Error: Set WEBHOOK_BASE_URL in .env")
        return False

    print(f"Business: {config.business_name}")
    print(f"Agent: {ELEVENLABS_AGENT_ID}")
    print(f"Webhook URL: {BASE_URL}\n")

    # Step 1: Update agent prompt
    print("Updating agent prompt...")
    update_agent_prompt()

    # Step 2: Configure tools
    print("\nChecking existing tools...")
    existing_tools = get_existing_tools()
    existing_names = {t.get("tool_config", {}).get("name"): t.get("id") for t in existing_tools}

    tools_config = get_tools_config()
    tool_ids = []

    print(f"\nConfiguring {len(tools_config)} tools...")
    for tc in tools_config:
        name = tc["name"]

        # Delete existing tool with same name to update it
        if name in existing_names:
            print(f"  Updating: {name}")
            delete_tool(existing_names[name])

        # Create tool
        print(f"  Creating: {name}")
        result = create_tool(tc)
        if result:
            tool_ids.append(result["id"])
            print(f"    -> ID: {result['id']}")
        else:
            print(f"    -> FAILED")

    if not tool_ids:
        print("\nNo tools were created!")
        return False

    # Step 3: Associate tools with agent
    print(f"\nAssociating {len(tool_ids)} tools with agent...")
    if update_agent_tool_ids(tool_ids):
        print("\nAgent configured successfully!")
        return True
    else:
        print("\nFailed to update agent")
        return False


def list_tools():
    """List all tools in workspace and on agent."""
    print("\n=== Workspace Tools ===")
    tools = get_existing_tools()
    for t in tools:
        tc = t.get("tool_config", {})
        print(f"  [{tc.get('type')}] {tc.get('name')} (ID: {t.get('id')})")

    print("\n=== Agent Tools ===")
    agent = get_agent()
    if agent:
        prompt = agent.get("conversation_config", {}).get("agent", {}).get("prompt", {})
        tool_ids = prompt.get("tool_ids", [])
        tools = prompt.get("tools", [])
        print(f"  Tool IDs: {tool_ids}")
        print(f"  Inline tools: {len(tools)}")
        for t in tools:
            print(f"    - [{t.get('type')}] {t.get('name')}")

    print("\n=== Config ===")
    print(f"  Business: {config.business_name}")
    print(f"  Prompt length: {len(config.agent_prompt)} chars")
    print(f"  Tool descriptions: {list(config.tool_descriptions.keys())}")


if __name__ == "__main__":
    print("=" * 60)
    print(f"{config.business_name} - ElevenLabs Tools Configuration")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_tools()
    else:
        configure_agent()
