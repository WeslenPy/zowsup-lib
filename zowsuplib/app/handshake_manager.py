"""
Gerenciador centralizado de handshakes.

Gerencia uma única thread para processar handshakes de todas as contas,
reduzindo o número de threads do sistema.
"""

import threading
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from loguru import logger

# TYPE_CHECKING para evitar importação circular
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from zowsuplib.consonance.protocol import WANoiseProtocol
    from zowsuplib.consonance.streams.segmented.segmented import SegmentedStream
    from zowsuplib.consonance.config.client import ClientConfig
    from zowsuplib.consonance.structs.keypair import KeyPair
    from zowsuplib.consonance.structs.publickey import PublicKey


@dataclass
class HandshakeTask:
    """Tarefa de handshake para processamento."""
    account_id: str
    attempt_id: int
    protocol: 'WANoiseProtocol'  # type: ignore
    stream: 'SegmentedStream'  # type: ignore
    client_config: 'ClientConfig'  # type: ignore
    s: 'KeyPair'  # type: ignore
    rs: Optional['PublicKey']  # type: ignore
    finish_callback: Callable[[Optional[Exception]], None]
    mode: Optional[str] = None
    identity: Optional[Any] = None
    regid: Optional[Any] = None
    signedprekey: Optional[Any] = None
    deviceid: Optional[int] = None
    created_time: float = 0.0
    active: bool = True


class HandshakeManager:
    """
    Gerenciador singleton que processa handshakes de todas as contas em uma única thread.
    
    Ao invés de cada handshake criar sua própria thread,
    este manager mantém uma fila de handshakes pendentes e os processa sequencialmente
    em uma única thread dedicada.
    """
    
    _instance: Optional['HandshakeManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Inicializa o gerenciador de handshakes."""
        if HandshakeManager._instance is not None:
            raise RuntimeError("HandshakeManager é um singleton. Use HandshakeManager.get_instance()")
        
        self._handshake_queue: Dict[str, HandshakeTask] = {}  # account_id -> HandshakeTask
        self._processing_queue: list = []  # Fila de handshakes para processar
        self._manager_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._processing_lock = threading.Lock()  # Lock para processamento sequencial
        
        logger.info("[HandshakeManager] Inicializado - modo de thread única ativado")
    
    @classmethod
    def get_instance(cls) -> 'HandshakeManager':
        """
        Retorna a instância singleton do HandshakeManager.
        
        Thread-safe: usa double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def register_handshake(
        self,
        account_id: str,
        attempt_id: int,
        protocol: 'WANoiseProtocol',  # type: ignore
        stream: 'SegmentedStream',  # type: ignore
        client_config: 'ClientConfig',  # type: ignore
        s: 'KeyPair',  # type: ignore
        rs: Optional['PublicKey'],  # type: ignore
        finish_callback: Callable[[Optional[Exception]], None],
        mode: Optional[str] = None,
        identity: Optional[Any] = None,
        regid: Optional[Any] = None,
        signedprekey: Optional[Any] = None,
        deviceid: Optional[int] = None
    ) -> None:
        """
        Registra um handshake para processamento no loop centralizado.
        
        Args:
            account_id: ID da conta
            attempt_id: ID da tentativa de handshake
            protocol: Protocolo WANoise
            stream: Stream segmentado
            client_config: Configuração do cliente
            s: KeyPair local
            rs: PublicKey remota (opcional)
            finish_callback: Callback chamado quando handshake termina
            mode: Modo do handshake (opcional)
            identity: Identidade (opcional)
            regid: Registration ID (opcional)
            signedprekey: Signed prekey (opcional)
            deviceid: Device ID (opcional)
        """
        with self._lock:
            # Remove handshake anterior da mesma conta se existir
            if account_id in self._handshake_queue:
                old_task = self._handshake_queue[account_id]
                old_task.active = False
                logger.warning(
                    f"[HandshakeManager] Substituindo handshake anterior da conta {account_id} "
                    f"(attempt_id={old_task.attempt_id} -> {attempt_id})"
                )
            
            logger.info(
                f"[HandshakeManager] Registrando handshake para conta {account_id} "
                f"(attempt_id={attempt_id}, mode={mode})"
            )
            
            task = HandshakeTask(
                account_id=account_id,
                attempt_id=attempt_id,
                protocol=protocol,
                stream=stream,
                client_config=client_config,
                s=s,
                rs=rs,
                finish_callback=finish_callback,
                mode=mode,
                identity=identity,
                regid=regid,
                signedprekey=signedprekey,
                deviceid=deviceid,
                created_time=time.time(),
                active=True
            )
            
            self._handshake_queue[account_id] = task
            self._processing_queue.append(account_id)
            
            # Inicia a thread do manager se ainda não estiver rodando
            if self._manager_thread is None or not self._manager_thread.is_alive():
                self._start_manager_thread()
            
            logger.debug(f"[HandshakeManager] Handshake registrado. Total na fila: {len(self._processing_queue)}")
    
    def unregister_handshake(self, account_id: str) -> None:
        """
        Remove um handshake do processamento.
        
        Args:
            account_id: ID da conta
        """
        with self._lock:
            if account_id in self._handshake_queue:
                task = self._handshake_queue.pop(account_id)
                task.active = False
                # Remove da fila de processamento se estiver lá
                if account_id in self._processing_queue:
                    self._processing_queue.remove(account_id)
                logger.debug(f"[HandshakeManager] Handshake removido para conta {account_id}")
    
    def _start_manager_thread(self) -> None:
        """Inicia a thread de processamento de handshakes."""
        if self._manager_thread is not None and self._manager_thread.is_alive():
            logger.warning("[HandshakeManager] Thread do manager já está rodando")
            return
        
        logger.info("[HandshakeManager] Iniciando thread do gerenciador de handshakes")
        self._stop_event.clear()
        self._manager_thread = threading.Thread(
            target=self._run_manager_loop,
            name="HandshakeManager",
            daemon=True
        )
        self._manager_thread.start()
        logger.info(f"[HandshakeManager] Thread do manager iniciada: {self._manager_thread.ident}")
    
    def _run_manager_loop(self) -> None:
        """
        Loop principal que processa todos os handshakes registrados.
        
        Processa handshakes sequencialmente (um por vez) para evitar conflitos.
        """
        logger.info("[HandshakeManager] Loop do gerenciador de handshakes iniciado")
        
        while not self._stop_event.is_set():
            try:
                # Obtém próximo handshake da fila
                account_id = None
                task = None
                
                with self._lock:
                    # Remove handshakes inativos da fila
                    self._processing_queue = [
                        acc_id for acc_id in self._processing_queue
                        if acc_id in self._handshake_queue and self._handshake_queue[acc_id].active
                    ]
                    
                    if self._processing_queue:
                        account_id = self._processing_queue.pop(0)
                        task = self._handshake_queue.get(account_id)
                
                # Se não há handshakes, aguarda um pouco
                if task is None or not task.active:
                    self._stop_event.wait(0.1)
                    continue
                
                # Processa o handshake (sequencialmente, com lock)
                with self._processing_lock:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        self._execute_handshake(task)
                    except Exception as e:
                        logger.error(
                            f"[HandshakeManager] Erro ao processar handshake para {account_id}: {e}",
                            exc_info=True
                        )
                        # Chama callback de erro
                        try:
                            task.finish_callback(e)
                        except Exception as callback_error:
                            logger.error(f"[HandshakeManager] Erro no callback de handshake: {callback_error}")
                    finally:
                        # Remove da fila após processamento
                        self.unregister_handshake(account_id)
                
            except Exception as e:
                logger.error(f"[HandshakeManager] Erro no loop principal: {e}", exc_info=True)
                self._stop_event.wait(0.1)
        
        logger.info("[HandshakeManager] Loop do gerenciador de handshakes finalizado")
    
    def _execute_handshake(self, task: HandshakeTask) -> None:
        """
        Executa um handshake específico.
        
        Args:
            task: Tarefa de handshake a ser executada
        """
        import traceback
        from zowsuplib.consonance.exceptions.handshake_failed_exception import HandshakeFailedException
        
        thread_id = threading.current_thread().ident
        logger.info(
            f"[HandshakeManager] Executando handshake | "
            f"account={task.account_id} attempt_id={task.attempt_id} "
            f"thread_id={thread_id} mode={task.mode}"
        )
        
        # Reset do protocolo
        task.protocol.reset()
        error = None
        
        try:
            logger.info(
                f"[HandshakeManager] [handshake {task.attempt_id}] iniciando protocol.start() | "
                f"account={task.account_id} thread_id={thread_id}"
            )
            
            # Executa o handshake (pode ser bloqueante)
            task.protocol.start(
                task.stream,
                task.client_config,
                task.s,
                task.rs,
                mode=task.mode,
                identity=task.identity,
                regid=task.regid,
                signedprekey=task.signedprekey,
                deviceid=task.deviceid
            )
            
            logger.info(
                f"[HandshakeManager] [handshake {task.attempt_id}] protocol.start() concluído com sucesso | "
                f"account={task.account_id} thread_id={thread_id}"
            )
            
        except HandshakeFailedException as e:
            error = e
            logger.error(
                f"[HandshakeManager] [handshake {task.attempt_id}] HandshakeFailedException | "
                f"account={task.account_id} thread_id={thread_id} error={e}"
            )
            logger.error(f"[HandshakeManager] Traceback:\n{traceback.format_exc()}")
        except Exception as e:
            error = e
            logger.error(
                f"[HandshakeManager] [handshake {task.attempt_id}] Exception inesperada | "
                f"account={task.account_id} thread_id={thread_id} error={e}"
            )
            logger.error(f"[HandshakeManager] Traceback:\n{traceback.format_exc()}")
        
        # Chama callback de término
        logger.info(
            f"[HandshakeManager] [handshake {task.attempt_id}] chamando finish_callback | "
            f"account={task.account_id} thread_id={thread_id} error={'present' if error else 'none'}"
        )
        try:
            task.finish_callback(error)
        except Exception as callback_error:
            logger.error(
                f"[HandshakeManager] Erro no finish_callback para {task.account_id}: {callback_error}",
                exc_info=True
            )
        
        logger.info(
            f"[HandshakeManager] [handshake {task.attempt_id}] handshake finalizado | "
            f"account={task.account_id} thread_id={thread_id}"
        )
    
    def stop(self) -> None:
        """Para o loop de processamento."""
        logger.info("[HandshakeManager] Parando gerenciador de handshakes")
        self._stop_event.set()
        
        if self._manager_thread is not None:
            self._manager_thread.join(timeout=5.0)
            if self._manager_thread.is_alive():
                logger.warning("[HandshakeManager] Thread do manager não terminou em 5 segundos")
            else:
                logger.info("[HandshakeManager] Thread do manager finalizada")
        
        with self._lock:
            self._handshake_queue.clear()
            self._processing_queue.clear()
    
    def get_handshake_count(self) -> int:
        """Retorna o número de handshakes na fila."""
        with self._lock:
            return len(self._processing_queue)
    
    def is_running(self) -> bool:
        """Verifica se o manager está rodando."""
        return self._manager_thread is not None and self._manager_thread.is_alive()

