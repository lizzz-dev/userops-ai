from app.services.command_parser import parse_command


def test_create_parser():
    parsed = parse_command(
        "Add user Sara Ahmed with email sara@example.com, phone 03001234567 and city Lahore"
    )
    assert parsed["intent"] == "create"
    assert parsed["name"] == "Sara Ahmed"
    assert parsed["email"] == "sara@example.com"
    assert parsed["fields"]["phone"] == "03001234567"
    assert parsed["fields"]["city"] == "Lahore"
    assert parsed["missing_fields"] == []


def test_read_update_list_and_count_parser():
    assert parse_command("Show user with ID 9")["user_id"] == 9
    updated = parse_command("Update Sara Ahmed's city to Karachi")
    assert updated["intent"] == "update"
    assert updated["name"] == "Sara Ahmed"
    assert updated["fields"]["city"] == "Karachi"
    assert parse_command("List all users")["intent"] == "list"
    assert parse_command("How many users are there?")["intent"] == "count"


def test_assignment_wording_variants():
    created = parse_command(
        "can you add the user john.smith@xyz.com with phone number 03001234567"
    )
    assert created["intent"] == "create"
    assert created["email"] == "john.smith@xyz.com"
    assert created["name"] is None
    assert created["missing_fields"] == []

    updated = parse_command("can you update samanthas city to Cordoba")
    assert updated["intent"] == "update"
    assert updated["name"].lower() == "samantha"
    assert updated["fields"]["city"] == "Cordoba"



# ---------------------------------------------------------------------------
# Final parser regression tests
# ---------------------------------------------------------------------------


def test_regression_natural_city_and_read_reference_parsing():
    from app.services.command_parser import extract_city, parse_command

    assert extract_city(
        "her city should be Islamabad now"
    ) == "Islamabad"

    show_user = parse_command("Show Zara")
    assert show_user["intent"] == "read"
    assert show_user["name"] == "Zara"

    where_user = parse_command("Where is Zara?")
    assert where_user["intent"] == "read"
    assert where_user["name"] == "Zara"

    trailing_user_word = parse_command("Find Zara user")
    assert trailing_user_word["intent"] == "read"
    assert trailing_user_word["name"] == "Zara"