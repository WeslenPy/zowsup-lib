"""
Gerenciador centralizado de loops de stack.

Gerencia uma única thread para processar todos os stacks de todas as contas,
reduzindo o número de threads do sistema.
"""

import threading
import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from loguru import logger

from zowsuplib.yowsup.stacks.yowstack import YowStack
from zowsuplib.yowsup.layers import YowLayerEvent
from zowsuplib.yowsup.layers.network.layer import YowNetworkLayer
from zowsuplib.yowsup.layers.network.dispatcher.dispatcher_asyncore import AsyncoreConnectionDispatcher
from zowsuplib.yowsup.common import asyncore


@dataclass
class StackLoopEntry:
    """Entrada na lista de stacks para processamento."""
    stack: YowStack
    account_id: str
    connect_event_sent: bool = False
    on_loop_end: Optional[Callable[[], None]] = None
    active: bool = True


class StackLoopManager:
    """
    Gerenciador singleton que processa todos os stacks em uma única thread.
    
    Ao invés de cada conta ter sua própria thread para o loop do stack,
    este manager mantém uma lista de stacks ativos e os processa em round-robin
    em uma única thread dedicada.
    """
    
    _instance: Optional['StackLoopManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Inicializa o gerenciador de loops de stack."""
        if StackLoopManager._instance is not None:
            raise RuntimeError("StackLoopManager é um singleton. Use StackLoopManager.get_instance()")
        
        self._stacks: Dict[str, StackLoopEntry] = {}
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._loop_interval = 0.01  # 10ms entre processamento de cada stack
        
        logger.info("[StackLoopManager] Inicializado - modo de thread única ativado")
    
    @classmethod
    def get_instance(cls) -> 'StackLoopManager':
        """
        Retorna a instância singleton do StackLoopManager.
        
        Thread-safe: usa double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def register_stack(
        self,
        account_id: str,
        stack: YowStack,
        on_loop_end: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Registra um stack para processamento no loop centralizado.
        
        Args:
            account_id: ID da conta (usado para identificação)
            stack: Stack a ser processado
            on_loop_end: Callback opcional chamado quando o loop termina
        """
        with self._lock:
            if account_id in self._stacks:
                logger.warning(f"[StackLoopManager] Stack para conta {account_id} já registrado, substituindo")
            
            logger.info(f"[StackLoopManager] Registrando stack para conta {account_id}")
            self._stacks[account_id] = StackLoopEntry(
                stack=stack,
                account_id=account_id,
                connect_event_sent=False,
                on_loop_end=on_loop_end,
                active=True
            )
            
            # Inicia a thread de loop se ainda não estiver rodando
            if self._loop_thread is None or not self._loop_thread.is_alive():
                self._start_loop_thread()
            
            logger.info(f"[StackLoopManager] Stack registrado. Total de stacks: {len(self._stacks)}")
    
    def unregister_stack(self, account_id: str) -> None:
        """
        Remove um stack do processamento.
        
        Args:
            account_id: ID da conta a ser removida
        """
        with self._lock:
            if account_id in self._stacks:
                logger.info(f"[StackLoopManager] Removendo stack da conta {account_id}")
                entry = self._stacks[account_id]
                entry.active = False
                del self._stacks[account_id]
                logger.info(f"[StackLoopManager] Stack removido. Total de stacks: {len(self._stacks)}")
            else:
                logger.warning(f"[StackLoopManager] Tentativa de remover stack inexistente: {account_id}")
    
    def _start_loop_thread(self) -> None:
        """Inicia a thread de processamento de loops."""
        if self._loop_thread is not None and self._loop_thread.is_alive():
            logger.warning("[StackLoopManager] Thread de loop já está rodando")
            return
        
        logger.info("[StackLoopManager] Iniciando thread de loop centralizado")
        self._stop_event.clear()
        self._loop_thread = threading.Thread(
            target=self._run_loop,
            name="StackLoopManager",
            daemon=True
        )
        self._loop_thread.start()
        logger.info(f"[StackLoopManager] Thread de loop iniciada: {self._loop_thread.ident}")
    
    def _run_loop(self) -> None:
        """
        Loop principal que processa todos os stacks registrados.
        
        Processa cada stack de forma não-bloqueante em round-robin.
        Também processa eventos asyncore de todas as conexões de rede.
        """
        logger.info("[StackLoopManager] Loop centralizado iniciado")
        
        while not self._stop_event.is_set():
            try:
                # Obtém lista de stacks ativos (com lock mínimo)
                stacks_to_process = []
                with self._lock:
                    stacks_to_process = [
                        (account_id, entry)
                        for account_id, entry in self._stacks.items()
                        if entry.active
                    ]
                
                # Se não há stacks, aguarda um pouco
                if not stacks_to_process:
                    time.sleep(0.1)
                    continue
                
                # Coleta todos os socket_maps de todos os dispatchers ativos
                combined_socket_map = {}
                for account_id, entry in stacks_to_process:
                    try:
                        # Obtém a interface da camada de rede do stack
                        network_interface = entry.stack.getLayerInterface(YowNetworkLayer)
                        if network_interface and hasattr(network_interface, '_layer'):
                            network_layer = network_interface._layer
                            if network_layer and hasattr(network_layer, '_dispatcher'):
                                dispatcher = network_layer._dispatcher
                                if isinstance(dispatcher, AsyncoreConnectionDispatcher):
                                    # Adiciona apenas sockets válidos e abertos ao mapa combinado
                                    if hasattr(dispatcher, 'socket_map') and dispatcher.socket_map:
                                        for sock, handler in dispatcher.socket_map.items():
                                            try:
                                                # Verifica se o socket ainda é válido antes de adicionar
                                                if sock.fileno() != -1:
                                                    combined_socket_map[sock] = handler
                                            except (OSError, ValueError, AttributeError):
                                                # Socket fechado ou inválido, remove do mapa original
                                                try:
                                                    if sock in dispatcher.socket_map:
                                                        del dispatcher.socket_map[sock]
                                                except:
                                                    pass
                    except Exception as e:
                        logger.debug(f"[StackLoopManager] Erro ao obter socket_map de {account_id}: {e}")
                
                # Processa eventos asyncore de todas as conexões (não-bloqueante)
                # Usa poll diretamente para evitar o sleep(0.2) bloqueante do loop()
                # Processa múltiplas vezes para garantir que eventos de conexão sejam tratados
                if combined_socket_map:
                    try:
                        # Filtra sockets fechados antes do poll para evitar WinError 10038
                        valid_socket_map = {}
                        for sock, handler in list(combined_socket_map.items()):
                            try:
                                # Verifica se o socket ainda é válido antes de adicionar
                                if sock.fileno() != -1:
                                    valid_socket_map[sock] = handler
                            except (OSError, ValueError, AttributeError):
                                # Socket fechado ou inválido, ignora
                                pass
                        
                        if valid_socket_map:
                            # Usa a mesma lógica do asyncore.loop() para escolher poll ou poll2
                            import select
                            use_poll = hasattr(select, 'poll')
                            # Processa até 3 vezes para garantir que eventos de conexão sejam tratados
                            for _ in range(3):
                                if use_poll:
                                    asyncore.poll2(timeout=0.0, map=valid_socket_map)
                                else:
                                    asyncore.poll(timeout=0.0, map=valid_socket_map)
                                # Se não há mais eventos pendentes, para
                                if not valid_socket_map:
                                    break
                    except Exception as e:
                        logger.debug(f"[StackLoopManager] Erro no asyncore.poll: {e}")
                
                # Processa cada stack
                for account_id, entry in stacks_to_process:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        # Envia evento de conexão na primeira vez
                        if not entry.connect_event_sent:
                            logger.debug(f"[StackLoopManager] Enviando evento de conexão para {account_id}")
                            entry.stack.broadcastEvent(
                                YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)
                            )
                            entry.connect_event_sent = True
                        
                        # Processa callbacks pendentes do stack (não-bloqueante)
                        entry.stack.loop()
                        
                    except Exception as e:
                        logger.error(
                            f"[StackLoopManager] Erro ao processar stack {account_id}: {e}",
                            exc_info=True
                        )
                        # Marca como inativo em caso de erro
                        entry.active = False
                
                # Pequeno delay entre ciclos para não consumir 100% CPU
                time.sleep(self._loop_interval)
                
            except Exception as e:
                logger.error(f"[StackLoopManager] Erro no loop principal: {e}", exc_info=True)
                time.sleep(0.1)
        
        logger.info("[StackLoopManager] Loop centralizado finalizado")
    
    def stop(self) -> None:
        """Para o loop de processamento."""
        logger.info("[StackLoopManager] Parando loop centralizado")
        self._stop_event.set()
        
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=5.0)
            if self._loop_thread.is_alive():
                logger.warning("[StackLoopManager] Thread de loop não terminou em 5 segundos")
            else:
                logger.info("[StackLoopManager] Thread de loop finalizada")
        
        with self._lock:
            self._stacks.clear()
    
    def get_stack_count(self) -> int:
        """Retorna o número de stacks registrados."""
        with self._lock:
            return len(self._stacks)
    
    def is_running(self) -> bool:
        """Verifica se o loop está rodando."""
        return self._loop_thread is not None and self._loop_thread.is_alive()

