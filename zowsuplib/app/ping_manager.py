"""
Gerenciador centralizado de pings.

Gerencia uma única thread para enviar pings de todas as contas,
reduzindo o número de threads do sistema.
"""

import threading
import time
from typing import Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
from loguru import logger

if TYPE_CHECKING:
    from zowsuplib.yowsup.layers.protocol_iq.layer import YowIqProtocolLayer

from zowsuplib.yowsup.layers.protocol_iq.protocolentities.iq_ping import PingIqProtocolEntity


@dataclass
class PingEntry:
    """Entrada na lista de pings para processamento."""
    layer: 'YowIqProtocolLayer'  # type: ignore
    account_id: str
    interval: int  # Intervalo em segundos
    last_ping_time: float = 0.0
    active: bool = True


class PingManager:
    """
    Gerenciador singleton que envia pings de todas as contas em uma única thread.
    
    Ao invés de cada conta ter sua própria thread para ping,
    este manager mantém uma lista de contas ativas e envia pings em round-robin
    em uma única thread dedicada.
    """
    
    _instance: Optional['PingManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Inicializa o gerenciador de pings."""
        if PingManager._instance is not None:
            raise RuntimeError("PingManager é um singleton. Use PingManager.get_instance()")
        
        self._pings: Dict[str, PingEntry] = {}
        self._ping_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._check_interval = 1.0  # Verifica a cada 1 segundo se algum ping precisa ser enviado
        
        logger.info("[PingManager] Inicializado - modo de thread única ativado")
    
    @classmethod
    def get_instance(cls) -> 'PingManager':
        """
        Retorna a instância singleton do PingManager.
        
        Thread-safe: usa double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def register_ping(
        self,
        account_id: str,
        layer: 'YowIqProtocolLayer',  # type: ignore
        interval: int
    ) -> None:
        """
        Registra uma conta para envio de pings no loop centralizado.
        
        Args:
            account_id: ID da conta (usado para identificação)
            layer: Layer IQ que gerencia os pings desta conta
            interval: Intervalo entre pings em segundos
        """
        with self._lock:
            if account_id in self._pings:
                logger.warning(f"[PingManager] Ping para conta {account_id} já registrado, atualizando")
            
            logger.info(f"[PingManager] Registrando ping para conta {account_id} (interval={interval}s)")
            self._pings[account_id] = PingEntry(
                layer=layer,
                account_id=account_id,
                interval=interval,
                last_ping_time=0.0,
                active=True
            )
            
            # Inicia a thread de ping se ainda não estiver rodando
            if self._ping_thread is None or not self._ping_thread.is_alive():
                self._start_ping_thread()
            
            logger.info(f"[PingManager] Ping registrado. Total de pings: {len(self._pings)}")
    
    def unregister_ping(self, account_id: str) -> None:
        """
        Remove uma conta do processamento de pings.
        
        Args:
            account_id: ID da conta a ser removida
        """
        with self._lock:
            if account_id in self._pings:
                logger.info(f"[PingManager] Removendo ping da conta {account_id}")
                entry = self._pings[account_id]
                entry.active = False
                del self._pings[account_id]
                logger.info(f"[PingManager] Ping removido. Total de pings: {len(self._pings)}")
            else:
                logger.warning(f"[PingManager] Tentativa de remover ping inexistente: {account_id}")
    
    def update_interval(self, account_id: str, interval: int) -> None:
        """
        Atualiza o intervalo de ping para uma conta.
        
        Args:
            account_id: ID da conta
            interval: Novo intervalo em segundos
        """
        with self._lock:
            if account_id in self._pings:
                self._pings[account_id].interval = interval
                logger.debug(f"[PingManager] Intervalo atualizado para {account_id}: {interval}s")
    
    def _start_ping_thread(self) -> None:
        """Inicia a thread de processamento de pings."""
        if self._ping_thread is not None and self._ping_thread.is_alive():
            logger.warning("[PingManager] Thread de ping já está rodando")
            return
        
        logger.info("[PingManager] Iniciando thread de ping centralizado")
        self._stop_event.clear()
        self._ping_thread = threading.Thread(
            target=self._run_ping_loop,
            name="PingManager",
            daemon=True
        )
        self._ping_thread.start()
        logger.info(f"[PingManager] Thread de ping iniciada: {self._ping_thread.ident}")
    
    def _run_ping_loop(self) -> None:
        """
        Loop principal que envia pings para todas as contas registradas.
        
        Verifica periodicamente se algum ping precisa ser enviado baseado no intervalo
        de cada conta.
        """
        logger.info("[PingManager] Loop de ping centralizado iniciado")
        
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Obtém lista de pings ativos (com lock mínimo)
                pings_to_check = []
                with self._lock:
                    pings_to_check = [
                        (account_id, entry)
                        for account_id, entry in self._pings.items()
                        if entry.active
                    ]
                
                # Se não há pings, aguarda um pouco
                if not pings_to_check:
                    time.sleep(self._check_interval)
                    continue
                
                # Verifica cada conta e envia ping se necessário
                for account_id, entry in pings_to_check:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        # Calcula se é hora de enviar ping
                        time_since_last_ping = current_time - entry.last_ping_time
                        
                        if time_since_last_ping >= entry.interval:
                            # Envia ping
                            ping = PingIqProtocolEntity()
                            ping_id = ping.getId()
                            
                            # Registra o ping na fila da layer
                            entry.layer.waitPong(ping_id)
                            
                            # Envia o ping
                            entry.layer.sendIq(ping)
                            
                            # Atualiza timestamp
                            entry.last_ping_time = current_time
                            
                            logger.debug(
                                f"[PingManager] Ping enviado para {account_id} "
                                f"(id={ping_id}, interval={entry.interval}s)"
                            )
                        
                    except Exception as e:
                        logger.error(
                            f"[PingManager] Erro ao enviar ping para {account_id}: {e}",
                            exc_info=True
                        )
                        # Marca como inativo em caso de erro
                        entry.active = False
                
                # Aguarda antes da próxima verificação
                time.sleep(self._check_interval)
                
            except Exception as e:
                logger.error(f"[PingManager] Erro no loop de ping: {e}", exc_info=True)
                time.sleep(self._check_interval)
        
        logger.info("[PingManager] Loop de ping centralizado finalizado")
    
    def stop(self) -> None:
        """Para o loop de pings."""
        logger.info("[PingManager] Parando loop de ping centralizado")
        self._stop_event.set()
        
        if self._ping_thread is not None:
            self._ping_thread.join(timeout=5.0)
            if self._ping_thread.is_alive():
                logger.warning("[PingManager] Thread de ping não terminou em 5 segundos")
            else:
                logger.info("[PingManager] Thread de ping finalizada")
        
        with self._lock:
            self._pings.clear()
    
    def get_ping_count(self) -> int:
        """Retorna o número de pings registrados."""
        with self._lock:
            return len(self._pings)
    
    def is_running(self) -> bool:
        """Verifica se o loop está rodando."""
        return self._ping_thread is not None and self._ping_thread.is_alive()

