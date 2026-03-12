import base64
import re


def decode_base64url(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode(
        "utf-8",
        errors="replace",
    )


def extract_text_from_payload(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")

    if mime_type == "text/plain" and data:
        return decode_base64url(data)

    for part in payload.get("parts", []):
        text = extract_text_from_payload(part)
        if text:
            return text

    return ""


def get_message_body(gmail_service, message_id: str) -> str:
    message = gmail_service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()

    payload = message.get("payload", {})
    return extract_text_from_payload(payload)


def list_onboarding_messages(gmail_service, max_results: int = 10) -> list[dict]:
    response = gmail_service.users().messages().list(
        userId="me",
        q='subject:ONBOARD newer_than:15d -label:onboarding-processado -label:onboarding-ignorado',
        maxResults=max_results,
    ).execute()

    return response.get("messages", [])


def clean_quoted_lines(text: str) -> str:
    lines = text.splitlines()
    clean_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith(">"):
            continue

        clean_lines.append(line)

    return "\n".join(clean_lines)


def normalize_text_block(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_main_onboarding_block(body: str) -> str:
    body = clean_quoted_lines(body)
    body = normalize_text_block(body)

    start_index = body.upper().find("ONBOARD DE CONTRATAÇÃO")
    if start_index == -1:
        return body

    return body[start_index:]


def extract_field_block(text: str, start_label: str, end_label: str | None = None) -> str:
    pattern = rf"{re.escape(start_label)}\s*(.*?)"

    if end_label:
        pattern += rf"\s*{re.escape(end_label)}"
    else:
        pattern += r"$"

    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""

    return match.group(1).strip()


def parse_multiline_comma_list(raw_value: str) -> list[str]:
    if not raw_value:
        return []

    cleaned = raw_value.replace("\n", " ")
    parts = [part.strip() for part in cleaned.split(",")]

    return [part for part in parts if part]


def extract_username_sugerido(text: str) -> str | None:
    match = re.search(
        r"USERNAME SUGERIDO:\s*(.+)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    raw_email = match.group(1).strip()
    if not raw_email:
        return None

    return raw_email.split()[0].lower()


def parse_onboarding_email(body: str) -> dict:
    main_body = extract_main_onboarding_block(body)

    user_email = extract_username_sugerido(main_body)

    raw_groups = extract_field_block(
        main_body,
        start_label="GRUPOS:",
        end_label="CLIENTES:",
    )

    raw_clients = extract_field_block(
        main_body,
        start_label="CLIENTES:",
        end_label="-----",
    )

    groups = parse_multiline_comma_list(raw_groups)
    clients = parse_multiline_comma_list(raw_clients)

    return {
        "email": user_email,
        "groups": groups,
        "clients": clients,
        "raw_body": body,
        "main_body": main_body,
    }