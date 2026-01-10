from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional, Dict
import threading
import time

from sqlalchemy import QueuePool, SingletonThreadPool, create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from zowsuplib.settings.conf import settings


# Declarative base for all ORM models
Base = declarative_base()


# Cache thread-safe para account_id por phone
class _AccountIdCache:
    """
    Cache thread-safe para mapear phone -> account_id.
    Reduz queries repetidas ao banco de dados.
    """
    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: Time-to-live do cache em segundos (padrão: 5 minutos)
        """
        self._cache: Dict[str, tuple[int, float]] = {}  # phone -> (account_id, timestamp)
        self._lock = threading.RLock()
        self._ttl = ttl_seconds
    
    def get(self, phone: str) -> Optional[int]:
        """
        Obtém account_id do cache se disponível e válido.
        
        Returns:
            account_id ou None se não estiver no cache ou expirado
        """
        with self._lock:
            if phone not in self._cache:
                return None
            
            account_id, timestamp = self._cache[phone]
            
            # Verifica se expirou
            if time.time() - timestamp > self._ttl:
                del self._cache[phone]
                return None
            
            return account_id
    
    def set(self, phone: str, account_id: int) -> None:
        """
        Armazena account_id no cache.
        """
        with self._lock:
            self._cache[phone] = (account_id, time.time())
    
    def invalidate(self, phone: str) -> None:
        """
        Remove entrada do cache (útil quando account é atualizado).
        """
        with self._lock:
            self._cache.pop(phone, None)
    
    def clear(self) -> None:
        """
        Limpa todo o cache.
        """
        with self._lock:
            self._cache.clear()
    
    def get_many(self, phones: list[str]) -> Dict[str, Optional[int]]:
        """
        Obtém múltiplos account_ids do cache de uma vez.
        
        Returns:
            Dict[phone, account_id] - None para phones não encontrados ou expirados
        """
        result = {}
        now = time.time()
        
        with self._lock:
            for phone in phones:
                if phone not in self._cache:
                    result[phone] = None
                    continue
                
                account_id, timestamp = self._cache[phone]
                
                # Verifica se expirou
                if now - timestamp > self._ttl:
                    del self._cache[phone]
                    result[phone] = None
                else:
                    result[phone] = account_id
        
        return result
    
    def set_many(self, phone_to_id: Dict[str, int]) -> None:
        """
        Armazena múltiplos account_ids no cache de uma vez.
        """
        with self._lock:
            now = time.time()
            for phone, account_id in phone_to_id.items():
                self._cache[phone] = (account_id, now)
    
    def size(self) -> int:
        """Retorna número de entradas no cache."""
        with self._lock:
            return len(self._cache)


# Instância global do cache (singleton)
_account_id_cache = _AccountIdCache(ttl_seconds=300)  # 5 minutos TTL


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
    
    Configurado para suportar concorrência multi-thread com isolamento adequado.
    """
    url = make_url(database_url)
    kwargs = {
        "pool_pre_ping": True,  # Verifica conexões antes de usar
        "pool_reset_on_return": "commit",  # Reseta transações ao retornar ao pool
    }

    if url.get_backend_name() != "sqlite":
        # QueuePool é o padrão e ideal para MySQL com FastAPI e múltiplas threads
        connect_args = {}
        # Para MySQL, configura isolation level para melhor concorrência
        if "mysql" in url.get_backend_name():
            connect_args["isolation_level"] = "READ COMMITTED"
        
        kwargs.update(
            poolclass=QueuePool,  # Explícito para MySQL
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            connect_args=connect_args,
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


# Thread-local storage para sessões
_thread_local = threading.local()


class ThreadLocalSessionManager:
    """
    Gerenciador de sessões thread-safe usando thread-local storage.
    Cada thread tem sua própria sessão isolada, garantindo que operações
    concorrentes não compartilhem a mesma sessão.
    """
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._lock = threading.RLock()
    
    def get_session(self) -> Session:
        """
        Obtém ou cria uma sessão para a thread atual.
        Thread-safe: cada thread tem sua própria sessão isolada.
        
        Returns:
            Session: Sessão isolada para a thread atual
        """
        if not hasattr(_thread_local, 'session') or _thread_local.session is None:
            _thread_local.session = self._session_factory()
            _thread_local.session_refcount = 1
        else:
            # Verifica se a sessão ainda está válida
            try:
                _thread_local.session.execute(text("SELECT 1"))
                _thread_local.session_refcount += 1
            except Exception:
                # Sessão inválida: cria nova
                try:
                    _thread_local.session.close()
                except Exception:
                    pass
                _thread_local.session = self._session_factory()
                _thread_local.session_refcount = 1
        
        return _thread_local.session
    
    def release_session(self):
        """
        Libera a sessão da thread atual.
        Fecha a sessão quando o refcount chega a zero.
        """
        if hasattr(_thread_local, 'session') and _thread_local.session is not None:
            _thread_local.session_refcount -= 1
            if _thread_local.session_refcount <= 0:
                try:
                    _thread_local.session.close()
                except Exception:
                    pass
                finally:
                    _thread_local.session = None
                    _thread_local.session_refcount = 0


# Instância global do gerenciador
_thread_session_manager = ThreadLocalSessionManager(SessionLocal)


def get_thread_local_session() -> Session:
    """
    Obtém uma sessão isolada para a thread atual.
    Cada thread tem sua própria sessão, garantindo isolamento completo.
    
    Returns:
        Session: Sessão isolada para a thread atual
    """
    return _thread_session_manager.get_session()


@contextmanager
def thread_local_session():
    """
    Context manager para sessão thread-local.
    Garante que a sessão seja fechada ao sair do contexto.
    
    Example:
        with thread_local_session() as db:
            account = db.query(models.Account).filter_by(phone="123").first()
            account.is_logged_in = True
            # Commit automático ao sair do with (se não houver exceção)
    """
    session = get_thread_local_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        _thread_session_manager.release_session()


# Lock para operações críticas que precisam de serialização
_critical_operation_lock = threading.RLock()


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


def _get_account_id_cached(db: Session, phone: str, create_if_missing: bool = False) -> Optional[int]:
    """
    Obtém account_id por phone usando cache.
    
    Args:
        db: Sessão do banco de dados
        phone: Número de telefone
        create_if_missing: Se True, cria a conta se não existir
    
    Returns:
        account_id ou None se não existir e create_if_missing=False
    """
    from zowsuplib.app import models
    
    # Verifica cache primeiro
    account_id = _account_id_cache.get(phone)
    if account_id is not None:
        return account_id
    
    # Não está no cache: busca no banco
    if create_if_missing:
        account = db.query(models.Account).filter_by(phone=phone).one_or_none()
        if account is None:
            account = models.Account(phone=phone)
            db.add(account)
            db.flush()
            db.refresh(account)
        
        account_id = account.id
    else:
        account_id = db.query(models.Account.id).filter_by(phone=phone).scalar()
    
    # Armazena no cache se encontrado
    if account_id is not None:
        _account_id_cache.set(phone, account_id)
    
    return account_id


def _get_account_ids_bulk_cached(db: Session, phones: list[str], create_if_missing: bool = False) -> Dict[str, int]:
    """
    Obtém múltiplos account_ids usando cache e bulk query.
    
    Args:
        db: Sessão do banco de dados
        phones: Lista de números de telefone
        create_if_missing: Se True, cria contas que não existem
    
    Returns:
        Dict[phone, account_id] - apenas phones encontrados/criados
    """
    from zowsuplib.app import models
    
    if not phones:
        return {}
    
    # Verifica cache primeiro
    cached_results = _account_id_cache.get_many(phones)
    
    # Separa phones que estão no cache e os que precisam ser buscados
    phones_to_query = [p for p in phones if cached_results.get(p) is None]
    
    if not phones_to_query:
        # Todos estão no cache
        return {p: aid for p, aid in cached_results.items() if aid is not None}
    
    # Busca phones que não estão no cache
    existing_accounts = {
        row.phone: row.id 
        for row in db.query(models.Account.phone, models.Account.id)
                      .filter(models.Account.phone.in_(phones_to_query))
                      .all()
    }
    
    # Cria contas que não existem se solicitado
    if create_if_missing:
        new_phones = [p for p in phones_to_query if p not in existing_accounts]
        if new_phones:
            new_accounts = [models.Account(phone=phone) for phone in new_phones]
            db.add_all(new_accounts)
            db.flush()
            # Atualiza dict com novos IDs
            for acc in new_accounts:
                existing_accounts[acc.phone] = acc.id
    
    # Atualiza cache com resultados
    _account_id_cache.set_many(existing_accounts)
    
    # Combina resultados do cache e do banco
    result = {p: aid for p, aid in cached_results.items() if aid is not None}
    result.update(existing_accounts)
    
    return result


def invalidate_account_cache(phone: str) -> None:
    """
    Invalida entrada do cache para um phone específico.
    Útil quando account é atualizado ou removido.
    """
    _account_id_cache.invalidate(phone)


def clear_account_cache() -> None:
    """
    Limpa todo o cache de accounts.
    Útil para forçar refresh completo.
    """
    _account_id_cache.clear()


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
    
    Usa sessão thread-local para isolamento thread-safe.
    """
    from zowsuplib.app import models

    with thread_local_session() as db:
        # Resolve grupo (campos exatos)
        group_row = (
            db.query(models.Group.id, models.Group.creator_account_id)
            .filter_by(group_jid=group_jid)
            .one_or_none()
        )

        creator_id = None
        if creator_phone:
            # ✅ OTIMIZAÇÃO: Usa cache para creator_phone
            creator_id = _get_account_id_cached(db, creator_phone, create_if_missing=True)

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

        # Adiciona participantes (otimizado com bulk operations)
        unique_phones = [p for p in dict.fromkeys(participants) if p]  # de-dupe preservando ordem
        
        if not unique_phones:
            db.commit()
            return
        
        # ✅ OTIMIZAÇÃO: Usa cache + bulk query para todos os phones de uma vez
        existing_accounts = _get_account_ids_bulk_cached(db, unique_phones, create_if_missing=True)
        
        # Mapeia phones para account_ids (existing_accounts já é um dict phone->id)
        phone_to_account_id = existing_accounts
        account_ids = list(existing_accounts.values())
        
        # ✅ OTIMIZAÇÃO: Bulk query para participantes existentes
        existing_participants = {
            (row.group_id, row.account_id)
            for row in db.query(models.GroupParticipant.group_id, 
                               models.GroupParticipant.account_id)
                          .filter(models.GroupParticipant.group_id == group_id,
                                 models.GroupParticipant.account_id.in_(account_ids))
                          .all()
        }
        
        # Adiciona apenas participantes novos (bulk insert)
        new_participants = []
        for phone in unique_phones:
            acc_id = phone_to_account_id[phone]
            if (group_id, acc_id) not in existing_participants:
                role = "owner" if creator_id and acc_id == creator_id else "member"
                new_participants.append(
                    models.GroupParticipant(
                        group_id=group_id,
                        account_id=acc_id,
                        role=role,
                    )
                )
        
        if new_participants:
            db.add_all(new_participants)
        # Commit automático via context manager


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
    
    Usa sessão thread-local para isolamento thread-safe.
    """
    from zowsuplib.app import models  # noqa: F401

    with thread_local_session() as db:
        # ✅ OTIMIZAÇÃO: Usa cache para obter account_id
        account_id = _get_account_id_cached(db, phone, create_if_missing=True)
        
        if account_id is None:
            # Não deveria acontecer se create_if_missing=True, mas trata edge case
            from loguru import logger
            logger.warning(f"Conta {phone} não pôde ser criada/encontrada")
            return

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
            # ✅ OTIMIZAÇÃO: Invalida cache quando account é atualizado
            invalidate_account_cache(phone)
        # Commit automático via context manager


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
    
    Usa sessão thread-local para isolamento thread-safe.
    """
    from zowsuplib.app import models  # noqa: F401

    with thread_local_session() as db:
        # ✅ OTIMIZAÇÃO: Usa cache para obter account_id
        account_id = _get_account_id_cached(db, phone, create_if_missing=True)

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
        # Commit automático via context manager


def is_account_initialized(phone: str) -> bool:
    """
    Verifica se a conta já foi inicializada.

    Args:
        phone: Número de telefone da conta

    Returns:
        True se a conta já foi inicializada, False caso contrário
    
    Usa sessão thread-local para isolamento thread-safe.
    """
    from zowsuplib.app import models  # noqa: F401

    with thread_local_session() as db:
        # ✅ OTIMIZAÇÃO: Usa cache para obter account_id, depois busca apenas o campo necessário
        account_id = _get_account_id_cached(db, phone, create_if_missing=False)
        if account_id is None:
            return False
        
        value = db.query(models.Account.is_initialized).filter_by(id=account_id).scalar()
        return bool(value)


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
    
    Usa sessão thread-local para isolamento thread-safe.
    """
    from zowsuplib.app import models  # noqa: F401
    from sqlalchemy import func

    with thread_local_session() as db:
        # ✅ OTIMIZAÇÃO: Usa cache para obter account_id
        account_id = _get_account_id_cached(db, phone, create_if_missing=False)
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
    
    with thread_local_session() as db:
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
    
    with thread_local_session() as db:
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


 

