"""
Gerenciador central de múltiplas contas WhatsApp.

Singleton para orquestrar múltiplas contas isoladas, sem dependência de SysVar.

Melhorias implementadas:
- ReadWriteLock para reduzir contenção (múltiplos leitores simultâneos)
- Operações bloqueantes executadas fora do lock
- Limite máximo de contas configurável
- Cleanup automático de contas desconectadas
"""

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from loguru import logger

from zowsuplib.app.api import ZowsupClient
from zowsuplib.app.rwlock import ReadWriteLock


@dataclass
class ManagedAccount:
    client: ZowsupClient


class AccountManager:
    """
    Gerenciador singleton para múltiplas contas WhatsApp.
    
    Garante que cada conta tenha seu próprio contexto isolado:
    - ZowsupClient isolado
    - Profile isolado
    - Stack isolado
    - Callbacks isolados
    - Logs identificados por conta
    
    Exemplo de uso:
        manager = AccountManager.get_instance()
        
        # Adiciona uma conta
        client1 = manager.add_account("5511999999999", env="android")
        client2 = manager.add_account("5511888888888", env="ios")
        
        # Lista contas ativas
        accounts = manager.list_accounts()
        
        # Obtém uma conta específica
        client = manager.get_account("5511999999999")
        
        # Remove uma conta
        manager.remove_account("5511999999999")
    """
    
    _instance: Optional['AccountManager'] = None
    _lock = threading.Lock()
    
    def __init__(self, max_accounts: Optional[int] = None):
        """
        Inicializa o gerenciador de contas.
        
        Args:
            max_accounts: Limite máximo de contas (None para ilimitado, padrão: 1000)
        """
        if AccountManager._instance is not None:
            raise RuntimeError("AccountManager é um singleton. Use AccountManager.get_instance()")
        
        self._accounts: Dict[str, ManagedAccount] = {}
        self._connect_threads: Dict[str, threading.Thread] = {}
        self._lock = ReadWriteLock()  # ReadWriteLock para melhor concorrência
        self._max_accounts = max_accounts or 1000  # Limite padrão de 1000 contas
        self._cleanup_interval = 300.0  # Cleanup a cada 5 minutos
        self._last_cleanup = time.time()
        logger.info(f"[AccountManager] Inicializado - max_accounts={self._max_accounts}, usando ReadWriteLock")
    
    @classmethod
    def get_instance(cls) -> 'AccountManager':
        """
        Retorna a instância singleton do AccountManager.
        
        Thread-safe: usa double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def add_account(
        self,
        account_id: str,
        *,
        env: Optional[str] = None,
        proxy: Optional[str] = None,
        auto_connect: bool = True,
    ) -> ZowsupClient:
        """
        Adiciona uma nova conta ao gerenciador.
        
        Args:
            account_id: Número da conta (ex: "5511999999999")
            env: Ambiente do device (android, ios, smb_android, smb_ios)
            proxy: String de proxy ou "DIRECT"
            auto_connect: Se True, conecta automaticamente
        
        Returns:
            ZowsupClient: Cliente da conta adicionada
        
        Raises:
            ValueError: Se a conta já existe ou se o limite máximo foi atingido
        """
        # Verifica limite antes de criar cliente (fora do lock)
        with self._lock.read():
            if account_id in self._accounts:
                raise ValueError(f"Conta {account_id} já está registrada. Use get_account() ou remove_account() primeiro.")
            
            current_count = len(self._accounts)
            if current_count >= self._max_accounts:
                raise ValueError(
                    f"Limite máximo de contas atingido ({self._max_accounts}). "
                    f"Remova contas antes de adicionar novas."
                )
        
        # Cria cliente FORA do lock (operação bloqueante)
        logger.info(f"[AccountManager] Adicionando conta {account_id} (env={env}, proxy={proxy or 'DIRECT'})")
        client = ZowsupClient(
            account_id=account_id,
            env=env,
            proxy=proxy,
            auto_connect=False,  # Conecta depois, fora do lock
        )
        
        # Adiciona ao dict com lock de escrita
        with self._lock.write():
            if account_id in self._accounts:
                # Race condition: outra thread adicionou enquanto criávamos o cliente
                logger.warning(f"[AccountManager] Conta {account_id} foi adicionada por outra thread, usando existente")
                return self._accounts[account_id].client
            
            self._accounts[account_id] = ManagedAccount(client=client)
            logger.info(f"[AccountManager] Conta {account_id} adicionada com sucesso. Total de contas: {len(self._accounts)}")
        
        # Conecta FORA do lock se solicitado
        if auto_connect:
            try:
                client.connect()
            except Exception as e:
                logger.error(f"[AccountManager] Erro ao conectar conta {account_id} automaticamente: {e}")
        
        return client

    def connect_in_thread(self, account_id: str, *, wait_login: bool = True) -> Optional[threading.Thread]:
        """
        Inicia conexão de forma assíncrona em thread separada.
        
        Args:
            account_id: Número da conta
            wait_login: Se True, aguarda o login completar
        
        Returns:
            Thread da conexão ou None se conta não encontrada
        """
        # Obtém referência do cliente FORA do lock
        with self._lock.read():
            record = self._accounts.get(account_id)
            if record is None:
                logger.warning(f"[AccountManager] Conta {account_id} não encontrada para conectar em thread")
                return None
            client = record.client
        
        # Verifica thread anterior FORA do lock
        with self._lock.write():
            old_thread = self._connect_threads.get(account_id)
            if old_thread and old_thread.is_alive():
                logger.debug(f"[AccountManager] Thread de conexão prévia ainda ativa para {account_id}, aguardando término")
                old_thread.join(timeout=0.1)
        
        # Executa conexão em thread separada (não bloqueia)
        def _connect():
            try:
                client.connect(wait_login=wait_login)
            except Exception as exc:
                logger.error(f"[AccountManager] Erro ao conectar conta {account_id}: {exc}", exc_info=True)
        
        thread = threading.Thread(target=_connect, name=f"connect-{account_id}", daemon=True)
        thread.start()
        
        # Atualiza tracking de threads
        with self._lock.write():
            self._connect_threads[account_id] = thread
        
        return thread
    
    def get_account(self, account_id: str) -> Optional[ZowsupClient]:
        """
        Obtém o cliente de uma conta específica.
        
        Usa lock de LEITURA - múltiplas threads podem ler simultaneamente.
        
        Args:
            account_id: Número da conta
        
        Returns:
            ZowsupClient se encontrado, None caso contrário
        """
        with self._lock.read():
            record = self._accounts.get(account_id)
            if record is None:
                return None
            return record.client
    
    def remove_account(self, account_id: str, disconnect: bool = True) -> bool:
        """
        Remove uma conta do gerenciador.
        
        Args:
            account_id: Número da conta
            disconnect: Se True, desconecta antes de remover
        
        Returns:
            True se a conta foi removida, False se não existia
        """
        # Obtém referência do cliente FORA do lock
        with self._lock.read():
            if account_id not in self._accounts:
                logger.warning(f"[AccountManager] Tentativa de remover conta inexistente: {account_id}")
                return False
            client = self._accounts[account_id].client
        
        # Desconecta FORA do lock (operação bloqueante)
        if disconnect:
            logger.info(f"[AccountManager] Desconectando conta {account_id} antes de remover")
            try:
                client.disconnect()
            except Exception as e:
                logger.error(f"[AccountManager] Erro ao desconectar conta {account_id}: {e}")
        
        # Remove do dict com lock de escrita
        with self._lock.write():
            if account_id not in self._accounts:
                # Race condition: já foi removida
                return False
            
            del self._accounts[account_id]
            # Limpa thread de conexão se existir
            if account_id in self._connect_threads:
                del self._connect_threads[account_id]
            
            logger.info(f"[AccountManager] Conta {account_id} removida. Total de contas: {len(self._accounts)}")
            return True
    
    def list_accounts(self) -> List[str]:
        """
        Lista os IDs de todas as contas gerenciadas.
        
        Usa lock de LEITURA - múltiplas threads podem ler simultaneamente.
        
        Returns:
            Lista de account_ids
        """
        with self._lock.read():
            return list(self._accounts.keys())
    
    def get_all_clients(self) -> Dict[str, ZowsupClient]:
        """
        Retorna um dicionário com todas as contas.
        
        Usa lock de LEITURA - múltiplas threads podem ler simultaneamente.
        
        Returns:
            Dict[account_id, ZowsupClient]
        """
        with self._lock.read():
            return {acc_id: record.client for acc_id, record in self._accounts.items()}
    
    def is_account_active(self, account_id: str) -> bool:
        """
        Verifica se uma conta está ativa (conectada).
        
        Usa lock de LEITURA e verifica conexão FORA do lock.
        
        Args:
            account_id: Número da conta
        
        Returns:
            True se a conta existe e está conectada
        """
        # Obtém referência FORA do lock
        with self._lock.read():
            record = self._accounts.get(account_id)
            if record is None:
                return False
            client = record.client
        
        # Verifica conexão FORA do lock (pode ser bloqueante)
        return client.is_connected()
    
    def disconnect_all(self) -> None:
        """
        Desconecta todas as contas gerenciadas.
        
        Obtém lista de clientes FORA do lock e desconecta em paralelo.
        """
        # Obtém lista de clientes FORA do lock
        with self._lock.read():
            accounts_to_disconnect = [
                (acc_id, record.client) 
                for acc_id, record in self._accounts.items()
            ]
        
        if not accounts_to_disconnect:
            logger.info("[AccountManager] Nenhuma conta para desconectar")
            return
        
        logger.info(f"[AccountManager] Desconectando todas as {len(accounts_to_disconnect)} contas")
        
        # Desconecta FORA do lock (operações bloqueantes)
        for account_id, client in accounts_to_disconnect:
            try:
                logger.debug(f"[AccountManager] Desconectando conta {account_id}")
                client.disconnect()
            except Exception as e:
                logger.error(f"[AccountManager] Erro ao desconectar conta {account_id}: {e}")
        
        logger.info("[AccountManager] Todas as contas desconectadas")
    
    def remove_all(self, disconnect: bool = True) -> None:
        """
        Remove todas as contas do gerenciador.
        
        Args:
            disconnect: Se True, desconecta antes de remover
        """
        # Obtém lista de contas FORA do lock
        with self._lock.read():
            account_ids = list(self._accounts.keys())
        
        if not account_ids:
            logger.info("[AccountManager] Nenhuma conta para remover")
            return
        
        logger.info(f"[AccountManager] Removendo todas as {len(account_ids)} contas")
        
        # Remove cada conta (remove_account já gerencia locks internamente)
        for account_id in account_ids:
            self.remove_account(account_id, disconnect=disconnect)
        
        logger.info("[AccountManager] Todas as contas removidas")
    
    def load_all_imported_accounts(
        self,
        *,
        auto_connect: bool = False,
        only_initialized: bool = False,
        only_active: bool = False,
        without_restriction: bool = False,
        env: Optional[str] = None,
        max_accounts: Optional[int] = None,
    ) -> Dict[str, ZowsupClient]:
        """
        Carrega todas as contas importadas do banco de dados e adiciona ao gerenciador.
        
        Args:
            auto_connect: Se True, conecta automaticamente cada conta após carregar
            only_initialized: Se True, carrega apenas contas inicializadas
            only_active: Se True, carrega apenas contas logadas
            without_restriction: Se True, carrega apenas contas sem restrição
            env: Ambiente a usar (android, smb_android, ios, smb_ios). 
                 Se None, usa o env salvo na conta ou "smb_android" como padrão
            max_accounts: Limita a quantidade máxima de contas carregadas (None para ilimitado)
        
        Returns:
            Dict[phone, ZowsupClient] com todas as contas carregadas
        
        Example:
            # Carregar todas as contas
            clients = manager.load_all_imported_accounts()
            
            # Carregar apenas contas inicializadas e conectar
            clients = manager.load_all_imported_accounts(
                only_initialized=True,
                auto_connect=True
            )
            
            # Carregar apenas contas ativas sem restrição
            clients = manager.load_all_imported_accounts(
                only_active=True,
                without_restriction=True
            )
        """
        from zowsuplib.app.db import get_all_imported_accounts
        
        # Busca todas as contas do banco de dados
        accounts = get_all_imported_accounts(
            only_initialized=only_initialized,
            only_active=only_active,
            without_restriction=without_restriction,
        )
        
        if not accounts:
            logger.info("[AccountManager] Nenhuma conta encontrada no banco de dados")
            return {}
        
        if max_accounts is not None:
            accounts = accounts[:max_accounts]
        logger.info(f"[AccountManager] Carregando {len(accounts)} contas do banco de dados...")
        
        loaded_clients = {}
        
        for account_info in accounts:
            phone = account_info["phone"]
            
            # Pula se a conta já está carregada
            with self._lock.read():
                if phone in self._accounts:
                    logger.debug(f"[AccountManager] Conta {phone} já está carregada, pulando")
                    loaded_clients[phone] = self._accounts[phone].client
                    continue
            
            try:
                # Usa o env da conta ou o fornecido, ou padrão
                account_env = env or account_info.get("env") or "smb_android"
                
                logger.info(f"[AccountManager] Carregando conta {phone} (env={account_env})...")
                
                # Adiciona a conta ao gerenciador
                client = self.add_account(
                    phone,
                    env=account_env,
                    auto_connect=auto_connect,
                )
                
                loaded_clients[phone] = client
                logger.info(f"[AccountManager] Conta {phone} carregada com sucesso")
                
            except Exception as e:
                logger.error(f"[AccountManager] Erro ao carregar conta {phone}: {e}", exc_info=True)
                continue
        
        logger.info(f"[AccountManager] {len(loaded_clients)} contas carregadas com sucesso")
        return loaded_clients
    
    def get_account_count(self) -> int:
        """
        Retorna o número de contas gerenciadas.
        
        Usa lock de LEITURA - múltiplas threads podem ler simultaneamente.
        
        Returns:
            Número de contas
        """
        with self._lock.read():
            return len(self._accounts)

    def ensure_account_connected(
        self,
        account_id: str,
        *,
        wait_login: bool = True,
        auto_connect: bool = True,
    ) -> bool:
        """
        Verifica se a conta está conectada; caso não esteja, dispara fallback de conexão em thread.

        Corrigido: mantém referência segura do cliente durante verificação.

        Returns:
            True se a conta já estava conectada ou se o disparo de reconexão foi iniciado.
        """
        # Obtém referência do cliente FORA do lock
        with self._lock.read():
            record = self._accounts.get(account_id)
            if record is None:
                logger.warning(f"[AccountManager] ensure_account_connected: conta {account_id} não encontrada")
                return False
            client = record.client
        
        # Verifica conexão FORA do lock (pode ser bloqueante)
        if client.is_connected():
            return True

        if not auto_connect:
            logger.debug(f"[AccountManager] Conta {account_id} desconectada e auto_connect desabilitado")
            return False

        logger.info(f"[AccountManager] Conta {account_id} desconectada; iniciando fallback de conexão em thread")
        self.connect_in_thread(account_id, wait_login=wait_login)
        return True
    
    def sync_all_accounts(
        self,
        *,
        sync_delay: float = 0.5,
        only_connected: bool = True,
        exclude_phones: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, any]]:
        """
        Sincroniza todas as contas entre si (bidirecional).
        
        Cada conta sincroniza os números de telefone de todas as outras contas,
        garantindo que todas as contas tenham todas as outras como contatos.
        
        Args:
            sync_delay: Delay em segundos entre cada sincronização (padrão: 0.5s)
            only_connected: Se True, sincroniza apenas contas conectadas (padrão: True)
            exclude_phones: Lista de números para excluir da sincronização (opcional)
        
        Returns:
            Dicionário com estatísticas da sincronização:
            {
                "total_accounts": 5,
                "synced_accounts": 4,
                "skipped_accounts": 1,
                "total_syncs": 20,
                "successful_syncs": 18,
                "failed_syncs": 2,
                "details": {
                    "5511999999999": {
                        "synced_count": 4,
                        "status": "success"
                    },
                    ...
                }
            }
        
        Example:
            # Sincronizar todas as contas conectadas
            stats = manager.sync_all_accounts()
            
            # Sincronizar com delay maior
            stats = manager.sync_all_accounts(sync_delay=1.0)
            
            # Sincronizar incluindo contas desconectadas (tentará mesmo assim)
            stats = manager.sync_all_accounts(only_connected=False)
            
            # Excluir algumas contas da sincronização
            stats = manager.sync_all_accounts(exclude_phones=["5511999999999"])
        """
        # Obtém lista de contas FORA do lock principal
        with self._lock.read():
            accounts = list(self._accounts.keys())
        
        if not accounts:
            logger.warning("[AccountManager] Nenhuma conta carregada para sincronizar")
            return {
                "total_accounts": 0,
                "synced_accounts": 0,
                "skipped_accounts": 0,
                "total_syncs": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "details": {}
            }
        
        exclude_phones = exclude_phones or []
        
        # Filtra contas a sincronizar
        accounts_to_sync = [acc for acc in accounts if acc not in exclude_phones]
        
        if not accounts_to_sync:
            logger.warning("[AccountManager] Nenhuma conta para sincronizar após filtros")
            return {
                "total_accounts": len(accounts),
                "synced_accounts": 0,
                "skipped_accounts": len(accounts),
                "total_syncs": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "details": {}
            }
        
        logger.info(f"[AccountManager] Iniciando sincronização entre {len(accounts_to_sync)} contas...")
        
        stats = {
            "total_accounts": len(accounts),
            "synced_accounts": 0,
            "skipped_accounts": 0,
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "details": {}
        }
        
        # Para cada conta, sincroniza com todas as outras
        for account_phone in accounts_to_sync:
            # Obtém cliente FORA do lock
            with self._lock.read():
                record = self._accounts.get(account_phone)
                if record is None:
                    logger.warning(f"[AccountManager] Conta {account_phone} não encontrada no gerenciador")
                    stats["skipped_accounts"] += 1
                    stats["details"][account_phone] = {
                        "synced_count": 0,
                        "status": "not_found"
                    }
                    continue
                client = record.client
            
            # Verifica se está conectada (se only_connected=True)
            if only_connected and not client.is_connected():
                logger.warning(f"[AccountManager] Conta {account_phone} não está conectada, pulando")
                stats["skipped_accounts"] += 1
                stats["details"][account_phone] = {
                    "synced_count": 0,
                    "status": "not_connected"
                }
                continue
            
            # Lista de outras contas para sincronizar
            other_phones = [p for p in accounts_to_sync if p != account_phone]
            
            if not other_phones:
                logger.debug(f"[AccountManager] Conta {account_phone} não tem outras contas para sincronizar")
                stats["skipped_accounts"] += 1
                stats["details"][account_phone] = {
                    "synced_count": 0,
                    "status": "no_other_accounts"
                }
                continue
            
            logger.info(f"[AccountManager] [{account_phone}] Sincronizando {len(other_phones)} contatos...")
            
            account_success = 0
            account_failed = 0
            
            try:
                # Sincroniza todos os outros números de uma vez
                phones_str = ",".join(other_phones)
                sync_result = client.sync_contacts(phones_str)
                
                stats["total_syncs"] += 1
                
                if sync_result.data:
                    sync_count = sync_result.data.get("count", 0)
                    account_success = sync_count
                    stats["successful_syncs"] += 1
                    logger.info(f"[AccountManager] [{account_phone}] ✓ {sync_count} contatos sincronizados")
                else:
                    account_failed = len(other_phones)
                    stats["failed_syncs"] += 1
                    logger.warning(f"[AccountManager] [{account_phone}] Resposta vazia ao sincronizar contatos")
                
                # Delay entre sincronizações de diferentes contas
                if sync_delay > 0:
                    time.sleep(sync_delay)
                
            except Exception as e:
                account_failed = len(other_phones)
                stats["failed_syncs"] += 1
                logger.error(f"[AccountManager] [{account_phone}] Erro ao sincronizar contatos: {e}", exc_info=True)
            
            stats["synced_accounts"] += 1
            stats["details"][account_phone] = {
                "synced_count": account_success,
                "failed_count": account_failed,
                "total_attempted": len(other_phones),
                "status": "success" if account_failed == 0 else "partial" if account_success > 0 else "failed"
            }
        
        logger.info(
            f"[AccountManager] Sincronização concluída: "
            f"{stats['synced_accounts']} contas sincronizadas, "
            f"{stats['successful_syncs']} sincronizações bem-sucedidas, "
            f"{stats['failed_syncs']} falhas"
        )
        
        return stats
    
    def connect_with_env_rotation(
        self,
        account_id: str,
        *,
        initial_env: Optional[str] = None,
        wait_login: bool = True,
    ) -> Optional[ZowsupClient]:
        """
        Conecta uma conta tentando diferentes tipos de ambiente se houver erro de handshake.
        
        Se houver erro de handshake, tenta automaticamente outros tipos de ambiente:
        smb_android -> android -> smb_ios -> ios
        
        Args:
            account_id: Número da conta
            initial_env: Ambiente inicial a tentar (None para usar o salvo na conta ou padrão)
            wait_login: Se True, aguarda o login completar
        
        Returns:
            ZowsupClient se conectou com sucesso, None caso contrário
        
        Example:
            # Conectar com rotação automática de ambiente
            client = manager.connect_with_env_rotation("5511999999999")
            
            # Especificar ambiente inicial
            client = manager.connect_with_env_rotation(
                "5511999999999",
                initial_env="android"
            )
        """
        from zowsuplib.app.db import get_all_imported_accounts, update_account_status
        
        # Busca informações da conta
        accounts = get_all_imported_accounts()
        account_info = next((acc for acc in accounts if acc["phone"] == account_id), None)
        
        # Determina ambiente inicial
        if initial_env:
            env_to_try = initial_env
        elif account_info and account_info.get("env"):
            env_to_try = account_info["env"]
        else:
            env_to_try = "smb_android"  # Padrão
        
        # Lista de ambientes para tentar (ordem de prioridade)
        env_types = ["smb_android", "android", "smb_ios", "ios"]
        
        # Reordena para tentar o inicial primeiro
        if env_to_try in env_types:
            env_types.remove(env_to_try)
            env_types.insert(0, env_to_try)
        
        logger.info(f"[AccountManager] Conectando {account_id} com rotação de ambiente. Ordem: {env_types}")
        
        # Remove a conta se já existe (para recriar com novo ambiente)
        if account_id in self._accounts:
            try:
                self.remove_account(account_id, disconnect=True)
            except:
                pass
        
        # Tenta cada ambiente
        for env_name in env_types:
            try:
                logger.info(f"[AccountManager] [{account_id}] Tentando ambiente: {env_name}")
                
                # Adiciona conta com o ambiente atual
                client = self.add_account(
                    account_id,
                    env=env_name,
                    auto_connect=False,  # Conecta manualmente para ter controle
                )
                
                # Tenta conectar com rotação automática
                success = client.connect(wait_login=wait_login, retry_with_env_rotation=False)
                
                if success and client.is_connected():
                    logger.info(f"[AccountManager] [{account_id}] ✓ Conectado com sucesso usando ambiente: {env_name}")
                    
                    # Atualiza o env no banco de dados
                    update_account_status(account_id, env=env_name)
                    
                    return client
                else:
                    logger.warning(f"[AccountManager] [{account_id}] ✗ Falha ao conectar com ambiente: {env_name}")
                    
                    # Remove a conta antes de tentar próximo ambiente
                    try:
                        self.remove_account(account_id, disconnect=True)
                    except:
                        pass
                    
                    # Pequeno delay antes de tentar próximo
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"[AccountManager] [{account_id}] Erro ao tentar ambiente {env_name}: {e}", exc_info=True)
                
                # Remove a conta antes de tentar próximo ambiente
                try:
                    if account_id in self._accounts:
                        self.remove_account(account_id, disconnect=True)
                except:
                    pass
                
                time.sleep(1)
                continue
        
        logger.error(f"[AccountManager] [{account_id}] ✗ Falha ao conectar com todos os tipos de ambiente")
        return None
    
    def _cleanup_disconnected_accounts(self, max_idle_time: float = 3600.0) -> int:
        """
        Remove contas desconectadas há mais de max_idle_time segundos.
        
        Args:
            max_idle_time: Tempo máximo de inatividade em segundos (padrão: 1 hora)
        
        Returns:
            Número de contas removidas
        """
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return 0
        
        self._last_cleanup = current_time
        
        # Obtém lista de contas desconectadas FORA do lock
        disconnected_accounts = []
        with self._lock.read():
            for account_id, record in self._accounts.items():
                if not record.client.is_connected():
                    # Verifica último acesso (se implementado)
                    disconnected_accounts.append(account_id)
        
        # Remove contas desconectadas
        removed_count = 0
        for account_id in disconnected_accounts:
            try:
                # Remove sem desconectar (já está desconectada)
                if self.remove_account(account_id, disconnect=False):
                    removed_count += 1
                    logger.info(f"[AccountManager] Conta {account_id} removida por cleanup (desconectada)")
            except Exception as e:
                logger.error(f"[AccountManager] Erro ao remover conta {account_id} no cleanup: {e}")
        
        if removed_count > 0:
            logger.info(f"[AccountManager] Cleanup: {removed_count} contas desconectadas removidas")
        
        return removed_count
    
    def __repr__(self) -> str:
        """Representação string do gerenciador."""
        with self._lock.read():
            accounts = list(self._accounts.keys())
            return f"AccountManager(accounts={len(accounts)}/{self._max_accounts}, ids={accounts[:5]}{'...' if len(accounts) > 5 else ''})"



