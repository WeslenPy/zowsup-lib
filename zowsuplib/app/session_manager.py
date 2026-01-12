"""
Gerenciador de ciclo de vida de sessões de banco de dados.

Gerencia sessões thread-local com isolamento por conta, timeout automático,
cleanup em background e observabilidade completa.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from contextlib import contextmanager
from sqlalchemy.orm import Session
from loguru import logger

from zowsuplib.app.db import SessionLocal, get_thread_local_session, _thread_session_manager
from zowsuplib.app.session_metrics import get_session_metrics


@dataclass
class SessionMetadata:
    """Metadata de uma sessão de banco de dados."""
    session: Session
    account_id: Optional[str]
    thread_id: int
    created_at: float
    last_activity: float = field(default_factory=time.time)
    transaction_start: Optional[float] = None
    is_expired: bool = False
    error_count: int = 0


class AccountSessionRegistry:
    """
    Registry de sessões por conta.
    
    Mantém registro de todas as sessões ativas por account_id,
    permitindo fechar todas as sessões de uma conta específica.
    """
    
    def __init__(self):
        self._sessions_by_account: Dict[str, Set[Session]] = {}
        self._lock = threading.RLock()
    
    def register_session(self, account_id: str, session: Session) -> None:
        """
        Registra uma sessão para uma conta.
        
        Args:
            account_id: ID da conta (phone number)
            session: Sessão a ser registrada
        """
        with self._lock:
            if account_id not in self._sessions_by_account:
                self._sessions_by_account[account_id] = set()
            self._sessions_by_account[account_id].add(session)
            logger.debug(f"[SESSION] Sessão registrada para conta {account_id} | total_sessions={len(self._sessions_by_account[account_id])}")
    
    def unregister_session(self, account_id: str, session: Session) -> None:
        """
        Remove registro de uma sessão de uma conta.
        
        Args:
            account_id: ID da conta
            session: Sessão a ser removida
        """
        with self._lock:
            if account_id in self._sessions_by_account:
                self._sessions_by_account[account_id].discard(session)
                if not self._sessions_by_account[account_id]:
                    del self._sessions_by_account[account_id]
                logger.debug(f"[SESSION] Sessão removida do registro para conta {account_id}")
    
    def get_sessions_for_account(self, account_id: str) -> List[Session]:
        """
        Obtém todas as sessões ativas de uma conta.
        
        Args:
            account_id: ID da conta
            
        Returns:
            Lista de sessões ativas da conta
        """
        with self._lock:
            return list(self._sessions_by_account.get(account_id, set()))
    
    def close_all_for_account(self, account_id: str) -> int:
        """
        Fecha todas as sessões de uma conta específica.
        
        Args:
            account_id: ID da conta
            
        Returns:
            Número de sessões fechadas
        """
        with self._lock:
            sessions = self._sessions_by_account.get(account_id, set()).copy()
            closed_count = 0
            
            for session in sessions:
                try:
                    if session.is_active:
                        session.rollback()
                    session.close()
                    closed_count += 1
                    logger.info(f"[SESSION] Sessão fechada para conta {account_id}")
                except Exception as e:
                    logger.error(f"[SESSION] Erro ao fechar sessão para conta {account_id}: {e}")
            
            if account_id in self._sessions_by_account:
                del self._sessions_by_account[account_id]
            
            if closed_count > 0:
                logger.info(f"[SESSION] {closed_count} sessões fechadas para conta {account_id}")
            
            return closed_count
    
    def get_all_account_ids(self) -> List[str]:
        """Retorna lista de todas as contas com sessões ativas."""
        with self._lock:
            return list(self._sessions_by_account.keys())
    
    def get_total_sessions(self) -> int:
        """Retorna total de sessões registradas."""
        with self._lock:
            return sum(len(sessions) for sessions in self._sessions_by_account.values())


class SessionLifecycleManager:
    """
    Gerenciador de ciclo de vida de sessões de banco de dados.
    
    Gerencia sessões thread-local com isolamento por conta, timeout automático
    e observabilidade completa.
    """
    
    def __init__(self, timeout_seconds: int = 300):
        """
        Inicializa o gerenciador de sessões.
        
        Args:
            timeout_seconds: Timeout em segundos para sessões inativas (padrão: 5 minutos)
        """
        self._timeout = timeout_seconds
        self._sessions_by_thread: Dict[int, SessionMetadata] = {}
        self._sessions_by_account: Dict[str, List[SessionMetadata]] = {}
        self._registry = AccountSessionRegistry()
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        self._started = False
        self._metrics = get_session_metrics()
        
        logger.info(f"[SESSION] SessionLifecycleManager inicializado | timeout={timeout_seconds}s")
    
    def start_cleanup_thread(self) -> None:
        """Inicia a thread de cleanup em background."""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            logger.warning("[SESSION] Cleanup thread já está rodando")
            return
        
        self._stop_cleanup.clear()
        self._cleanup_thread = SessionCleanupThread(self, self._stop_cleanup)
        self._cleanup_thread.daemon = True
        self._cleanup_thread.start()
        self._started = True
        logger.info("[SESSION] Cleanup thread iniciada")
    
    def stop_cleanup_thread(self) -> None:
        """Para a thread de cleanup."""
        if self._cleanup_thread is None:
            return
        
        self._stop_cleanup.set()
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        self._started = False
        logger.info("[SESSION] Cleanup thread parada")
    
    def get_or_create_session(
        self,
        account_id: Optional[str] = None,
        auto_commit: bool = True
    ) -> Session:
        """
        Obtém ou cria uma sessão thread-local.
        
        Args:
            account_id: ID da conta (opcional, para registro)
            auto_commit: Se True, commit automático ao fechar (via context manager)
            
        Returns:
            Session: Sessão thread-local
        """
        thread_id = threading.current_thread().ident
        
        with self._lock:
            # Obtém sessão thread-local existente ou cria nova
            session = get_thread_local_session()
            
            # Verifica se já temos metadata para esta sessão
            if thread_id not in self._sessions_by_thread:
                # Nova sessão: cria metadata
                metadata = SessionMetadata(
                    session=session,
                    account_id=account_id,
                    thread_id=thread_id,
                    created_at=time.time()
                )
                self._sessions_by_thread[thread_id] = metadata
                
                # Registra por conta se account_id fornecido
                if account_id:
                    if account_id not in self._sessions_by_account:
                        self._sessions_by_account[account_id] = []
                    self._sessions_by_account[account_id].append(metadata)
                    self._registry.register_session(account_id, session)
                
                logger.info(
                    f"[SESSION] Nova sessão criada | account={account_id or 'N/A'} "
                    f"thread_id={thread_id} session_id={id(session)}"
                )
                self._metrics.record_session_created(account_id)
            else:
                # Sessão existente: atualiza metadata
                metadata = self._sessions_by_thread[thread_id]
                metadata.last_activity = time.time()
                
                # Atualiza account_id se fornecido e diferente
                if account_id and metadata.account_id != account_id:
                    # Remove do registro antigo
                    if metadata.account_id:
                        old_sessions = self._sessions_by_account.get(metadata.account_id, [])
                        if metadata in old_sessions:
                            old_sessions.remove(metadata)
                            self._registry.unregister_session(metadata.account_id, session)
                    
                    # Adiciona ao novo registro
                    metadata.account_id = account_id
                    if account_id not in self._sessions_by_account:
                        self._sessions_by_account[account_id] = []
                    self._sessions_by_account[account_id].append(metadata)
                    self._registry.register_session(account_id, session)
            
            return session
    
    def update_activity(self, session: Session) -> None:
        """
        Atualiza timestamp de última atividade de uma sessão.
        
        Args:
            session: Sessão a atualizar
        """
        thread_id = threading.current_thread().ident
        with self._lock:
            if thread_id in self._sessions_by_thread:
                metadata = self._sessions_by_thread[thread_id]
                if metadata.session is session:
                    metadata.last_activity = time.time()
                    metadata.is_expired = False
    
    def close_session(self, session: Session, account_id: Optional[str] = None) -> bool:
        """
        Fecha uma sessão específica.
        
        Args:
            session: Sessão a fechar
            account_id: ID da conta (opcional, para limpeza de registro)
            
        Returns:
            True se a sessão foi fechada, False se não encontrada
        """
        thread_id = threading.current_thread().ident
        
        with self._lock:
            # Remove metadata
            if thread_id in self._sessions_by_thread:
                metadata = self._sessions_by_thread[thread_id]
                if metadata.session is session:
                    account_id = account_id or metadata.account_id
                    
                    # Remove de registros
                    if account_id:
                        if account_id in self._sessions_by_account:
                            if metadata in self._sessions_by_account[account_id]:
                                self._sessions_by_account[account_id].remove(metadata)
                                if not self._sessions_by_account[account_id]:
                                    del self._sessions_by_account[account_id]
                        self._registry.unregister_session(account_id, session)
                    
                    del self._sessions_by_thread[thread_id]
            
            # Fecha sessão
            try:
                if session.is_active:
                    session.rollback()
                session.close()
                logger.info(f"[SESSION] Sessão fechada | account={account_id or 'N/A'} thread_id={thread_id}")
                self._metrics.record_session_closed(account_id)
                return True
            except Exception as e:
                logger.error(f"[SESSION] Erro ao fechar sessão: {e}")
                return False
    
    def close_all_for_account(self, account_id: str) -> int:
        """
        Fecha todas as sessões de uma conta específica.
        
        IMPORTANTE: Não fecha sessões que estão ativas (em uso por outras threads)
        para evitar travamentos e erros.
        
        Args:
            account_id: ID da conta
            
        Returns:
            Número de sessões fechadas
        """
        current_thread_id = threading.current_thread().ident
        sessions_to_close = []
        
        # Coleta sessões para fechar (dentro do lock, mas não fecha ainda)
        with self._lock:
            sessions_to_close = self._sessions_by_account.get(account_id, []).copy()
            
            # Remove metadatas dos registros ANTES de fechar (evita race condition)
            for metadata in sessions_to_close:
                thread_id = metadata.thread_id
                
                # Remove de registros
                if thread_id in self._sessions_by_thread:
                    del self._sessions_by_thread[thread_id]
            
            # Limpa registros
            if account_id in self._sessions_by_account:
                del self._sessions_by_account[account_id]
        
        # Fecha sessões FORA do lock para evitar deadlock
        # E não fecha sessões que estão em uso pela thread atual
        closed_count = 0
        for metadata in sessions_to_close:
            try:
                session = metadata.session
                thread_id = metadata.thread_id
                
                # Não fecha sessão se está sendo usada pela thread atual
                if thread_id == current_thread_id:
                    logger.warning(
                        f"[SESSION] Pulando fechamento de sessão em uso pela thread atual | "
                        f"account={account_id} thread_id={thread_id}"
                    )
                    continue
                
                # Verifica se sessão ainda está válida antes de fechar
                try:
                    if session.is_active:
                        session.rollback()
                    session.close()
                    closed_count += 1
                    logger.info(f"[SESSION] Sessão fechada para conta {account_id} | thread_id={thread_id}")
                    self._metrics.record_session_closed(account_id)
                except Exception as close_error:
                    # Sessão pode já ter sido fechada ou estar em uso
                    logger.debug(
                        f"[SESSION] Sessão já estava fechada ou em uso | "
                        f"account={account_id} thread_id={thread_id} error={close_error}"
                    )
            except Exception as e:
                logger.error(f"[SESSION] Erro ao fechar sessão para conta {account_id}: {e}")
        
        # Usa registry também (fora do lock principal)
        try:
            registry_closed = self._registry.close_all_for_account(account_id)
        except Exception as e:
            logger.warning(f"[SESSION] Erro ao fechar sessões do registry para conta {account_id}: {e}")
            registry_closed = 0
        
        total_closed = closed_count + registry_closed
        if total_closed > 0:
            logger.info(f"[SESSION] {total_closed} sessões fechadas para conta {account_id}")
        
        return total_closed
    
    def close_all_for_thread(self, thread_id: int) -> int:
        """
        Fecha todas as sessões de uma thread específica.
        
        Args:
            thread_id: ID da thread
            
        Returns:
            Número de sessões fechadas
        """
        with self._lock:
            if thread_id not in self._sessions_by_thread:
                return 0
            
            metadata = self._sessions_by_thread[thread_id]
            session = metadata.session
            account_id = metadata.account_id
            
            # Remove de registros
            if account_id:
                if account_id in self._sessions_by_account:
                    if metadata in self._sessions_by_account[account_id]:
                        self._sessions_by_account[account_id].remove(metadata)
                        if not self._sessions_by_account[account_id]:
                            del self._sessions_by_account[account_id]
                self._registry.unregister_session(account_id, session)
            
            del self._sessions_by_thread[thread_id]
            
            # Fecha sessão
            try:
                if session.is_active:
                    session.rollback()
                session.close()
                logger.info(f"[SESSION] Sessão fechada para thread {thread_id} | account={account_id or 'N/A'}")
                return 1
            except Exception as e:
                logger.error(f"[SESSION] Erro ao fechar sessão para thread {thread_id}: {e}")
                return 0
    
    def get_expired_sessions(self, timeout_seconds: Optional[int] = None) -> List[SessionMetadata]:
        """
        Identifica sessões expiradas (sem atividade há mais de timeout).
        
        Args:
            timeout_seconds: Timeout em segundos (None para usar o padrão)
            
        Returns:
            Lista de metadata de sessões expiradas
        """
        timeout = timeout_seconds or self._timeout
        now = time.time()
        expired = []
        
        with self._lock:
            for metadata in self._sessions_by_thread.values():
                if (now - metadata.last_activity) > timeout:
                    metadata.is_expired = True
                    expired.append(metadata)
        
        return expired
    
    def cleanup_expired_sessions(self) -> int:
        """
        Fecha todas as sessões expiradas.
        
        IMPORTANTE: Não fecha sessões que estão ativas (em uso por outras threads)
        para evitar travamentos.
        
        Returns:
            Número de sessões fechadas
        """
        expired = self.get_expired_sessions()
        closed_count = 0
        current_thread_id = threading.current_thread().ident
        
        for metadata in expired:
            account_id = metadata.account_id
            session = metadata.session
            thread_id = metadata.thread_id
            
            # Não fecha sessão se está sendo usada pela thread atual
            if thread_id == current_thread_id:
                logger.debug(
                    f"[SESSION] Pulando cleanup de sessão em uso pela thread atual | "
                    f"account={account_id or 'N/A'} thread_id={thread_id}"
                )
                continue
            
            # Verifica se a sessão ainda está expirada antes de fechar
            # (pode ter sido atualizada desde que foi marcada como expirada)
            now = time.time()
            if (now - metadata.last_activity) <= self._timeout:
                # Sessão foi atualizada, não está mais expirada
                logger.debug(
                    f"[SESSION] Sessão não está mais expirada, pulando cleanup | "
                    f"account={account_id or 'N/A'} thread_id={thread_id}"
                )
                continue
            
            if self.close_session(session, account_id):
                closed_count += 1
                logger.warning(
                    f"[SESSION] Sessão expirada fechada | account={account_id or 'N/A'} "
                    f"thread_id={thread_id} idle_time={now - metadata.last_activity:.1f}s"
                )
        
        return closed_count
    
    def get_stats(self) -> Dict:
        """
        Retorna estatísticas sobre sessões ativas.
        
        Returns:
            Dicionário com estatísticas
        """
        with self._lock:
            total_sessions = len(self._sessions_by_thread)
            sessions_by_account = {
                account_id: len(metadatas)
                for account_id, metadatas in self._sessions_by_account.items()
            }
            
            expired_count = len(self.get_expired_sessions())
            
            return {
                "total_active_sessions": total_sessions,
                "sessions_by_account": sessions_by_account,
                "expired_sessions": expired_count,
                "total_accounts": len(self._sessions_by_account),
                "registry_total": self._registry.get_total_sessions()
            }
    
    @contextmanager
    def account_session(self, account_id: str):
        """
        Context manager que garante sessão isolada por conta.
        
        Args:
            account_id: ID da conta
            
        Yields:
            Session: Sessão thread-local isolada para a conta
        """
        session = self.get_or_create_session(account_id=account_id)
        try:
            yield session
            session.commit()
            self.update_activity(session)
        except Exception:
            session.rollback()
            raise
        finally:
            # Não fecha a sessão aqui - ela é thread-local e pode ser reutilizada
            # Apenas atualiza atividade
            self.update_activity(session)


class SessionCleanupThread(threading.Thread):
    """
    Thread de cleanup em background que fecha sessões expiradas e órfãs.
    """
    
    def __init__(self, manager: SessionLifecycleManager, stop_event: threading.Event):
        """
        Inicializa a thread de cleanup.
        
        Args:
            manager: SessionLifecycleManager a ser usado
            stop_event: Event para sinalizar parada
        """
        super().__init__(name="SessionCleanupThread", daemon=True)
        self._manager = manager
        self._stop_event = stop_event
        self._interval = 60.0  # Verifica a cada 60 segundos
    
    def run(self) -> None:
        """Loop principal da thread de cleanup."""
        logger.info("[SESSION] Cleanup thread iniciada")
        
        while not self._stop_event.is_set():
            try:
                # Limpa sessões expiradas
                closed = self._manager.cleanup_expired_sessions()
                if closed > 0:
                    logger.info(f"[SESSION] Cleanup: {closed} sessões expiradas fechadas")
                
                # Aguarda próximo ciclo
                self._stop_event.wait(self._interval)
                
            except Exception as e:
                logger.error(f"[SESSION] Erro na cleanup thread: {e}", exc_info=True)
                # Continua mesmo com erro
                self._stop_event.wait(self._interval)
        
        logger.info("[SESSION] Cleanup thread finalizada")


# Instância global do gerenciador
_session_lifecycle_manager: Optional[SessionLifecycleManager] = None
_manager_lock = threading.Lock()


def get_session_lifecycle_manager() -> SessionLifecycleManager:
    """
    Obtém a instância global do SessionLifecycleManager.
    
    Returns:
        SessionLifecycleManager: Instância singleton do gerenciador
    """
    global _session_lifecycle_manager
    
    if _session_lifecycle_manager is None:
        with _manager_lock:
            if _session_lifecycle_manager is None:
                _session_lifecycle_manager = SessionLifecycleManager()
                _session_lifecycle_manager.start_cleanup_thread()
    
    return _session_lifecycle_manager


def check_session_health() -> Dict:
    """
    Verifica saúde das sessões ativas.
    
    Returns:
        Dicionário com informações de saúde:
        - active_sessions: Número de sessões ativas
        - expired_sessions: Número de sessões expiradas
        - orphaned_sessions: Sessões sem atividade há >10 minutos
        - long_transactions: Transações com mais de 30 segundos
        - pool_status: Status do connection pool
    """
    manager = get_session_lifecycle_manager()
    stats = manager.get_stats()
    
    now = time.time()
    orphaned = []
    long_transactions = []
    
    with manager._lock:
        for metadata in manager._sessions_by_thread.values():
            # Sessões órfãs (>10 minutos sem atividade)
            if (now - metadata.last_activity) > 600:
                orphaned.append({
                    "account_id": metadata.account_id,
                    "thread_id": metadata.thread_id,
                    "idle_time": now - metadata.last_activity
                })
            
            # Transações longas (>30 segundos)
            if metadata.transaction_start and (now - metadata.transaction_start) > 30:
                long_transactions.append({
                    "account_id": metadata.account_id,
                    "thread_id": metadata.thread_id,
                    "duration": now - metadata.transaction_start
                })
    
    # Status do pool (se disponível)
    pool_status = {}
    try:
        from zowsuplib.app.db import engine
        pool = engine.pool
        pool_status = {
            "size": pool.size() if hasattr(pool, 'size') else None,
            "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None,
            "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else None,
            "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
        }
    except Exception as e:
        pool_status = {"error": str(e)}
    
    return {
        "active_sessions": stats["total_active_sessions"],
        "expired_sessions": stats["expired_sessions"],
        "orphaned_sessions": len(orphaned),
        "orphaned_details": orphaned,
        "long_transactions": len(long_transactions),
        "long_transactions_details": long_transactions,
        "sessions_by_account": stats["sessions_by_account"],
        "pool_status": pool_status,
        "health_status": "healthy" if len(orphaned) == 0 and len(long_transactions) == 0 else "warning"
    }

