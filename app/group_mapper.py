import re
import unicodedata

from app.config import GOOGLE_WORKSPACE_DOMAIN


GROUP_NAME_EXCEPTIONS = {
    "líderes": "lideres@ampfy.com",
    "lideres": "lideres@ampfy.com",
    "criação": "criacao@ampfy.com",
    "criacao": "criacao@ampfy.com",
}

EXTRA_GROUP_RULES = {
    "colaboradores": ["acessoclientes@ampfy.com"],
    "líderes": ["acessoclientes@ampfy.com"],
    "lideres": ["acessoclientes@ampfy.com"],
}

CLIENT_RULES = {
    "pepsico": ["acessoclientesbakery@bakery.ag"],
}


def normalize_text(value: str) -> str:
    value = value.strip().lower()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))

    value = value.replace(">", "")
    value = value.replace("<", "")
    value = value.replace('"', "")
    value = value.replace("'", "")

    value = re.sub(r"\s+", " ", value).strip()

    return value


def map_single_group(group_name: str, default_domain: str = GOOGLE_WORKSPACE_DOMAIN) -> str:
    normalized = normalize_text(group_name)

    if normalized in GROUP_NAME_EXCEPTIONS:
        return GROUP_NAME_EXCEPTIONS[normalized]

    return f"{normalized}@{default_domain}"


def get_extra_groups_from_group_rules(group_names: list[str]) -> list[str]:
    extra_groups = []

    for group_name in group_names:
        normalized = normalize_text(group_name)
        if normalized in EXTRA_GROUP_RULES:
            extra_groups.extend(EXTRA_GROUP_RULES[normalized])

    return extra_groups


def get_extra_groups_from_client_rules(client_names: list[str]) -> list[str]:
    extra_groups = []

    for client_name in client_names:
        normalized = normalize_text(client_name)
        if normalized in CLIENT_RULES:
            extra_groups.extend(CLIENT_RULES[normalized])

    return extra_groups


def build_final_group_emails(group_names: list[str], client_names: list[str]) -> list[str]:
    mapped_groups = [map_single_group(group_name) for group_name in group_names]

    extra_from_groups = get_extra_groups_from_group_rules(group_names)
    extra_from_clients = get_extra_groups_from_client_rules(client_names)

    final_groups = mapped_groups + extra_from_groups + extra_from_clients

    unique_groups = []
    seen = set()

    for group in final_groups:
        if group not in seen:
            seen.add(group)
            unique_groups.append(group)

    return unique_groups