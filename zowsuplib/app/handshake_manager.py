"""
Gerenciador centralizado de handshakes.

Gerencia uma única thread para processar handshakes de todas as contas,
reduzindo o número de threads do sistema.
"""

import threading
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
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
    Gerenciador singleton que processa handshakes de todas as contas em paralelo.
    
    Usa ThreadPoolExecutor com 3 workers para processar até 3 handshakes simultaneamente,
    melhorando a escalabilidade para múltiplas contas.
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
        
        # ThreadPoolExecutor para processamento paralelo (3 handshakes simultâneos)
        self._executor: Optional[ThreadPoolExecutor] = ThreadPoolExecutor(
            max_workers=3,
            thread_name_prefix="HandshakeWorker"
        )
        self._futures: Dict[str, Future] = {}  # account_id -> Future
        
        logger.info("[HandshakeManager] Inicializado - modo paralelo ativado (3 workers)")
    
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
                logger.info(f"[HandshakeManager] Thread do manager não está rodando, iniciando...")
                self._start_manager_thread()
            else:
                logger.debug(f"[HandshakeManager] Thread do manager já está rodando (thread_id={self._manager_thread.ident})")
            
            logger.info(
                f"[HandshakeManager] Handshake registrado para {account_id}. "
                f"Total na fila: {len(self._processing_queue)}, "
                f"Total no dicionário: {len(self._handshake_queue)}"
            )
    
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
            logger.warning(
                f"[HandshakeManager] Thread do manager já está rodando "
                f"(thread_id={self._manager_thread.ident}, is_alive={self._manager_thread.is_alive()})"
            )
            return
        
        logger.info("[HandshakeManager] Iniciando thread do gerenciador de handshakes")
        self._stop_event.clear()
        self._manager_thread = threading.Thread(
            target=self._run_manager_loop,
            name="HandshakeManager",
            daemon=True
        )
        self._manager_thread.start()
        logger.info(
            f"[HandshakeManager] Thread do manager iniciada: "
            f"thread_id={self._manager_thread.ident}, "
            f"name={self._manager_thread.name}, "
            f"is_alive={self._manager_thread.is_alive()}"
        )
    
    def _run_manager_loop(self) -> None:
        """
        Loop principal que processa todos os handshakes registrados em paralelo.
        
        Usa ThreadPoolExecutor para processar até 3 handshakes simultaneamente.
        """
        logger.info("[HandshakeManager] Loop do gerenciador de handshakes iniciado (modo paralelo)")
        loop_iteration = 0
        
        while not self._stop_event.is_set():
            try:
                loop_iteration += 1
                
                # Limpa futures completados
                self._cleanup_completed_futures()
                
                # Verifica quantos handshakes estão em execução
                active_futures = len([f for f in self._futures.values() if not f.done()])
                max_workers = 3
                
                # Se já temos 3 handshakes em execução, aguarda um pouco
                if active_futures >= max_workers:
                    if loop_iteration % 50 == 0:
                        logger.debug(
                            f"[HandshakeManager] Loop iteração {loop_iteration}: "
                            f"{active_futures} handshakes em execução (máximo: {max_workers}), aguardando..."
                        )
                    self._stop_event.wait(0.1)
                    continue
                
                # Obtém próximo handshake da fila
                account_id = None
                task = None
                
                with self._lock:
                    # Remove handshakes inativos e já em execução da fila
                    self._processing_queue = [
                        acc_id for acc_id in self._processing_queue
                        if acc_id in self._handshake_queue 
                        and self._handshake_queue[acc_id].active
                        and acc_id not in self._futures  # Não está em execução
                    ]
                    
                    if self._processing_queue:
                        account_id = self._processing_queue.pop(0)
                        task = self._handshake_queue.get(account_id)
                        logger.debug(
                            f"[HandshakeManager] Loop iteração {loop_iteration}: "
                            f"handshake encontrado para {account_id}, "
                            f"fila restante: {len(self._processing_queue)}, "
                            f"em execução: {active_futures}/{max_workers}"
                        )
                    else:
                        if loop_iteration % 100 == 0:  # Log a cada 100 iterações quando vazio
                            logger.debug(
                                f"[HandshakeManager] Loop iteração {loop_iteration}: "
                                f"nenhum handshake na fila, aguardando... "
                                f"(em execução: {active_futures}/{max_workers})"
                            )
                
                # Se não há handshakes, aguarda um pouco
                if task is None or not task.active:
                    self._stop_event.wait(0.1)
                    continue
                
                # Submete handshake ao executor (processamento paralelo)
                logger.info(
                    f"[HandshakeManager] Submetendo handshake para processamento paralelo: {account_id} "
                    f"(attempt_id={task.attempt_id}, iteração={loop_iteration}, "
                    f"em execução: {active_futures + 1}/{max_workers})"
                )
                
                if self._stop_event.is_set():
                    break
                
                # Submete ao executor
                future = self._executor.submit(self._execute_handshake_wrapper, task)
                with self._lock:
                    self._futures[account_id] = future
                logger.debug(
                    f"[HandshakeManager] Handshake submetido ao executor para {account_id} "
                    f"(future={future}, executor_threads={self._executor._threads if hasattr(self._executor, '_threads') else 'N/A'})"
                )
                
            except Exception as e:
                logger.error(f"[HandshakeManager] Erro no loop principal (iteração {loop_iteration}): {e}", exc_info=True)
                self._stop_event.wait(0.1)
        
        # Aguarda conclusão de todos os handshakes pendentes
        logger.info("[HandshakeManager] Aguardando conclusão de handshakes pendentes...")
        self._wait_for_all_futures()
        
        logger.info(f"[HandshakeManager] Loop do gerenciador de handshakes finalizado (total de iterações: {loop_iteration})")
    
    def _cleanup_completed_futures(self) -> None:
        """Remove futures completados e limpa handshakes finalizados."""
        with self._lock:
            completed_accounts = []
            for account_id, future in list(self._futures.items()):
                if future.done():
                    completed_accounts.append(account_id)
                    # Remove da fila de processamento
                    if account_id in self._processing_queue:
                        self._processing_queue.remove(account_id)
                    # Remove do dicionário de handshakes
                    if account_id in self._handshake_queue:
                        del self._handshake_queue[account_id]
            
            for account_id in completed_accounts:
                del self._futures[account_id]
                logger.debug(f"[HandshakeManager] Handshake finalizado e removido: {account_id}")
    
    def _wait_for_all_futures(self, timeout: float = 30.0) -> None:
        """Aguarda conclusão de todos os futures pendentes."""
        with self._lock:
            futures_to_wait = list(self._futures.values())
        
        if not futures_to_wait:
            return
        
        logger.info(f"[HandshakeManager] Aguardando {len(futures_to_wait)} handshake(s) pendente(s)...")
        for future in as_completed(futures_to_wait, timeout=timeout):
            try:
                future.result(timeout=1.0)
            except Exception as e:
                logger.error(f"[HandshakeManager] Erro ao aguardar future: {e}", exc_info=True)
    
    def _execute_handshake_wrapper(self, task: HandshakeTask) -> None:
        """
        Wrapper para executar handshake e tratar erros.
        
        Args:
            task: Tarefa de handshake a ser executada
        """
        account_id = task.account_id
        try:
            logger.info(
                f"[HandshakeManager] Iniciando processamento de handshake para {account_id} "
                f"(attempt_id={task.attempt_id})"
            )
            self._execute_handshake(task)
            logger.info(
                f"[HandshakeManager] Handshake para {account_id} processado com sucesso"
            )
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
        """Para o loop de processamento e fecha o executor."""
        logger.info("[HandshakeManager] Parando gerenciador de handshakes")
        self._stop_event.set()
        
        if self._manager_thread is not None:
            self._manager_thread.join(timeout=5.0)
            if self._manager_thread.is_alive():
                logger.warning("[HandshakeManager] Thread do manager não terminou em 5 segundos")
            else:
                logger.info("[HandshakeManager] Thread do manager finalizada")
        
        # Fecha o executor e aguarda conclusão de tasks pendentes
        if self._executor is not None:
            logger.info("[HandshakeManager] Fechando ThreadPoolExecutor...")
            self._executor.shutdown(wait=True, timeout=30.0)
            logger.info("[HandshakeManager] ThreadPoolExecutor fechado")
        
        with self._lock:
            self._handshake_queue.clear()
            self._processing_queue.clear()
            self._futures.clear()
    
    def get_handshake_count(self) -> int:
        """Retorna o número de handshakes na fila."""
        with self._lock:
            return len(self._processing_queue)
    
    def is_running(self) -> bool:
        """Verifica se o manager está rodando."""
        return self._manager_thread is not None and self._manager_thread.is_alive()

