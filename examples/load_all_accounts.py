"""
Exemplo de carregamento de todas as contas importadas.

Este exemplo demonstra como carregar todas as contas que foram
importadas no banco de dados e adicioná-las ao AccountManager.
"""

from app.account_manager import AccountManager
from app.db import get_all_imported_accounts
from loguru import logger
import time


def main():
    # Obtém o gerenciador
    manager = AccountManager.get_instance()
    
    logger.info("=== Exemplo 1: Listar todas as contas importadas ===")
    
    # Lista todas as contas do banco de dados (sem carregar no manager)
    all_accounts = get_all_imported_accounts()
    
    logger.info(f"Total de contas no banco de dados: {len(all_accounts)}")
    
    for account in all_accounts:
        logger.info(
            f"  - {account['phone']}: "
            f"pushname={account['pushname']}, "
            f"env={account['env']}, "
            f"logged_in={account['is_logged_in']}, "
            f"restriction={account['has_restriction']}, "
            f"initialized={account['is_initialized']}"
        )
    
    logger.info("\n=== Exemplo 2: Carregar todas as contas no AccountManager ===")
    
    # Carrega todas as contas (sem conectar)
    clients = manager.load_all_imported_accounts(auto_connect=False)
    
    logger.info(f"Contas carregadas no AccountManager: {len(clients)}")
    for phone, client in clients.items():
        logger.info(f"  - {phone}: cliente criado (conectado={client.is_connected()})")
    
    logger.info("\n=== Exemplo 3: Carregar apenas contas inicializadas ===")
    
    # Carrega apenas contas que já foram inicializadas
    initialized_clients = manager.load_all_imported_accounts(
        only_initialized=True,
        auto_connect=False
    )
    
    logger.info(f"Contas inicializadas carregadas: {len(initialized_clients)}")
    
    logger.info("\n=== Exemplo 4: Carregar apenas contas ativas sem restrição ===")
    
    # Carrega apenas contas que estão logadas e sem restrição
    active_clients = manager.load_all_imported_accounts(
        only_active=True,
        without_restriction=True,
        auto_connect=False
    )
    
    logger.info(f"Contas ativas sem restrição: {len(active_clients)}")
    
    logger.info("\n=== Exemplo 5: Carregar e conectar todas as contas ===")
    
    # Carrega todas as contas e conecta automaticamente
    # ATENÇÃO: Isso pode demorar bastante se houver muitas contas
    logger.info("Carregando e conectando todas as contas...")
    
    connected_clients = manager.load_all_imported_accounts(
        auto_connect=True,
        only_initialized=True  # Apenas contas inicializadas para evitar erros
    )
    
    logger.info(f"Contas conectadas: {len(connected_clients)}")
    
    # Lista status de conexão
    for phone, client in connected_clients.items():
        status = "conectado" if client.is_connected() else "desconectado"
        logger.info(f"  - {phone}: {status}")
    
    logger.info("\n=== Exemplo 6: Usar filtros combinados ===")
    
    # Carrega contas inicializadas, sem restrição, e com env específico
    filtered_clients = manager.load_all_imported_accounts(
        only_initialized=True,
        without_restriction=True,
        env="smb_android",  # Força usar smb_android mesmo se a conta tiver outro env
        auto_connect=False
    )
    
    logger.info(f"Contas filtradas carregadas: {len(filtered_clients)}")
    
    # Aguarda um pouco antes de desconectar
    logger.info("\nAguardando 5 segundos antes de desconectar...")
    time.sleep(5)
    
    # Desconecta todas as contas
    logger.info("Desconectando todas as contas...")
    manager.disconnect_all()
    
    logger.info("Exemplo concluído!")


if __name__ == "__main__":
    main()

