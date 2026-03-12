from googleapiclient.errors import HttpError


def get_user(service, user_email):
    try:
        return service.users().get(userKey=user_email).execute()
    except HttpError as error:
        if error.resp.status == 404:
            return None
        raise


def add_user_to_group(service, user_email, group_email):
    try:
        member = {
            "email": user_email,
            "role": "MEMBER",
        }

        service.members().insert(
            groupKey=group_email,
            body=member,
        ).execute()

        return {
            "status": "success",
            "message": "Usuário adicionado ao grupo",
        }

    except HttpError as error:
        if error.resp.status == 409:
            return {
                "status": "already_member",
                "message": "Usuário já é membro do grupo",
            }

        return {
            "status": "error",
            "message": str(error),
        }