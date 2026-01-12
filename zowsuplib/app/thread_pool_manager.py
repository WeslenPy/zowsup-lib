"""
Gerenciador singleton de ThreadPoolExecutor compartilhado entre todas as contas.

Benefícios:
- Reduz uso de recursos (menos threads)
- Melhor aproveitamento do pool de threads
- Facilita monitoramento centralizado

Uso:
    executor = ThreadPoolManager.get_executor()
    future = executor.submit(func, *args, **kwargs)
"""

import threading
import concurrent.futures
from typing import Optional
from loguru import logger


class ThreadPoolManager:
    """
    Gerenciador singleton de ThreadPoolExecutor compartilhado entre todas as contas.
    
    Benefícios:
    - Reduz uso de recursos (menos threads)
    - Melhor aproveitamento do pool de threads
    - Facilita monitoramento centralizado
    
    Uso:
        executor = ThreadPoolManager.get_executor()
        future = executor.submit(func, *args, **kwargs)
    """
    
    _instance: Optional['ThreadPoolManager'] = None
    _lock = threading.Lock()
    
    def __init__(self, max_workers: int = 50):
        """
        Inicializa o gerenciador de thread pool.
        
        Args:
            max_workers: Número máximo de workers compartilhados (padrão: 50)
                        Ajuste baseado no número esperado de contas ativas
        """
        if ThreadPoolManager._instance is not None:
            raise RuntimeError("ThreadPoolManager é um singleton. Use get_instance()")
        
        self._max_workers = max_workers
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._ref_count = 0  # Contador de referências (quantas contas estão usando)
        self._ref_lock = threading.Lock()
        
        logger.info(f"[ThreadPoolManager] Inicializado com {max_workers} workers compartilhados")
    
    @classmethod
    def get_instance(cls, max_workers: int = 50) -> 'ThreadPoolManager':
        """
        Retorna a instância singleton do ThreadPoolManager.
        
        Thread-safe: usa double-checked locking.
        
        Args:
            max_workers: Número máximo de workers (usado apenas na primeira criação)
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_workers)
        return cls._instance
    
    def get_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """
        Retorna o executor compartilhado, criando se necessário.
        
        Thread-safe: incrementa contador de referências.
        
        Returns:
            ThreadPoolExecutor compartilhado
        """
        with self._ref_lock:
            if self._executor is None:
                self._executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix="cmd-handler-shared"
                )
                logger.info(f"[ThreadPoolManager] Executor criado com {self._max_workers} workers")
            
            self._ref_count += 1
            logger.debug(f"[ThreadPoolManager] Executor referenciado (ref_count={self._ref_count})")
            
            return self._executor
    
    def release_executor(self) -> None:
        """
        Libera uma referência ao executor.
        
        Se não houver mais referências, o executor é encerrado.
        """
        with self._ref_lock:
            if self._ref_count > 0:
                self._ref_count -= 1
                logger.debug(f"[ThreadPoolManager] Executor liberado (ref_count={self._ref_count})")
                
                # Se não há mais referências, encerra o executor
                if self._ref_count == 0 and self._executor is not None:
                    logger.info("[ThreadPoolManager] Encerrando executor (sem referências)")
                    self._executor.shutdown(wait=False)
                    self._executor = None
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do executor compartilhado.
        
        Returns:
            Dict com estatísticas
        """
        stats = {
            "max_workers": self._max_workers,
            "ref_count": self._ref_count,
            "executor_exists": self._executor is not None,
        }
        
        if self._executor is not None:
            try:
                stats["active_threads"] = len([
                    t for t in threading.enumerate() 
                    if t.name.startswith("cmd-handler-shared")
                ])
                
                if hasattr(self._executor, '_threads'):
                    stats["executor_threads"] = len([
                        t for t in self._executor._threads if t is not None
                    ])
            except Exception:
                pass
        
        return stats
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Encerra o executor compartilhado.
        
        Args:
            wait: Se True, aguarda conclusão de tarefas pendentes
        """
        with self._ref_lock:
            if self._executor is not None:
                logger.info(f"[ThreadPoolManager] Encerrando executor (wait={wait})")
                self._executor.shutdown(wait=wait)
                self._executor = None
                self._ref_count = 0

