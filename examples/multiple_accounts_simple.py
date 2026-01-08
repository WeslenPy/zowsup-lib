"""
Exemplo simples: conectar duas contas simultaneamente.

Versão simplificada do exemplo completo.
"""

from loguru import logger
from zowsuplib.app.account_manager import AccountManager


def main():
    """Exemplo simples de duas contas simultâneas."""
    
    # Obtém o gerenciador
    manager = AccountManager.get_instance()
    
    # IDs das contas (substitua pelos seus números)
    account1 = "5511999999999"
    account2 = "5511888888888"
    
    try:
        # Adiciona e conecta primeira conta
        logger.info(f"Conectando conta 1: {account1}")
        client1 = manager.add_account(account1, env="android", auto_connect=True)
        
        # Adiciona e conecta segunda conta
        logger.info(f"Conectando conta 2: {account2}")
        client2 = manager.add_account(account2, env="android", auto_connect=True)
        
        # Aguarda um pouco para garantir que as conexões foram estabelecidas
        import time
        time.sleep(5)
        
        # Verifica status
        logger.info(f"Conta 1 online: {client1.is_online()}")
        logger.info(f"Conta 2 online: {client2.is_online()}")
        
        # Exemplo: envia mensagem da conta 1
        # client1.send_text("5511777777777", "Olá da conta 1!")
        
        # Mantém rodando
        logger.info("Contas conectadas. Pressione Ctrl+C para sair.")
        while True:
            time.sleep(60)
            logger.info("Contas ainda online...")
            
    except KeyboardInterrupt:
        logger.info("Desconectando...")
    finally:
        manager.disconnect_all()
        manager.remove_all()


if __name__ == "__main__":
    main()

