import re
from typing import Any

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
USER_ID_PATTERN = re.compile(
    r"\b(?:user\s+)?id\s*(?:is|=|:)?\s*(\d+)\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"\b(?:phone(?:\s+number)?|mobile)\b"
    r"(?:\s+of\s+.+?\s+to\s*|\s*(?:is|=|:|to)?\s+)"
    r"([+]?\d(?:[\d\s().-]{5,18}\d))"
    r"(?=\s*(?:,|;|\.|\band\b|\bcity\b|\bemail\b|\bname\b|$))",
    re.IGNORECASE,
)
CITY_PATTERN = re.compile(
    r"\bcity\s*(?:"
    r"(?:should|must)\s+be\s+|"
    r"needs?\s+to\s+be\s+|"
    r"(?:is|=|:|to)\s+"
    r")?"
    r"(.+?)"
    r"(?=\s+(?:and\s+)?(?:phone|email|name)\b|[,.;!?]|$)",
    re.IGNORECASE,
)
NEW_NAME_PATTERN = re.compile(
    r"\bname\s*(?:is|=|:|to)\s+"
    r"(.+?)"
    r"(?=\s+(?:and\s+)?(?:phone|email|city)\b|[,.;!?]|$)",
    re.IGNORECASE,
)


def clean_value(value: str) -> str:
    return " ".join(value.strip(" \t\n,.;:'\"!?").split())


def clean_reference(value: str) -> str:
    """Normalize a human user reference without changing the actual name."""
    cleaned = clean_value(value)
    cleaned = re.sub(
        r"\s+(?:user|person|employee|record)$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def clean_city(value: str) -> str:
    """Remove conversational filler while preserving multi-word city names."""
    cleaned = clean_value(value)
    cleaned = re.sub(
        r"^(?:(?:should|must)\s+be|needs?\s+to\s+be)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s+(?:now|please|recently)$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def detect_intent(message: str) -> str:
    lowered = message.lower()

    if re.search(r"\b(how many|count|total number of)\s+users?\b", lowered):
        return "count"

    if re.search(
        r"\b(?:show|list|view)\s+(?:recent\s+)?(?:activity|actions|audit\s+log)\b",
        lowered,
    ):
        return "activity"

    if re.search(
        r"\b(?:list\s+(?:all\s+)?users?"
        r"|(?:show|display|get)\s+(?:me\s+)?all\s+users?"
        r"|(?:show|display|get)\s+(?:me\s+)?users)\b",
        lowered,
    ):
        return "list"

    if re.search(r"\b(add|create|insert|register)\b", lowered):
        return "create"

    if re.search(r"\b(update|change|modify|set)\b", lowered):
        return "update"

    if re.search(r"\b(delete|remove|erase)\b", lowered):
        return "delete"

    if re.search(
        r"\b(?:show|find|get|display|view|lookup|search|where\s+(?:is|are))\b",
        lowered,
    ):
        return "read"

    return "unknown"


def extract_email(message: str) -> str | None:
    match = EMAIL_PATTERN.search(message)
    return match.group(0).lower() if match else None


def extract_user_id(message: str) -> int | None:
    match = USER_ID_PATTERN.search(message)
    return int(match.group(1)) if match else None


def extract_phone(message: str) -> str | None:
    match = PHONE_PATTERN.search(message)
    return clean_value(match.group(1)) if match else None


def extract_city(message: str) -> str | None:
    match = CITY_PATTERN.search(message)
    if not match:
        return None
    city = clean_city(match.group(1))
    return city or None


def extract_new_name(message: str) -> str | None:
    match = NEW_NAME_PATTERN.search(message)
    return clean_value(match.group(1)) if match else None


def extract_create_name(message: str) -> str | None:
    pattern = re.compile(
        r"\b(?:add|create|insert|register)\b"
        r"(?:\s+(?:a|the))?"
        r"(?:\s+new)?"
        r"(?:\s+user)?"
        r"\s+(.+?)"
        r"(?=\s+(?:with\s+)?email\b"
        r"|\s+(?:with\s+)?phone\b"
        r"|\s+(?:with\s+)?city\b"
        r"|[,;]|$)",
        re.IGNORECASE,
    )
    match = pattern.search(message)
    if not match:
        return None

    name = clean_value(match.group(1))
    if "@" in name or name.lower() in {"user", "a user", "new user"}:
        return None
    return name


def extract_target_name(message: str, intent: str) -> str | None:
    if intent == "create":
        return extract_create_name(message)

    if intent == "update":
        patterns = [
            re.compile(
                r"\b(?:update|change|modify|set)\s+(?:the\s+)?(?:user\s+)?"
                r"(.+?)['’]s\s+(?:name|phone|city)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:update|change|modify|set)\s+(?:the\s+)?(?:user\s+)?"
                r"(.+?)s\s+(?:name|phone|city)\s+to\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:update|change|modify|set)\s+(?:the\s+)?(?:user\s+)?"
                r"(.+?)\s+(?:name|phone|city)\s+to\b",
                re.IGNORECASE,
            ),
        ]
        for pattern in patterns:
            match = pattern.search(message)
            if match:
                return clean_value(match.group(1))

    if intent == "delete":
        match = re.search(
            r"\b(?:delete|remove|erase)\s+(?:the\s+)?(?:user\s+)?(?:named\s+)?"
            r"(.+?)\s*$",
            message,
            re.IGNORECASE,
        )
        if match:
            return clean_reference(match.group(1))

    if intent == "read":
        patterns = [
            re.compile(
                r"\b(?:show|find|get|display|view|lookup|search)"
                r"(?:\s+me)?(?:\s+the)?(?:\s+user)?"
                r"(?:\s+(?:information|info|details))?"
                r"(?:\s+(?:for|of|about|named))?\s+"
                r"(.+?)\s*[?.!]*$",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bwhere\s+(?:is|are)\s+(?:the\s+)?(?:user\s+)?"
                r"(.+?)\s*[?.!]*$",
                re.IGNORECASE,
            ),
        ]
        for pattern in patterns:
            match = pattern.search(message)
            if match:
                return clean_reference(match.group(1))

    return None


def find_missing_fields(
    intent: str,
    *,
    email: str | None,
    name: str | None,
    user_id: int | None,
    fields: dict[str, str],
) -> list[str]:
    missing: list[str] = []

    if intent == "create":
        if not email:
            missing.append("email")

    if intent in {"read", "update", "delete"}:
        if not (email or name or user_id is not None):
            missing.append("user reference")

    if intent == "update" and not fields:
        missing.append("field to update")

    return missing


def parse_command(message: str) -> dict[str, Any]:
    cleaned_message = message.strip()
    intent = detect_intent(cleaned_message)
    email = extract_email(cleaned_message)
    user_id = extract_user_id(cleaned_message)
    name = extract_target_name(cleaned_message, intent)

    fields: dict[str, str] = {}
    phone = extract_phone(cleaned_message)
    city = extract_city(cleaned_message)

    if phone:
        fields["phone"] = phone
    if city:
        fields["city"] = city

    if intent == "update":
        new_name = extract_new_name(cleaned_message)
        if new_name:
            fields["name"] = new_name

    missing_fields = find_missing_fields(
        intent,
        email=email,
        name=name,
        user_id=user_id,
        fields=fields,
    )

    return {
        "intent": intent,
        "email": email,
        "name": name,
        "user_id": user_id,
        "fields": fields,
        "missing_fields": missing_fields,
    }