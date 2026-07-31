from typing import Any

from fastapi.testclient import TestClient


def send_chat(
    client: TestClient,
    message: str,
    conversation_id: str | None = None,
):
    payload: dict[str, Any] = {"message": message}

    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    return client.post("/chat", json=payload)


def assert_success(response) -> dict[str, Any]:
    assert response.status_code == 200, response.text

    body = response.json()

    assert body["status"] == "success", body

    return body


def test_chat_requires_authentication(client: TestClient):
    response = send_chat(client, "List all users")

    assert response.status_code == 401


def test_complete_chat_crud_flow(
    authenticated_client: TestClient,
):
    client = authenticated_client

    created = assert_success(
        send_chat(
            client,
            "Add user Sara Ahmed with email sara@example.com, "
            "phone 03001234567 and city Lahore",
        )
    )

    conversation_id = created["conversation_id"]

    assert created["data"]["city"] == "Lahore"

    found = assert_success(
        send_chat(
            client,
            "Show user Sara Ahmed",
            conversation_id,
        )
    )

    assert found["data"]["email"] == "sara@example.com"

    updated = assert_success(
        send_chat(
            client,
            "Update Sara Ahmed's city to Islamabad",
            conversation_id,
        )
    )

    assert updated["data"]["city"] == "Islamabad"

    listed = assert_success(
        send_chat(
            client,
            "List all users",
            conversation_id,
        )
    )

    assert len(listed["data"]) == 1

    counted = assert_success(
        send_chat(
            client,
            "How many users are there?",
            conversation_id,
        )
    )

    assert counted["data"]["count"] == 1

    delete_request = send_chat(
        client,
        "Delete user Sara Ahmed",
        conversation_id,
    )

    assert delete_request.status_code == 200

    delete_body = delete_request.json()

    assert delete_body["status"] == "needs_confirmation"
    assert delete_body["action"]["type"] == "confirm_delete"

    confirmed = client.post(
        "/chat/confirm",
        json={
            "token": delete_body["action"]["token"],
            "confirm": True,
            "conversation_id": conversation_id,
        },
    )

    confirmed_body = assert_success(confirmed)

    assert confirmed_body["data"]["email"] == "sara@example.com"

    final_count = assert_success(
        send_chat(
            client,
            "How many users are there?",
            conversation_id,
        )
    )

    assert final_count["data"]["count"] == 0


def test_email_only_create_matches_assignment(
    authenticated_client: TestClient,
):
    body = assert_success(
        send_chat(
            authenticated_client,
            "Can you add john.smith@xyz.com "
            "with phone number 03001234567?",
        )
    )

    assert body["data"]["name"] is None
    assert body["data"]["email"] == "john.smith@xyz.com"
    assert body["data"]["phone"] == "03001234567"


def test_multiturn_create_collects_follow_up_fields(
    authenticated_client: TestClient,
):
    client = authenticated_client

    started = send_chat(
        client,
        "We have a new employee called Sara",
    ).json()

    conversation_id = started["conversation_id"]

    assert started["status"] == "collecting_fields"
    assert started["context"]["current_intent"] == "create"
    assert started["context"]["awaiting_field"] == "email"
    assert started["context"]["draft_fields"]["name"] == "Sara"

    email = send_chat(
        client,
        "Use sara@example.com for her",
        conversation_id,
    ).json()

    assert email["status"] == "collecting_fields"
    assert email["context"]["awaiting_field"] == "phone"

    phone = send_chat(
        client,
        "03001234567",
        conversation_id,
    ).json()

    assert phone["status"] == "collecting_fields"
    assert phone["context"]["awaiting_field"] == "city"

    completed = assert_success(
        send_chat(
            client,
            "She lives in Lahore",
            conversation_id,
        )
    )

    assert completed["data"]["name"] == "Sara"
    assert completed["data"]["email"] == "sara@example.com"
    assert completed["data"]["phone"] == "03001234567"
    assert completed["data"]["city"] == "Lahore"


def test_multiturn_create_can_skip_optional_fields(
    authenticated_client: TestClient,
):
    client = authenticated_client

    started = send_chat(
        client,
        "Register someone called Noor",
    ).json()

    conversation_id = started["conversation_id"]

    email = send_chat(
        client,
        "Her email is noor@example.com",
        conversation_id,
    ).json()

    assert email["context"]["awaiting_field"] == "phone"

    skipped_phone = send_chat(
        client,
        "Skip phone",
        conversation_id,
    ).json()

    assert skipped_phone["context"]["awaiting_field"] == "city"

    created = assert_success(
        send_chat(
            client,
            "Create her now",
            conversation_id,
        )
    )

    assert created["data"]["email"] == "noor@example.com"
    assert created["data"]["phone"] is None
    assert created["data"]["city"] is None


def test_selected_user_pronouns_and_context_question(
    authenticated_client: TestClient,
):
    client = authenticated_client

    created = assert_success(
        send_chat(
            client,
            "Add user Ayesha with email ayesha@example.com "
            "and city Lahore",
        )
    )

    conversation_id = created["conversation_id"]

    shown = assert_success(
        send_chat(
            client,
            "Show me Ayesha",
            conversation_id,
        )
    )

    assert (
        shown["context"]["selected_user"]["email"]
        == "ayesha@example.com"
    )

    updated = assert_success(
        send_chat(
            client,
            "She moved to Islamabad recently",
            conversation_id,
        )
    )

    assert updated["data"]["city"] == "Islamabad"

    context = assert_success(
        send_chat(
            client,
            "Who were we editing?",
            conversation_id,
        )
    )

    assert "Ayesha" in context["reply"]


def test_duplicate_names_support_second_one_selection(
    authenticated_client: TestClient,
):
    client = authenticated_client

    first = assert_success(
        send_chat(
            client,
            "Add Ali with email ali.one@example.com",
        )
    )

    conversation_id = first["conversation_id"]

    assert_success(
        send_chat(
            client,
            "Add Ali with email ali.two@example.com",
            conversation_id,
        )
    )

    ambiguous = send_chat(
        client,
        "Show Ali",
        conversation_id,
    ).json()

    assert ambiguous["status"] == "needs_clarification"
    assert len(ambiguous["data"]) == 2
    assert ambiguous["context"]["candidate_count"] == 2

    selected = assert_success(
        send_chat(
            client,
            "Second one",
            conversation_id,
        )
    )

    assert selected["data"]["email"] == "ali.two@example.com"


def test_duplicate_selection_by_city_and_natural_delete_cancellation(
    authenticated_client: TestClient,
):
    client = authenticated_client

    first = assert_success(
        send_chat(
            client,
            "Add Ali with email ali.lahore@example.com "
            "and city Lahore",
        )
    )

    conversation_id = first["conversation_id"]

    assert_success(
        send_chat(
            client,
            "Add Ali with email ali.karachi@example.com "
            "and city Karachi",
            conversation_id,
        )
    )

    ambiguous = send_chat(
        client,
        "Delete Ali",
        conversation_id,
    ).json()

    assert ambiguous["status"] == "needs_clarification"

    selected = send_chat(
        client,
        "The Karachi one",
        conversation_id,
    ).json()

    assert selected["status"] == "needs_confirmation"
    assert selected["data"]["email"] == "ali.karachi@example.com"

    cancelled = send_chat(
        client,
        "Actually don't delete him",
        conversation_id,
    ).json()

    assert cancelled["status"] == "cancelled"

    still_exists = assert_success(
        send_chat(
            client,
            "Show ali.karachi@example.com",
            conversation_id,
        )
    )

    assert (
        still_exists["data"]["email"]
        == "ali.karachi@example.com"
    )


def test_pending_delete_can_switch_to_update(
    authenticated_client: TestClient,
):
    client = authenticated_client

    created = assert_success(
        send_chat(
            client,
            "Add Sara with email sara@example.com",
        )
    )

    conversation_id = created["conversation_id"]

    delete_request = send_chat(
        client,
        "Delete her",
        conversation_id,
    ).json()

    assert delete_request["status"] == "needs_confirmation"

    switched = send_chat(
        client,
        "No, change her number instead",
        conversation_id,
    ).json()

    assert switched["status"] == "collecting_fields"
    assert switched["context"]["current_intent"] == "update"
    assert switched["context"]["awaiting_field"] == "phone"

    updated = assert_success(
        send_chat(
            client,
            "03009998888",
            conversation_id,
        )
    )

    assert updated["data"]["phone"] == "03009998888"


def test_confirmation_button_can_cancel_delete(
    authenticated_client: TestClient,
):
    client = authenticated_client

    created = assert_success(
        send_chat(
            client,
            "Add Ali with email ali@example.com",
        )
    )

    conversation_id = created["conversation_id"]

    request = send_chat(
        client,
        "Delete ali@example.com",
        conversation_id,
    ).json()

    cancelled = client.post(
        "/chat/confirm",
        json={
            "token": request["action"]["token"],
            "confirm": False,
            "conversation_id": conversation_id,
        },
    )

    cancelled_body = cancelled.json()

    assert cancelled.status_code == 200
    assert cancelled_body["status"] == "cancelled"

    assert_success(
        send_chat(
            client,
            "Show ali@example.com",
            conversation_id,
        )
    )


def test_activity_log_records_create_and_update(
    authenticated_client: TestClient,
):
    client = authenticated_client

    created = assert_success(
        send_chat(
            client,
            "Add Sara with email sara@example.com",
        )
    )

    conversation_id = created["conversation_id"]

    assert_success(
        send_chat(
            client,
            "Update Sara's city to Karachi",
            conversation_id,
        )
    )

    activity = assert_success(
        send_chat(
            client,
            "Show recent activity",
            conversation_id,
        )
    )

    assert activity["data"][0]["action"] == "user_updated"
    assert activity["data"][1]["action"] == "user_created"


def test_workspace_users_and_conversations_are_isolated(
    authenticated_client: TestClient,
    second_authenticated_client: TestClient,
):
    first_client = authenticated_client
    second_client = second_authenticated_client

    created = assert_success(
        send_chat(
            first_client,
            "Add Shared Name with email shared@example.com",
        )
    )

    first_conversation_id = created["conversation_id"]

    second_count = assert_success(
        send_chat(
            second_client,
            "How many users are there?",
        )
    )

    assert second_count["data"]["count"] == 0

    duplicate_in_other_workspace = assert_success(
        send_chat(
            second_client,
            "Add Shared Name with email shared@example.com",
        )
    )

    assert (
        duplicate_in_other_workspace["data"]["email"]
        == "shared@example.com"
    )

    foreign_history = second_client.get(
        f"/chat/conversations/{first_conversation_id}"
    )

    assert foreign_history.status_code == 404


def test_conversation_history_persists_and_reset_clears_it(
    authenticated_client: TestClient,
):
    client = authenticated_client

    greeting = assert_success(
        send_chat(
            client,
            "Hello",
        )
    )

    conversation_id = greeting["conversation_id"]

    history = client.get(
        f"/chat/conversations/{conversation_id}"
    )

    assert history.status_code == 200

    history_body = history.json()

    assert [
        message["role"]
        for message in history_body["messages"]
    ] == [
        "user",
        "assistant",
    ]

    reset = client.delete(
        f"/chat/conversations/{conversation_id}"
    )

    assert reset.status_code == 200

    reset_body = reset.json()

    assert reset_body["messages"] == []
    assert reset_body["context"]["status"] == "idle"
    assert reset_body["context"]["selected_user_id"] is None
    assert reset_body["context"]["draft_fields"] == {}

    restored = client.get(
        f"/chat/conversations/{conversation_id}"
    )

    assert restored.status_code == 200
    assert restored.json()["messages"] == []


def test_missing_information_question_uses_saved_context(
    authenticated_client: TestClient,
):
    client = authenticated_client

    started = send_chat(
        client,
        "Create a user named Hina",
    ).json()

    conversation_id = started["conversation_id"]

    assert started["context"]["awaiting_field"] == "email"

    context = assert_success(
        send_chat(
            client,
            "What information is still missing?",
            conversation_id,
        )
    )

    assert "email" in context["reply"].lower()


def test_common_typos_use_safe_fallback(
    authenticated_client: TestClient,
):
    client = authenticated_client

    created = assert_success(
        send_chat(
            client,
            "craete user Zara with email zara@example.com",
        )
    )

    conversation_id = created["conversation_id"]

    assert created["context"]["ai_mode"] == "fallback"

    shown = assert_success(
        send_chat(
            client,
            "shwo Zara",
            conversation_id,
        )
    )

    assert shown["data"]["email"] == "zara@example.com"

    updated = assert_success(
        send_chat(
            client,
            "udpate her city to Multan",
            conversation_id,
        )
    )

    assert updated["data"]["city"] == "Multan"

    def test_completed_deletion_cannot_be_falsely_cancelled(
    authenticated_client: TestClient,
): client = authenticated_client

    created = assert_success(
        send_chat(
            client,
            "Add Ali with email ali@example.com",
        )
    )

    conversation_id = created["conversation_id"]

    delete_request = send_chat(
        client,
        "Delete Ali",
        conversation_id,
    ).json()

    assert delete_request["status"] == "needs_confirmation"

    confirmed = client.post(
        "/chat/confirm",
        json={
            "token": delete_request["action"]["token"],
            "confirm": True,
            "conversation_id": conversation_id,
        },
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "success"

    late_cancel = send_chat(
        client,
        "Don't delete Ali",
        conversation_id,
    )

    assert late_cancel.status_code == 200

    late_cancel_body = late_cancel.json()

    assert late_cancel_body["status"] == "invalid"
    assert "already confirmed" in late_cancel_body["reply"].lower()

    show_deleted = send_chat(
        client,
        "Show Ali",
        conversation_id,
    ).json()

    assert show_deleted["status"] == "not_found"

    # ---------------------------------------------------------------------------
# Final behavior regression tests
# These tests protect the fixes for partial-name resolution, stale candidate
# state, clean city extraction, and safe deletion cancellation.
# ---------------------------------------------------------------------------


def _send_behavior_regression_chat(
    client,
    message: str,
    conversation_id: str | None = None,
):
    payload = {"message": message}

    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    return client.post("/chat", json=payload)


def test_regression_unique_first_name_resolves_full_name(
    authenticated_client,
):
    client = authenticated_client

    created = _send_behavior_regression_chat(
        client,
        (
            "Add user Zara Khan with email zara@example.com "
            "and city Faisalabad"
        ),
    ).json()

    conversation_id = created["conversation_id"]

    shown = _send_behavior_regression_chat(
        client,
        "Show Zara",
        conversation_id,
    ).json()

    assert shown["status"] == "success"
    assert shown["data"]["name"] == "Zara Khan"
    assert shown["data"]["email"] == "zara@example.com"

    delete_request = _send_behavior_regression_chat(
        client,
        "Delete Zara",
        conversation_id,
    ).json()

    assert delete_request["status"] == "needs_confirmation"
    assert delete_request["data"]["name"] == "Zara Khan"
    assert delete_request["data"]["email"] == "zara@example.com"


def test_regression_duplicate_first_name_requires_clarification(
    authenticated_client,
):
    client = authenticated_client

    first = _send_behavior_regression_chat(
        client,
        "Add user Zara Khan with email zara.khan@example.com",
    ).json()

    conversation_id = first["conversation_id"]

    _send_behavior_regression_chat(
        client,
        "Add user Zara Ali with email zara.ali@example.com",
        conversation_id,
    )

    ambiguous = _send_behavior_regression_chat(
        client,
        "Show Zara",
        conversation_id,
    ).json()

    assert ambiguous["status"] == "needs_clarification"
    assert len(ambiguous["data"]) == 2


def test_regression_fresh_read_clears_old_candidate_selection(
    authenticated_client,
):
    client = authenticated_client

    first = _send_behavior_regression_chat(
        client,
        "Add user Ali Khan with email ali.khan@example.com",
    ).json()

    conversation_id = first["conversation_id"]

    _send_behavior_regression_chat(
        client,
        "Add user Ali Raza with email ali.raza@example.com",
        conversation_id,
    )

    ambiguous = _send_behavior_regression_chat(
        client,
        "Show Ali",
        conversation_id,
    ).json()

    assert ambiguous["status"] == "needs_clarification"

    missing = _send_behavior_regression_chat(
        client,
        "Where is Liz?",
        conversation_id,
    ).json()

    assert missing["status"] == "not_found"
    assert "could not find" in missing["reply"].lower()
    assert missing["context"]["candidate_count"] == 0


def test_regression_pending_delete_switches_to_clean_city_update(
    authenticated_client,
):
    client = authenticated_client

    created = _send_behavior_regression_chat(
        client,
        (
            "Add user Zara Khan with email zara@example.com "
            "and city Faisalabad"
        ),
    ).json()

    conversation_id = created["conversation_id"]

    delete_request = _send_behavior_regression_chat(
        client,
        "Delete Zara",
        conversation_id,
    ).json()

    assert delete_request["status"] == "needs_confirmation"

    stale_token = delete_request["action"]["token"]

    updated = _send_behavior_regression_chat(
        client,
        "her city should be Islamabad now",
        conversation_id,
    ).json()

    assert updated["status"] == "success"
    assert updated["data"]["city"] == "Islamabad"
    assert updated["context"]["pending_action"] is None

    stale_confirmation = client.post(
        "/chat/confirm",
        json={
            "token": stale_token,
            "confirm": True,
            "conversation_id": conversation_id,
        },
    )

    assert stale_confirmation.status_code == 409

    still_exists = _send_behavior_regression_chat(
        client,
        "Find zara@example.com",
        conversation_id,
    ).json()

    assert still_exists["status"] == "success"
    assert still_exists["data"]["name"] == "Zara Khan"
    assert still_exists["data"]["city"] == "Islamabad"

    reassurance = _send_behavior_regression_chat(
        client,
        "Actually don't delete her",
        conversation_id,
    ).json()

    assert reassurance["status"] == "success"
    assert "has not been deleted" in reassurance["reply"].lower()