import json

from tools import (
    find_instructions,
    check_service_status,
    prepare_ticket,
)


def test_find_wifi_instructions():
    result = find_instructions.invoke({"topic": "Wi-Fi"})

    assert result["category"] == "wifi"
    assert result["instruction_id"]
    assert len(result["steps"]) > 0


def test_find_password_instructions():
    result = find_instructions.invoke({"topic": "password recovery"})

    assert result["category"] == "password"
    assert result["instruction_id"]
    assert len(result["steps"]) > 0


def test_find_unsupported_topic():
    result = find_instructions.invoke({"topic": "printer"})

    assert result["error"] == "Unsupported topic"


def test_wifi_normal_status():
    result = check_service_status.invoke({
        "service": "wifi",
        "profile": "normal",
    })

    assert result["service"] == "wifi"
    assert result["profile"] == "normal"
    assert result["status"] == "operational"


def test_password_recovery_outage():
    result = check_service_status.invoke({
        "service": "password recovery",
        "profile": "recovery_outage",
    })

    assert result["service"] == "account_recovery"
    assert result["profile"] == "recovery_outage"
    assert result["status"] != "operational"


def test_unknown_status_profile():
    result = check_service_status.invoke({
        "service": "wifi",
        "profile": "invalid",
    })

    assert result["error"] == "Unknown status profile"


def test_unknown_service():
    result = check_service_status.invoke({
        "service": "printer",
        "profile": "normal",
    })

    assert result["error"] == "Unknown service"


def test_prepare_ticket_creates_local_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPDESK_STORAGE_DIR", str(tmp_path))

    result = prepare_ticket.invoke({
        "user_id": "test-user",
        "thread_id": "test-thread",
        "category": "wifi",
        "summary": "Cannot connect to campus Wi-Fi",
        "steps_tried": ["Restarted Wi-Fi"],
        "service_status": "operational",
        "status_profile": "normal",
        "reference_ids": ["GUIDE-WIFI"],
    })

    assert result["ticket_id"].startswith("DRAFT-")
    assert result["status"] == "draft"
    assert result["user_id"] == "test-user"
    assert result["reference_ids"] == ["GUIDE-WIFI"]

    ticket_path = tmp_path / "tickets" / f"{result['ticket_id']}.json"

    assert ticket_path.exists()

    saved_ticket = json.loads(
        ticket_path.read_text(encoding="utf-8")
    )

    assert saved_ticket == result


def test_prepare_ticket_missing_details(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPDESK_STORAGE_DIR", str(tmp_path))

    result = prepare_ticket.invoke({
        "user_id": "test-user",
        "thread_id": "test-thread",
        "category": "wifi",
        "summary": "",
        "steps_tried": [],
    })

    assert result["error"] == "Missing ticket details"
    assert not (tmp_path / "tickets").exists()
