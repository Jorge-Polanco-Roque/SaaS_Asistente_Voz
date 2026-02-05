"""
Configuration loader for multi-business voice service.
Reads business.yaml and agent_prompt.txt and exposes them as a singleton.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

CONFIG_DIR = Path(__file__).parent
BUSINESS_YAML = CONFIG_DIR / "business.yaml"
AGENT_PROMPT_TXT = CONFIG_DIR / "agent_prompt.txt"


class BusinessConfig:
    """Singleton that holds all business configuration."""

    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if BusinessConfig._loaded:
            return
        self._data: Dict[str, Any] = {}
        self._agent_prompt: str = ""
        self._load()
        BusinessConfig._loaded = True

    def _load(self):
        """Load configuration from YAML and prompt files."""
        with open(BUSINESS_YAML, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)

        if AGENT_PROMPT_TXT.exists():
            with open(AGENT_PROMPT_TXT, "r", encoding="utf-8") as f:
                self._agent_prompt = f.read().strip()

    # ------------------------------------------------------------------
    # Top-level properties
    # ------------------------------------------------------------------

    @property
    def business_name(self) -> str:
        return self._data.get("business_name", "My Business")

    @property
    def business_type(self) -> str:
        return self._data.get("business_type", "restaurante")

    # ------------------------------------------------------------------
    # Reservation settings
    # ------------------------------------------------------------------

    @property
    def reservation(self) -> Dict[str, Any]:
        return self._data.get("reservation", {})

    @property
    def duration_hours(self) -> float:
        return self.reservation.get("duration_hours", 2.0)

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------

    @property
    def tables(self) -> List[Dict[str, Any]]:
        return self._data.get("tables", [])

    def get_mock_tables(self) -> List[Dict[str, Any]]:
        """Return tables from config formatted for mock mode."""
        return [
            {
                "id": t["id"],
                "nombre": t["name"],
                "capacidad": t["capacity"],
                "ubicacion": t["location"],
                "activa": True,
            }
            for t in self.tables
        ]

    # ------------------------------------------------------------------
    # Tool descriptions (for ElevenLabs)
    # ------------------------------------------------------------------

    @property
    def tool_descriptions(self) -> Dict[str, str]:
        return self._data.get("tool_descriptions", {})

    # ------------------------------------------------------------------
    # Agent prompt
    # ------------------------------------------------------------------

    @property
    def agent_prompt(self) -> str:
        return self._agent_prompt

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    @property
    def messages(self) -> Dict[str, str]:
        return self._data.get("messages", {})

    def msg(self, key: str, **kwargs) -> str:
        """Get a formatted message by key.

        Example:
            config.msg("no_tables_capacity", party_size=4)
        """
        template = self.messages.get(key, key)
        try:
            return template.format(**kwargs)
        except KeyError:
            return template


# Singleton instance — import this from anywhere
config = BusinessConfig()
