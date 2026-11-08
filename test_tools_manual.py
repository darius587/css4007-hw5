
from tools import (
    find_instructions,
    check_service_status,
    prepare_ticket,
)


print("\nTEST 1: Find Wi-Fi instructions")
print(find_instructions.invoke({"topic": "wifi"}))


print("\nTEST 2: Check normal Wi-Fi status")
print(check_service_status.invoke({
    "service": "wifi",
    "profile": "normal",
}))


print("\nTEST 3: Check Wi-Fi outage")
print(check_service_status.invoke({
    "service": "wifi",
    "profile": "wifi_outage",
}))


print("\nTEST 4: Prepare a ticket")
print(prepare_ticket.invoke({
    "user_id": "demo-user-a",
    "thread_id": "demo-thread-1",
    "category": "wifi",
    "summary": "Wi-Fi does not connect",
    "steps_tried": [
        "Checked Wi-Fi settings",
        "Forgot and reconnected to the network",
    ],
    "service_status": "operational",
    "status_profile": "normal",
    "reference_ids": ["GUIDE-WIFI"],
}))


print("\nTEST 5: Missing ticket details")
print(prepare_ticket.invoke({
    "user_id": "demo-user-a",
    "thread_id": "demo-thread-1",
    "category": "wifi",
    "summary": "",
    "steps_tried": [],
}))
