"""
Gerenciador centralizado de processamento de commands.

Gerencia uma única thread para processar resultados de commands de todas as contas,
reduzindo o número de threads do sistema e melhorando a eficiência.
"""

import threading
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class CommandEntry:
    """Entrada na lista de commands para processamento."""
    account_id: str
    cmd_id: str
    event: threading.Event
    wait_time: float  # Tempo máximo de espera em segundos
    start_time: float  # Timestamp de quando o comando foi iniciado
    result_callback: Optional[Callable[[Any, Optional[Dict[str, Any]]], None]] = None
    active: bool = True


class CommandManager:
    """
    Gerenciador singleton que processa resultados de commands em uma única thread.
    
    Ao invés de cada conta bloquear sua própria thread aguardando resultados de commands,
    este manager mantém uma lista de commands pendentes e os processa em uma única thread
    dedicada, verificando eventos e timeouts de forma não-bloqueante.
    """
    
    _instance: Optional['CommandManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Inicializa o gerenciador de commands."""
        if CommandManager._instance is not None:
            raise RuntimeError("CommandManager é um singleton. Use CommandManager.get_instance()")
        
        self._commands: Dict[str, CommandEntry] = {}  # cmd_id -> CommandEntry
        self._manager_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._check_interval = 0.1  # Verifica a cada 100ms
        
        logger.info("[CommandManager] Inicializado - pronto para gerenciar commands")
    
    @classmethod
    def get_instance(cls) -> 'CommandManager':
        """
        Retorna a instância singleton do CommandManager.
        
        Thread-safe: usa double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def register_command(
        self,
        account_id: str,
        cmd_id: str,
        event: threading.Event,
        wait_time: float,
        result_callback: Optional[Callable[[Any, Optional[Dict[str, Any]]], None]] = None
    ) -> None:
        """
        Registra um comando para processamento no loop centralizado.
        
        O CommandManager monitora o comando e limpa automaticamente quando expira,
        mas o wait_result() ainda pode bloquear normalmente para manter compatibilidade.
        
        Args:
            account_id: ID da conta
            cmd_id: ID do comando
            event: Evento que será sinalizado quando o resultado chegar
            wait_time: Tempo máximo de espera em segundos
            result_callback: Callback opcional chamado quando timeout ocorrer (não usado se resultado chegar)
        """
        with self._lock:
            if cmd_id in self._commands:
                logger.debug(f"[CommandManager] Command {cmd_id} já registrado, atualizando")
            
            logger.debug(f"[CommandManager] Registrando command {cmd_id} para conta {account_id} (wait_time={wait_time}s)")
            self._commands[cmd_id] = CommandEntry(
                account_id=account_id,
                cmd_id=cmd_id,
                event=event,
                wait_time=wait_time,
                start_time=time.time(),
                result_callback=result_callback,
                active=True
            )
            
            # Inicia a thread do manager se ainda não estiver rodando
            if self._manager_thread is None or not self._manager_thread.is_alive():
                self._start_manager_thread()
            
            logger.debug(f"[CommandManager] Command registrado. Total de commands: {len(self._commands)}")
    
    def unregister_command(self, cmd_id: str) -> None:
        """
        Remove um comando do processamento.
        
        Args:
            cmd_id: ID do comando a ser removido
        """
        with self._lock:
            if cmd_id in self._commands:
                entry = self._commands.pop(cmd_id)
                entry.active = False
                logger.debug(f"[CommandManager] Command {cmd_id} removido. Total de commands: {len(self._commands)}")
            else:
                logger.debug(f"[CommandManager] Tentativa de remover command inexistente: {cmd_id}")
    
    def is_command_pending(self, cmd_id: str) -> bool:
        """
        Verifica se um comando está pendente.
        
        Args:
            cmd_id: ID do comando
            
        Returns:
            True se o comando está pendente, False caso contrário
        """
        with self._lock:
            return cmd_id in self._commands and self._commands[cmd_id].active
    
    def _start_manager_thread(self) -> None:
        """Inicia a thread de processamento de commands."""
        if self._manager_thread is not None and self._manager_thread.is_alive():
            logger.warning("[CommandManager] Thread do manager já está rodando")
            return
        
        logger.info("[CommandManager] Iniciando thread do gerenciador de commands")
        self._stop_event.clear()
        self._manager_thread = threading.Thread(
            target=self._run_manager_loop,
            name="CommandManager",
            daemon=True
        )
        self._manager_thread.start()
        logger.info(f"[CommandManager] Thread do manager iniciada: {self._manager_thread.ident}")
    
    def _run_manager_loop(self) -> None:
        """
        Loop principal que processa todos os commands registrados.
        
        Verifica eventos e timeouts de forma não-bloqueante.
        """
        logger.info("[CommandManager] Loop do gerenciador de commands iniciado")
        
        while not self._stop_event.is_set():
            try:
                # Obtém lista de commands ativos (com lock mínimo)
                commands_to_check = []
                with self._lock:
                    commands_to_check = [
                        entry
                        for entry in self._commands.values()
                        if entry.active
                    ]
                
                # Se não há commands, aguarda um pouco
                if not commands_to_check:
                    self._stop_event.wait(self._check_interval)
                    continue
                
                current_time = time.time()
                completed_commands = []
                
                # Verifica cada comando
                for entry in commands_to_check:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        # Verifica se o evento foi sinalizado (resultado chegou)
                        if entry.event.is_set():
                            logger.debug(f"[CommandManager] Command {entry.cmd_id} completado (evento sinalizado)")
                            completed_commands.append(entry.cmd_id)
                            continue
                        
                        # Verifica timeout
                        elapsed_time = current_time - entry.start_time
                        if elapsed_time >= entry.wait_time:
                            # Timeout: apenas loga, não interfere com wait_result() que já trata timeout
                            logger.debug(
                                f"[CommandManager] Command {entry.cmd_id} expirou após {elapsed_time:.2f}s "
                                f"(timeout={entry.wait_time}s) - será limpo automaticamente"
                            )
                            # Chama callback se fornecido (para notificação de timeout)
                            if entry.result_callback:
                                try:
                                    entry.result_callback(None, {"code": -5, "msg": "Command timeout"})
                                except Exception as e:
                                    logger.debug(f"[CommandManager] Erro no callback de timeout para {entry.cmd_id}: {e}")
                            completed_commands.append(entry.cmd_id)
                            continue
                        
                    except Exception as e:
                        logger.error(
                            f"[CommandManager] Erro ao verificar command {entry.cmd_id}: {e}",
                            exc_info=True
                        )
                        completed_commands.append(entry.cmd_id)
                
                # Remove commands completados
                for cmd_id in completed_commands:
                    self.unregister_command(cmd_id)
                
                # Pequeno delay para não consumir 100% CPU
                self._stop_event.wait(self._check_interval)
                
            except Exception as e:
                logger.error(f"[CommandManager] Erro no loop principal: {e}", exc_info=True)
                self._stop_event.wait(0.1)
        
        logger.info("[CommandManager] Loop do gerenciador de commands finalizado")
    
    def stop(self) -> None:
        """Para o loop de processamento."""
        logger.info("[CommandManager] Parando gerenciador de commands")
        self._stop_event.set()
        
        if self._manager_thread is not None:
            self._manager_thread.join(timeout=2.0)
            if self._manager_thread.is_alive():
                logger.warning("[CommandManager] Thread do manager não terminou em 2 segundos")
            else:
                logger.info("[CommandManager] Thread do manager finalizada")
        
        with self._lock:
            self._commands.clear()
    
    def get_command_count(self) -> int:
        """Retorna o número de commands registrados."""
        with self._lock:
            return len(self._commands)
    
    def is_running(self) -> bool:
        """Verifica se o manager está rodando."""
        return self._manager_thread is not None and self._manager_thread.is_alive()

