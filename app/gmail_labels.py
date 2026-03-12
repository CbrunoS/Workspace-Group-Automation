def get_or_create_label(gmail_service, label_name: str) -> str:
    response = gmail_service.users().labels().list(userId="me").execute()
    labels = response.get("labels", [])

    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    created_label = gmail_service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()

    return created_label["id"]


def add_label_to_message(gmail_service, message_id: str, label_id: str) -> None:
    if not label_id:
        return

    gmail_service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]},
    ).execute()


def remove_label_from_message(gmail_service, message_id: str, label_id: str) -> None:
    if not label_id:
        return

    gmail_service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": [label_id]},
    ).execute()