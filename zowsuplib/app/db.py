from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import QueuePool, SingletonThreadPool, create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from zowsuplib.settings.conf import settings


# Declarative base for all ORM models
Base = declarative_base()


def _build_database_url() -> str:
    """
    Builds the SQLAlchemy database URL using Pydantic settings.

    By default this points to a single SQLite database file in the
    project root (zowsup.db), but can be overridden via ZOWSUP_DB_URL.
    """
    return settings.db_url


def _build_engine_kwargs(database_url: str) -> dict:
    """
    Builds engine kwargs with sensible pooling defaults.

    For SQLite we keep the defaults (SingletonThreadPool) to avoid
    breaking the lightweight file‑based workflow. For other backends we
    expand the pool to handle many simultaneous accounts.
    """
    url = make_url(database_url)
    kwargs = {"pool_pre_ping": True}

    if url.get_backend_name() != "sqlite":
        # QueuePool é o padrão e ideal para MySQL com FastAPI e múltiplas threads
        kwargs.update(
            poolclass=QueuePool,  # Explícito para MySQL
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
        )

    if url.get_backend_name() == "sqlite":
        kwargs.update(
            poolclass=QueuePool,
            connect_args={"check_same_thread": False},
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
        )

    return kwargs


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    **_build_engine_kwargs(DATABASE_URL),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Simple context‑like generator to be used in scripts or higher‑level APIs:

        with SessionLocal() as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager para sessões do banco de dados.
    
    Garante commit automático em sucesso, rollback em erro e fechamento da sessão.
    
    Example:
        with get_db_session() as db:
            account = db.query(models.Account).filter_by(phone="123").first()
            account.is_logged_in = True
            # Commit automático ao sair do with (se não houver exceção)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Creates all tables defined on models that inherit from Base.

    Call this once (e.g. from a management script) to create the unified DB schema.
    """
    # Deferred import so models can import Base from here without circular deps.
    from zowsuplib.app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def record_group(
    group_jid: str,
    creator_phone: str | None,
    participants: list[str],
    subject: str | None = None,
) -> None:
    """
    Persiste grupo, criador e participantes no banco.
    - Cria o grupo se não existir.
    - Garante participantes únicos.
    """
    from zowsuplib.app import models

    db = SessionLocal()
    try:
        # Resolve grupo (campos exatos)
        group_row = (
            db.query(models.Group.id, models.Group.creator_account_id)
            .filter_by(group_jid=group_jid)
            .one_or_none()
        )

        creator_id = None
        if creator_phone:
            creator_id = (
                db.query(models.Account.id)
                .filter_by(phone=creator_phone)
                .scalar()
            )

        if group_row is None:
            group = models.Group(
                group_jid=group_jid,
                creator_account_id=creator_id,
                subject=subject,
            )
            db.add(group)
            db.flush()
            group_id = group.id
        else:
            group_id = group_row.id
            if subject is not None:
                db.query(models.Group).filter_by(id=group_id).update(
                    {"subject": subject},
                    synchronize_session=False,
                )
            # Preenche creator_account_id apenas se ainda não existir
            if creator_id and group_row.creator_account_id is None:
                db.query(models.Group).filter_by(id=group_id).update(
                    {"creator_account_id": creator_id},
                    synchronize_session=False,
                )

        # Adiciona participantes
        unique_phones = [p for p in dict.fromkeys(participants) if p]  # de-dupe preservando ordem
        for phone in unique_phones:
            acc_id = db.query(models.Account.id).filter_by(phone=phone).scalar()
            if acc_id is None:
                acc = models.Account(phone=phone)
                db.add(acc)
                db.flush()
                acc_id = acc.id

            exists_id = (
                db.query(models.GroupParticipant.id)
                .filter_by(group_id=group_id, account_id=acc_id)
                .scalar()
            )
            if exists_id is None:
                db.add(
                    models.GroupParticipant(
                        group_id=group_id,
                        account_id=acc_id,
                        role="owner" if creator_id and acc_id == creator_id else "member",
                    )
                )

        db.commit()
    except Exception as exc:
        db.rollback()
        from loguru import logger

        logger.error(f"Erro ao registrar grupo {group_jid}: {exc}")
    finally:
        db.close()


def update_account_status(
    phone: str,
    *,
    is_logged_in: Optional[bool] = None,
    has_restriction: Optional[bool] = None,
    is_initialized: Optional[bool] = None,
    env: Optional[str] = None,
) -> None:
    """
    Atualiza o status da conta no banco de dados.

    Args:
        phone: Número de telefone da conta
        is_logged_in: Se a conta está logada (None para não atualizar)
        has_restriction: Se a conta possui restrição (None para não atualizar)
        is_initialized: Se a conta já foi inicializada (None para não atualizar)
        env: Tipo de ambiente (android, smb_android, ios, smb_ios) (None para não atualizar)
    """
    from zowsuplib.app import models  # noqa: F401

    db = SessionLocal()
    try:
        account_id = db.query(models.Account.id).filter_by(phone=phone).scalar()
        if account_id is None:
            # Cria a conta se não existir
            account = models.Account(phone=phone)
            db.add(account)
            db.flush()
            account_id = account.id

        updates = {}
        if is_logged_in is not None:
            updates["is_logged_in"] = is_logged_in
        if has_restriction is not None:
            updates["has_restriction"] = has_restriction
        if is_initialized is not None:
            updates["is_initialized"] = is_initialized
        if env is not None:
            updates["env"] = env

        if updates:
            db.query(models.Account).filter_by(id=account_id).update(updates, synchronize_session=False)

        db.commit()
    except Exception as e:
        db.rollback()
        from loguru import logger
        logger.error(f"Erro ao atualizar status da conta {phone}: {e}")
    finally:
        db.close()


def register_sent_message(
    phone: str,
    msg_id: str,
    recipient: str,
    *,
    message_type: Optional[str] = None,
    status: str = "EXECUTED",
    error_code: Optional[str] = None,
) -> None:
    """
    Registra uma mensagem enviada no banco de dados.

    Args:
        phone: Número de telefone da conta que enviou
        msg_id: ID único da mensagem
        recipient: JID do destinatário (número ou grupo)
        message_type: Tipo da mensagem (TEXT, IMAGE, VIDEO, etc.)
        status: Status da mensagem (EXECUTED, SENT, ERROR)
        error_code: Código de erro, se houver
    """
    from zowsuplib.app import models  # noqa: F401

    db = SessionLocal()
    try:
        account_id = db.query(models.Account.id).filter_by(phone=phone).scalar()
        if account_id is None:
            account = models.Account(phone=phone)
            db.add(account)
            db.flush()
            account_id = account.id

        # Verifica se a mensagem já foi registrada (evita duplicatas)
        existing_id = (
            db.query(models.SentMessage.id)
            .filter_by(account_id=account_id, msg_id=msg_id)
            .scalar()
        )

        if existing_id is None:
            sent_message = models.SentMessage(
                account_id=account_id,
                msg_id=msg_id,
                recipient=recipient,
                message_type=message_type,
                status=status,
                error_code=error_code,
            )
            db.add(sent_message)
        else:
            # Atualiza o status se a mensagem já existir
            updates = {"status": status}
            if error_code is not None:
                updates["error_code"] = error_code
            db.query(models.SentMessage).filter_by(id=existing_id).update(updates, synchronize_session=False)

        db.commit()
    except Exception as e:
        db.rollback()
        from loguru import logger
        logger.error(f"Erro ao registrar mensagem enviada {msg_id} da conta {phone}: {e}")
    finally:
        db.close()


def is_account_initialized(phone: str) -> bool:
    """
    Verifica se a conta já foi inicializada.

    Args:
        phone: Número de telefone da conta

    Returns:
        True se a conta já foi inicializada, False caso contrário
    """
    from zowsuplib.app import models  # noqa: F401

    db = SessionLocal()
    try:
        value = db.query(models.Account.is_initialized).filter_by(phone=phone).scalar()
        return bool(value)
    except Exception as e:
        from loguru import logger
        logger.error(f"Erro ao verificar status de inicialização da conta {phone}: {e}")
        return False
    finally:
        db.close()


def get_sent_messages_count(
    phone: str,
    *,
    recipient: Optional[str] = None,
    message_type: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """
    Conta quantas mensagens uma conta enviou, opcionalmente filtradas por destinatário.

    Args:
        phone: Número de telefone da conta
        recipient: Filtro opcional por destinatário (None para contar todas)
        message_type: Filtro opcional por tipo de mensagem
        status: Filtro opcional por status (EXECUTED, SENT, ERROR)

    Returns:
        Dicionário com:
        - total: Total de mensagens enviadas
        - by_recipient: Lista de dicionários com {recipient, count} para cada destinatário
    """
    from zowsuplib.app import models  # noqa: F401
    from sqlalchemy import func

    db = SessionLocal()
    try:
        account_id = db.query(models.Account.id).filter_by(phone=phone).scalar()
        if account_id is None:
            return {"total": 0, "by_recipient": []}

        # Query base
        query = db.query(models.SentMessage).filter_by(account_id=account_id)

        # Aplicar filtros opcionais
        if recipient is not None:
            query = query.filter_by(recipient=recipient)
        if message_type is not None:
            query = query.filter_by(message_type=message_type)
        if status is not None:
            query = query.filter_by(status=status)

        # Conta total
        total = query.count()

        # Conta por destinatário
        by_recipient_query = (
            db.query(
                models.SentMessage.recipient,
                func.count(models.SentMessage.id).label("count"),
            )
            .filter_by(account_id=account_id)
        )

        if message_type is not None:
            by_recipient_query = by_recipient_query.filter_by(message_type=message_type)
        if status is not None:
            by_recipient_query = by_recipient_query.filter_by(status=status)

        by_recipient_query = by_recipient_query.group_by(models.SentMessage.recipient)
        by_recipient_results = by_recipient_query.all()

        by_recipient = [
            {"recipient": row.recipient, "count": row.count}
            for row in by_recipient_results
        ]

        # Ordena por count decrescente
        by_recipient.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total": total,
            "by_recipient": by_recipient,
        }
    except Exception as e:
        from loguru import logger
        logger.error(f"Erro ao contar mensagens enviadas da conta {phone}: {e}")
        return {"total": 0, "by_recipient": []}
    finally:
        db.close()


def export_contacts_to_vcard(
    output_file: Optional[str] = None,
    include_groups: bool = False,
) -> str:
    """
    Exporta todos os contatos de uma conta para formato vCard.
    
    Args:
        phone: Número de telefone da conta
        output_file: Caminho do arquivo de saída (opcional). Se None, retorna apenas a string.
        include_groups: Se True, inclui grupos na exportação (padrão: False)
    
    Returns:
        String com o conteúdo vCard ou caminho do arquivo se output_file foi fornecido
    
    Example:
        # Exportar para string
        vcard_content = export_contacts_to_vcard("5511999999999")
        
        # Exportar para arquivo
        export_contacts_to_vcard("5511999999999", output_file="contacts.vcf")
    """
    from zowsuplib.app import models
    from loguru import logger
    from datetime import datetime
    
    db = SessionLocal()
    try:
        # Busca todos os contatos da conta
        contacts = (
            db.query(models.Account.phone, models.Account.pushname)
            .order_by(models.Account.id.asc())
            .all()
        )
        
        if not contacts:
            logger.warning(f"Nenhum contato encontrado")
            return ""
        
        logger.info(f"Exportando {len(contacts)} contatos para vCard...")
        
        vcard_lines = []

        
        for phone, pushname in contacts:
            jid = phone
            
            # Ignora grupos se include_groups=False
            if not include_groups and ("@g.us" in jid or "broadcast" in jid):
                continue
            
            # Extrai o número de telefone do JID
            phone_number = jid.split('@')[0]
            
            # Remove prefixos de dispositivo se presente (formato: phone:device)
            if ':' in phone_number:
                phone_number = phone_number.split(':')[0]
            
            # Obtém o nome (pushname ou nome salvo)
            display_name = pushname if pushname and pushname.strip() else phone_number
            
            # Gera vCard para este contato
            vcard_lines.append("BEGIN:VCARD")
            vcard_lines.append("VERSION:3.0")
            vcard_lines.append(f"FN:{_escape_vcard_field(display_name)}")
            
            # Adiciona telefone apenas se não for grupo
            if "@g.us" not in jid and "broadcast" not in jid:
                # Formata o número (remove caracteres não numéricos exceto +)
                formatted_phone = phone_number
                if not formatted_phone.startswith('+'):
                    # Tenta adicionar + se não tiver
                    formatted_phone = f"+{formatted_phone}"
                
                vcard_lines.append(f"TEL;TYPE=CELL:{formatted_phone}")
            
            
            vcard_lines.append("END:VCARD")
            vcard_lines.append("")
        
        vcard_content = "\n".join(vcard_lines)
        
        # Se output_file foi fornecido, salva no arquivo
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(vcard_content)
                logger.info(f"Contatos exportados para {output_file}")
                return output_file
            except Exception as e:
                logger.error(f"Erro ao salvar arquivo vCard: {e}")
                raise
        
        return vcard_content
        
    except Exception as e:
        logger.error(f"Erro ao exportar contatos para vCard: {e}", exc_info=True)
        raise
    finally:
        db.close()


def _escape_vcard_field(value: str) -> str:
    """
    Escapa caracteres especiais em campos vCard conforme RFC 2426.
    
    Args:
        value: Valor a ser escapado
    
    Returns:
        Valor escapado
    """
    if not value:
        return ""
    
    # Substitui caracteres que precisam ser escapados
    value = value.replace("\\", "\\\\")
    value = value.replace(",", "\\,")
    value = value.replace(";", "\\;")
    value = value.replace("\n", "\\n")
    value = value.replace("\r", "\\r")
    
    return value


def get_all_imported_accounts(
    *,
    only_initialized: bool = False,
    only_active: bool = False,
    without_restriction: bool = False,
) -> list[dict]:
    """
    Carrega todas as contas importadas do banco de dados.
    
    Args:
        only_initialized: Se True, retorna apenas contas inicializadas
        only_active: Se True, retorna apenas contas logadas (is_logged_in=True)
        without_restriction: Se True, retorna apenas contas sem restrição
    
    Returns:
        Lista de dicionários com informações das contas:
        [
            {
                "phone": "5511999999999",
                "pushname": "Nome da Conta",
                "env": "smb_android",
                "is_logged_in": True,
                "has_restriction": False,
                "is_initialized": True,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00"
            },
            ...
        ]
    
    Example:
        # Carregar todas as contas
        accounts = get_all_imported_accounts()
        
        # Apenas contas inicializadas
        accounts = get_all_imported_accounts(only_initialized=True)
        
        # Apenas contas ativas sem restrição
        accounts = get_all_imported_accounts(only_active=True, without_restriction=True)
    """
    from zowsuplib.app import models
    from loguru import logger
    
    db = SessionLocal()
    try:
        # Query base (campos exatos)
        query = db.query(
            models.Account.phone,
            models.Account.pushname,
            models.Account.env,
            models.Account.is_logged_in,
            models.Account.has_restriction,
            models.Account.is_initialized,
            models.Account.created_at,
            models.Account.updated_at,
        )
        
        # Aplica filtros
        if only_initialized:
            query = query.filter(models.Account.is_initialized == True)
        
        if only_active:
            query = query.filter(models.Account.is_logged_in == True)
        
        if without_restriction:
            query = query.filter(models.Account.has_restriction == False)
        
        # Ordena por data de criação (mais recentes primeiro)
        rows = query.order_by(models.Account.created_at.desc()).all()
        
        # Converte para lista de dicionários
        result = []
        for (
            phone,
            pushname,
            env_val,
            is_logged_in,
            has_restriction,
            is_initialized,
            created_at,
            updated_at,
        ) in rows:
            result.append(
                {
                    "phone": phone,
                    "pushname": pushname,
                    "env": env_val,
                    "is_logged_in": is_logged_in,
                    "has_restriction": has_restriction,
                    "is_initialized": is_initialized,
                    "created_at": created_at.isoformat() if created_at else None,
                    "updated_at": updated_at.isoformat() if updated_at else None,
                }
            )
        
        logger.info(f"Carregadas {len(result)} contas do banco de dados")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao carregar contas do banco de dados: {e}", exc_info=True)
        return []
    finally:
        db.close()


 

