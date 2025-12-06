"""
Exemplo de rotação automática de ambiente quando há erro de handshake.

Este exemplo demonstra como o sistema detecta automaticamente erros de
handshake e tenta diferentes tipos de ambiente (android, smb_android, ios, smb_ios)
até encontrar um que funcione.
"""

from app.account_manager import AccountManager
from loguru import logger
import time


def main():
    # Obtém o gerenciador
    manager = AccountManager.get_instance()
    
    logger.info("=== Exemplo: Conexão com rotação automática de ambiente ===")
    
    # Número da conta para testar
    account_phone = "5511999999999"  # Substitua pelo número da sua conta
    
    # Método 1: Usar connect_with_env_rotation do AccountManager
    logger.info("\n--- Método 1: connect_with_env_rotation ---")
    client = manager.connect_with_env_rotation(
        account_phone,
        initial_env="smb_android",  # Tenta este primeiro
        wait_login=True
    )
    
    if client and client.is_connected():
        logger.info(f"✓ Conta {account_phone} conectada com sucesso!")
        logger.info(f"Ambiente usado: {client.bot_env.deviceEnv.obj.__class__.__name__}")
    else:
        logger.error(f"✗ Falha ao conectar conta {account_phone}")
    
    # Método 2: Usar connect do ZowsupClient com retry_with_env_rotation=True
    logger.info("\n--- Método 2: connect com retry_with_env_rotation ---")
    
    # Remove a conta se já existe
    if account_phone in manager.list_accounts():
        manager.remove_account(account_phone, disconnect=True)
    
    try:
        client2 = manager.add_account(
            account_phone,
            env="android",  # Ambiente inicial
            auto_connect=False
        )
        
        # Conecta com rotação automática
        success = client2.connect(
            wait_login=True,
            retry_with_env_rotation=True  # Ativa rotação automática
        )
        
        if success and client2.is_connected():
            logger.info(f"✓ Conta {account_phone} conectada com rotação automática!")
        else:
            logger.error(f"✗ Falha ao conectar conta {account_phone}")
            
    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
    
    # Método 3: Carregar todas as contas e conectar com rotação
    logger.info("\n--- Método 3: Carregar todas e conectar com rotação ---")
    
    clients = manager.load_all_imported_accounts(
        auto_connect=False,
        only_initialized=True
    )
    
    logger.info(f"Carregadas {len(clients)} contas")
    
    connected_count = 0
    for phone, client in clients.items():
        try:
            logger.info(f"Conectando {phone} com rotação automática...")
            success = client.connect(
                wait_login=True,
                retry_with_env_rotation=True
            )
            
            if success and client.is_connected():
                connected_count += 1
                env_name = client.bot_env.deviceEnv.obj.__class__.__name__
                logger.info(f"  ✓ {phone} conectada (env: {env_name})")
            else:
                logger.warning(f"  ✗ {phone} falhou ao conectar")
                
        except Exception as e:
            logger.error(f"  ✗ Erro ao conectar {phone}: {e}")
    
    logger.info(f"\nTotal: {connected_count}/{len(clients)} contas conectadas")
    
    # Mantém conectado por um tempo
    logger.info("\nMantendo conexões ativas. Pressione Ctrl+C para desconectar e sair.")
    try:
        while True:
            time.sleep(60)
            # Verifica status
            active = sum(1 for c in clients.values() if c.is_connected())
            logger.info(f"Contas ativas: {active}/{len(clients)}")
    except KeyboardInterrupt:
        logger.info("\nDesconectando todas as contas...")
        manager.disconnect_all()
        logger.info("Todas as contas desconectadas.")


if __name__ == "__main__":
    main()

