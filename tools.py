import os
import uuid
import json
from copy import deepcopy
from pathlib import Path

from langchain_core.tools import tool


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


@tool
def find_instructions(topic: str) -> dict:
    """Find local helpdesk instructions for Wi-Fi or password recovery."""
    data = load_json("helpdesk.json")

    normalized = (
        topic.lower()
        .replace("-", "")
        .replace(" ", "")
        .replace("_", "")
    )

    if "wifi" in normalized:
        category = "wifi"
    elif "password" in normalized or "accountrecovery" in normalized:
        category = "password"
    else:
        return {
            "error": "Unsupported topic",
            "supported_topics": ["wifi", "password"],
        }

    instructions = data["instructions"][category]

    return {
        "category": category,
        "title": instructions["title"],
        "steps": instructions["steps"],
        "instruction_id": instructions["instruction_id"],
    }

@tool
def check_service_status(
    service: str,
    profile: str = "normal",
) -> dict:
    """Check fictional Wi-Fi or account recovery service status."""
    data = load_json("service_status.json")
    profiles = data["profiles"]

    if profile not in profiles:
        return {
            "error": "Unknown status profile",
            "available_profiles": list(profiles.keys()),
        }

    service = service.lower().strip()
    normalized = (
        service.replace("-", "")
        .replace(" ", "")
        .replace("_", "")
    )

    if "wifi" in normalized:
        service = "wifi"
    elif "password" in normalized or "accountrecovery" in normalized:
        service = "account_recovery"
    else:
        return {
            "error": "Unknown service",
            "supported_services": ["wifi", "account_recovery"],
        }

    status = profiles[profile][service]

    return {
        "service": service,
        "profile": profile,
        "status": status["status"],
        "message": status["message"],
    }

@tool
def prepare_ticket(
    user_id: str,
    thread_id: str,
    category: str,
    summary: str,
    steps_tried: list[str],
    service_status: str = "unknown",
    status_profile: str = "normal",
    reference_ids: list[str] | None = None,
) -> dict:
    """Create a local ticket draft without submitting it."""
    template = load_json("ticket_template.json")
    ticket = deepcopy(template["ticket"])

    if not summary.strip() or not steps_tried:
        return {
            "error": "Missing ticket details",
            "message": "Problem description and steps tried are required.",
        }

    ticket.update({
        "ticket_id": None,
        "status": "draft",
        "user_id": user_id,
        "thread_id": thread_id,
        "category": category,
        "summary": summary,
        "steps_tried": steps_tried,
        "service_status": service_status,
        "status_profile": status_profile,
        "reference_ids": reference_ids or [],
    })

    
    storage_dir = Path(
        os.getenv("HELPDESK_STORAGE_DIR", "local-storage")
    )

    if not storage_dir.is_absolute():
        storage_dir = BASE_DIR / storage_dir

    tickets_dir = storage_dir / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)

    ticket["ticket_id"] = f"DRAFT-{uuid.uuid4().hex[:12]}"

    ticket_path = tickets_dir / f"{ticket['ticket_id']}.json"

    with open(ticket_path, "w", encoding="utf-8") as f:
        json.dump(ticket, f, ensure_ascii=False, indent=2)

    return ticket

