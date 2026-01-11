"""
Métricas e estatísticas sobre sessões de banco de dados.

Coleta e expõe métricas sobre sessões ativas, performance e saúde do sistema.
"""

import threading
import time
from typing import Dict, List, Optional
from collections import defaultdict
from loguru import logger


class SessionMetrics:
    """
    Coleta métricas sobre sessões de banco de dados.
    
    Thread-safe: usa locks para garantir consistência.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Contadores
        self._total_created = 0
        self._total_closed = 0
        self._total_errors = 0
        
        # Métricas por thread
        self._sessions_by_thread: Dict[int, int] = defaultdict(int)
        
        # Métricas por conta
        self._sessions_by_account: Dict[str, int] = defaultdict(int)
        
        # Métricas de transação
        self._transaction_times: List[float] = []
        self._max_transaction_time = 100  # Mantém apenas últimas 100 transações
        
        # Erros por tipo
        self._errors_by_type: Dict[str, int] = defaultdict(int)
        
        # Timestamps
        self._start_time = time.time()
    
    def record_session_created(self, account_id: Optional[str] = None) -> None:
        """
        Registra criação de uma nova sessão.
        
        Args:
            account_id: ID da conta (opcional)
        """
        with self._lock:
            self._total_created += 1
            thread_id = threading.current_thread().ident
            self._sessions_by_thread[thread_id] += 1
            
            if account_id:
                self._sessions_by_account[account_id] += 1
    
    def record_session_closed(self, account_id: Optional[str] = None) -> None:
        """
        Registra fechamento de uma sessão.
        
        Args:
            account_id: ID da conta (opcional)
        """
        with self._lock:
            self._total_closed += 1
            thread_id = threading.current_thread().ident
            if thread_id in self._sessions_by_thread:
                self._sessions_by_thread[thread_id] = max(0, self._sessions_by_thread[thread_id] - 1)
            
            if account_id and account_id in self._sessions_by_account:
                self._sessions_by_account[account_id] = max(0, self._sessions_by_account[account_id] - 1)
    
    def record_error(self, error_type: str, account_id: Optional[str] = None) -> None:
        """
        Registra um erro de sessão.
        
        Args:
            error_type: Tipo do erro (ex: "DetachedInstanceError", "Timeout")
            account_id: ID da conta (opcional)
        """
        with self._lock:
            self._total_errors += 1
            self._errors_by_type[error_type] += 1
            logger.warning(f"[SESSION] Erro registrado | type={error_type} account={account_id or 'N/A'}")
    
    def record_transaction_time(self, duration: float) -> None:
        """
        Registra duração de uma transação.
        
        Args:
            duration: Duração em segundos
        """
        with self._lock:
            self._transaction_times.append(duration)
            # Mantém apenas últimas N transações
            if len(self._transaction_times) > self._max_transaction_time:
                self._transaction_times.pop(0)
    
    def get_stats(self) -> Dict:
        """
        Retorna estatísticas completas sobre sessões.
        
        Returns:
            Dicionário com estatísticas:
            - total_created: Total de sessões criadas
            - total_closed: Total de sessões fechadas
            - active_sessions: Sessões ativas atualmente
            - total_errors: Total de erros
            - errors_by_type: Erros agrupados por tipo
            - sessions_by_thread: Sessões ativas por thread
            - sessions_by_account: Sessões ativas por conta
            - avg_transaction_time: Tempo médio de transação
            - max_transaction_time: Tempo máximo de transação
            - min_transaction_time: Tempo mínimo de transação
            - uptime: Tempo desde inicialização
        """
        with self._lock:
            active_sessions = sum(self._sessions_by_thread.values())
            
            avg_transaction = 0.0
            max_transaction = 0.0
            min_transaction = 0.0
            
            if self._transaction_times:
                avg_transaction = sum(self._transaction_times) / len(self._transaction_times)
                max_transaction = max(self._transaction_times)
                min_transaction = min(self._transaction_times)
            
            uptime = time.time() - self._start_time
            
            return {
                "total_created": self._total_created,
                "total_closed": self._total_closed,
                "active_sessions": active_sessions,
                "total_errors": self._total_errors,
                "errors_by_type": dict(self._errors_by_type),
                "sessions_by_thread": dict(self._sessions_by_thread),
                "sessions_by_account": dict(self._sessions_by_account),
                "avg_transaction_time": avg_transaction,
                "max_transaction_time": max_transaction,
                "min_transaction_time": min_transaction,
                "transaction_count": len(self._transaction_times),
                "uptime_seconds": uptime,
                "uptime_formatted": f"{uptime / 3600:.1f}h"
            }
    
    def reset(self) -> None:
        """Reseta todas as métricas."""
        with self._lock:
            self._total_created = 0
            self._total_closed = 0
            self._total_errors = 0
            self._sessions_by_thread.clear()
            self._sessions_by_account.clear()
            self._transaction_times.clear()
            self._errors_by_type.clear()
            self._start_time = time.time()
            logger.info("[SESSION] Métricas resetadas")


# Instância global de métricas
_session_metrics: Optional[SessionMetrics] = None
_metrics_lock = threading.Lock()


def get_session_metrics() -> SessionMetrics:
    """
    Obtém a instância global de SessionMetrics.
    
    Returns:
        SessionMetrics: Instância singleton de métricas
    """
    global _session_metrics
    
    if _session_metrics is None:
        with _metrics_lock:
            if _session_metrics is None:
                _session_metrics = SessionMetrics()
    
    return _session_metrics

