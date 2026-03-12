from datetime import datetime, timedelta

from app.config import (
    GMAIL_LABEL_DONE,
    GMAIL_LABEL_IGNORED,
    GMAIL_LABEL_PENDING,
    LOCK_FILE,
    ONBOARDING_HISTORY_FILE,
    PENDING_ONBOARDINGS_FILE,
)
from app.gmail_labels import (
    add_label_to_message,
    get_or_create_label,
    remove_label_from_message,
)
from app.gmail_reader import (
    get_message_body,
    list_onboarding_messages,
    parse_onboarding_email,
)
from app.google_client import (
    get_directory_service,
    get_gmail_service,
)
from app.group_mapper import build_final_group_emails
from app.group_service import (
    add_user_to_group,
    get_user,
)
from app.history_service import append_history_record
from app.logger import get_logger
from app.onboarding_queue import (
    add_onboarding_to_queue,
    get_pending_records,
    update_record_status,
)

from app.lock_service import acquire_lock, release_lock


MAX_ATTEMPTS = 500
RETRY_INTERVAL_HOURS = 2


def should_wait_for_retry(created_at, attempts: int):
    if not created_at or str(created_at).strip().lower() in ["", "nan", "none"]:
        return False, None

    try:
        created_time = datetime.fromisoformat(str(created_at))
    except ValueError:
        return False, None

    next_retry_time = created_time + timedelta(
        hours=attempts * RETRY_INTERVAL_HOURS
    )

    if datetime.now() < next_retry_time:
        return True, next_retry_time

    return False, next_retry_time


def collect_onboardings(gmail_service, pending_label_id, ignored_label_id, logger):
    logger.info("Buscando emails de onboarding...")

    messages = list_onboarding_messages(gmail_service)

    if not messages:
        logger.info("Nenhum email de onboarding encontrado.")
        return

    logger.info(f"Emails encontrados: {len(messages)}")

    for msg in messages:
        message_id = msg["id"]
        body = get_message_body(gmail_service, message_id)
        parsed = parse_onboarding_email(body)

        logger.info(
            f"Parse do email | message_id={message_id} | "
            f"email={parsed['email']} | groups={parsed['groups']} | "
            f"clients={parsed['clients']}"
        )

        if not parsed["email"]:
            logger.warning(
                f"Email ignorado por não conter USERNAME SUGERIDO. "
                f"Message ID: {message_id}"
            )

            add_label_to_message(gmail_service, message_id, ignored_label_id)

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email="",
                group="",
                status="ignored_missing_username",
                message="Email ignorado por não conter USERNAME SUGERIDO",
            )
            continue

        final_groups = build_final_group_emails(
            parsed["groups"],
            parsed["clients"],
        )

        if not final_groups:
            logger.warning(
                f"Email ignorado por não conter grupos válidos. "
                f"email={parsed['email']} | message_id={message_id}"
            )

            add_label_to_message(gmail_service, message_id, ignored_label_id)

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=parsed["email"],
                group="",
                status="ignored_missing_groups",
                message="Email ignorado por não conter grupos válidos",
            )
            continue

        was_added = add_onboarding_to_queue(
            queue_file=PENDING_ONBOARDINGS_FILE,
            message_id=message_id,
            email=parsed["email"],
            groups=final_groups,
        )

        if was_added:
            add_label_to_message(gmail_service, message_id, pending_label_id)

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=parsed["email"],
                group="",
                status="queued",
                message=f"Onboarding adicionado na fila com grupos: {', '.join(final_groups)}",
            )

            logger.info(
                f"Onboarding adicionado na fila | "
                f"email={parsed['email']} | grupos={final_groups}"
            )
        else:
            logger.info(
                f"Onboarding já existente na fila ou já concluído | "
                f"email={parsed['email']} | message_id={message_id}"
            )


def process_pending_onboardings(
    gmail_service,
    directory_service,
    pending_label_id,
    done_label_id,
    ignored_label_id,
    logger,
):
    logger.info("Processando onboardings pendentes...")

    records = get_pending_records(PENDING_ONBOARDINGS_FILE)
    logger.info(f"Pendentes encontrados: {len(records)}")

    for record in records:
        message_id = str(record["message_id"])
        user_email = str(record["email"]).strip().lower()
        raw_groups = record.get("groups", "")
        groups = [group.strip() for group in str(raw_groups).split(";") if group.strip()]

        attempts_raw = record.get("attempts", 0)
        attempts = 0 if str(attempts_raw).strip().lower() in ["", "nan", "none"] else int(attempts_raw)

        created_at = record.get("created_at")

        if attempts >= MAX_ATTEMPTS:
            logger.warning(
                f"Limite de tentativas atingido para {user_email}. "
                f"Marcando como failed_timeout."
            )

            update_record_status(
                queue_file=PENDING_ONBOARDINGS_FILE,
                message_id=message_id,
                status="failed_timeout",
                attempts=attempts,
                processed_at=datetime.now().isoformat(),
            )

            remove_label_from_message(gmail_service, message_id, pending_label_id)
            add_label_to_message(gmail_service, message_id, ignored_label_id)

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=user_email,
                group="",
                status="failed_timeout",
                message="Limite de tentativas atingido sem encontrar o usuário",
            )
            continue

        if not groups:
            logger.warning(f"Registro sem grupos válidos. message_id={message_id}")

            update_record_status(
                queue_file=PENDING_ONBOARDINGS_FILE,
                message_id=message_id,
                status="invalid",
                attempts=attempts + 1,
                processed_at=datetime.now().isoformat(),
            )

            remove_label_from_message(gmail_service, message_id, pending_label_id)
            add_label_to_message(gmail_service, message_id, ignored_label_id)

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=user_email,
                group="",
                status="invalid",
                message="Registro sem grupos válidos",
            )
            continue

        must_wait, next_retry_time = should_wait_for_retry(created_at, attempts)
        if must_wait:
            logger.info(
                f"Aguardando próximo retry para {user_email}. "
                f"Próxima tentativa após {next_retry_time.isoformat()}"
            )
            continue

        user = get_user(directory_service, user_email)
        if not user:
            logger.info(f"Usuário ainda não existe: {user_email}")

            update_record_status(
                queue_file=PENDING_ONBOARDINGS_FILE,
                message_id=message_id,
                status="pending",
                attempts=attempts + 1,
            )

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=user_email,
                group="",
                status="user_not_found_yet",
                message="Usuário ainda não existe no Google Workspace",
            )
            continue

        all_groups_processed = True

        for group in groups:
            result = add_user_to_group(
                directory_service,
                user_email,
                group,
            )

            logger.info(
                f"Usuário: {user_email} | Grupo: {group} | Status: {result['status']}"
            )

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=user_email,
                group=group,
                status=result["status"],
                message=result["message"],
            )

            if result["status"] not in ["success", "already_member"]:
                all_groups_processed = False

        if all_groups_processed:
            update_record_status(
                queue_file=PENDING_ONBOARDINGS_FILE,
                message_id=message_id,
                status="done",
                attempts=attempts + 1,
                processed_at=datetime.now().isoformat(),
            )

            remove_label_from_message(gmail_service, message_id, pending_label_id)
            add_label_to_message(gmail_service, message_id, done_label_id)

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=user_email,
                group="",
                status="done",
                message="Onboarding concluído com sucesso",
            )

            logger.info(f"Onboarding concluído: {user_email}")
        else:
            update_record_status(
                queue_file=PENDING_ONBOARDINGS_FILE,
                message_id=message_id,
                status="pending",
                attempts=attempts + 1,
            )

            append_history_record(
                history_file=ONBOARDING_HISTORY_FILE,
                message_id=message_id,
                email=user_email,
                group="",
                status="partial_failure",
                message="Falha parcial ao adicionar usuário em um ou mais grupos",
            )


def main():
    logger = get_logger()

    if not acquire_lock(LOCK_FILE):
        logger.warning("Outra execução já está em andamento. Encerrando...")
        return

    try:
        logger.info("===== EXECUÇÃO AUTOMÁTICA DO CRON =====")
        logger.info("Iniciando automação de onboarding por email...")

        gmail_service = get_gmail_service()
        directory_service = get_directory_service()

        pending_label_id = get_or_create_label(gmail_service, GMAIL_LABEL_PENDING)
        done_label_id = get_or_create_label(gmail_service, GMAIL_LABEL_DONE)
        ignored_label_id = get_or_create_label(gmail_service, GMAIL_LABEL_IGNORED)

        collect_onboardings(
            gmail_service,
            pending_label_id,
            ignored_label_id,
            logger,
        )

        process_pending_onboardings(
            gmail_service,
            directory_service,
            pending_label_id,
            done_label_id,
            ignored_label_id,
            logger,
        )
    finally:
        release_lock(LOCK_FILE)


if __name__ == "__main__":
    main()