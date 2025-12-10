"""
Exemplo de uso do AccountManager para gerenciar múltiplas contas simultaneamente.

Este exemplo demonstra como:
1. Criar e gerenciar múltiplas contas isoladas
2. Enviar mensagens de diferentes contas
3. Configurar auto responder por conta
4. Monitorar o status de todas as contas
"""

from zowsuplib.app.account_manager import AccountManager
from loguru import logger


def main():
    # Obtém a instância singleton do AccountManager
    manager = AccountManager.get_instance()
    
    # Adiciona múltiplas contas
    logger.info("=== Adicionando contas ===")
    
    try:
        # Conta 1: Android
        client1 = manager.add_account(
            "5511999999999",
            env="android",
            auto_connect=True
        )
        logger.info(f"Conta 1 adicionada: {client1.get_account_id()}")
        
        # Conta 2: iOS
        client2 = manager.add_account(
            "5511888888888",
            env="ios",
            auto_connect=True
        )
        logger.info(f"Conta 2 adicionada: {client2.get_account_id()}")
        
        # Lista todas as contas
        logger.info(f"\n=== Contas ativas: {manager.list_accounts()} ===")
        
        # Verifica status de cada conta
        logger.info("\n=== Status das contas ===")
        for account_id in manager.list_accounts():
            client = manager.get_account(account_id)
            status = client.get_status()
            logger.info(f"Conta {account_id}: {status}")
        
        # Configura auto responder para a primeira conta
        logger.info("\n=== Configurando auto responder ===")
        client1.enable_auto_reply(
            "Olá! Esta é uma resposta automática da conta 1.",
            ignore_groups=True
        )
        logger.info("Auto responder habilitado para conta 1")
        
        # Envia mensagem da conta 1
        logger.info("\n=== Enviando mensagem da conta 1 ===")
        result = client1.send_text("5511777777777", "Olá da conta 1!")
        logger.info(f"Resultado: {result.data}")
        
        # Envia mensagem da conta 2
        logger.info("\n=== Enviando mensagem da conta 2 ===")
        result = client2.send_text("5511777777777", "Olá da conta 2!")
        logger.info(f"Resultado: {result.data}")
        
        # Aguarda um pouco para ver as mensagens sendo processadas
        import time
        logger.info("\n=== Aguardando 10 segundos... ===")
        time.sleep(10)
        
        # Verifica status novamente
        logger.info("\n=== Status final das contas ===")
        for account_id in manager.list_accounts():
            client = manager.get_account(account_id)
            status = client.get_status()
            logger.info(f"Conta {account_id}: {status}")
        
    except Exception as e:
        logger.error(f"Erro durante execução: {e}", exc_info=True)
    
    finally:
        # Desconecta todas as contas
        logger.info("\n=== Desconectando todas as contas ===")
        manager.disconnect_all()
        
        # Remove todas as contas
        logger.info("\n=== Removendo todas as contas ===")
        manager.remove_all(disconnect=False)  # Já desconectamos acima


if __name__ == "__main__":
    main()



