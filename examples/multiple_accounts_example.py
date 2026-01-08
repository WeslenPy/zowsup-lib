"""
Exemplo de uso do AccountManager para conectar múltiplas contas simultaneamente.

Este exemplo demonstra como usar o sistema de thread única para gerenciar
múltiplas contas WhatsApp de forma eficiente.
"""

import time
from loguru import logger
from zowsuplib.app.account_manager import AccountManager


def message_callback(account_id: str, message_type: int, from_jid: str, message_data: dict):
    """
    Callback personalizado para receber mensagens de qualquer conta.
    
    Args:
        account_id: ID da conta que recebeu a mensagem
        message_type: Tipo da mensagem (1=text, 5=media, etc.)
        from_jid: JID do remetente
        message_data: Dados da mensagem
    """
    if message_type == 1:  # Text message
        text = message_data.get('text', '')
        logger.info(f"[{account_id}] Mensagem de {from_jid}: {text}")
    elif message_type == 5:  # Media message
        media_type = message_data.get('media_type', 'unknown')
        logger.info(f"[{account_id}] Mídia recebida de {from_jid}: {media_type}")


def main():
    """
    Exemplo principal: conecta duas contas simultaneamente.
    """
    logger.info("=" * 60)
    logger.info("Exemplo: Conectando múltiplas contas simultaneamente")
    logger.info("=" * 60)
    
    # Obtém o gerenciador singleton
    manager = AccountManager.get_instance()
    
    # IDs das contas (substitua pelos seus números)
    account1_id = "5511999999999"  # Substitua pelo número real
    account2_id = "5511888888888"  # Substitua pelo número real
    
    try:
        # ============================================================
        # PASSO 1: Adiciona as contas ao gerenciador
        # ============================================================
        logger.info("\n[PASSO 1] Adicionando contas ao gerenciador...")
        
        # Adiciona primeira conta
        logger.info(f"Adicionando conta 1: {account1_id}")
        client1 = manager.add_account(
            account_id=account1_id,
            env="android",  # ou "ios", "smb_android", "smb_ios"
            auto_connect=False  # Vamos conectar manualmente
        )
        
        # Configura callback personalizado para a primeira conta
        client1.set_message_callback(
            lambda msg_type, from_jid, msg_data: message_callback(account1_id, msg_type, from_jid, msg_data)
        )
        
        # Adiciona segunda conta
        logger.info(f"Adicionando conta 2: {account2_id}")
        client2 = manager.add_account(
            account_id=account2_id,
            env="android",  # ou "ios", "smb_android", "smb_ios"
            auto_connect=False  # Vamos conectar manualmente
        )
        
        # Configura callback personalizado para a segunda conta
        client2.set_message_callback(
            lambda msg_type, from_jid, msg_data: message_callback(account2_id, msg_type, from_jid, msg_data)
        )
        
        logger.info(f"✓ {len(manager.list_accounts())} contas adicionadas")
        
        # ============================================================
        # PASSO 2: Conecta as contas simultaneamente
        # ============================================================
        logger.info("\n[PASSO 2] Conectando contas simultaneamente...")
        
        # Conecta primeira conta
        logger.info(f"Conectando conta 1: {account1_id}")
        success1 = client1.connect(wait_login=True)
        
        if success1:
            logger.info(f"✓ Conta 1 ({account1_id}) conectada com sucesso!")
            logger.info(f"  - Online: {client1.is_online()}")
            logger.info(f"  - Conectada: {client1.is_connected()}")
        else:
            logger.error(f"✗ Falha ao conectar conta 1 ({account1_id})")
            return
        
        # Conecta segunda conta
        logger.info(f"Conectando conta 2: {account2_id}")
        success2 = client2.connect(wait_login=True)
        
        if success2:
            logger.info(f"✓ Conta 2 ({account2_id}) conectada com sucesso!")
            logger.info(f"  - Online: {client2.is_online()}")
            logger.info(f"  - Conectada: {client2.is_connected()}")
        else:
            logger.error(f"✗ Falha ao conectar conta 2 ({account2_id})")
            return
        
        # ============================================================
        # PASSO 3: Verifica status das contas
        # ============================================================
        logger.info("\n[PASSO 3] Verificando status das contas...")
        
        accounts = manager.list_accounts()
        logger.info(f"Total de contas gerenciadas: {len(accounts)}")
        
        for account_id in accounts:
            client = manager.get_account(account_id)
            if client:
                status = client.get_connection_status()
                logger.info(f"\nConta: {account_id}")
                logger.info(f"  - Online: {status['online']}")
                logger.info(f"  - Conectada: {status['connected']}")
                logger.info(f"  - Iniciada: {status['started']}")
                logger.info(f"  - Stack ativo: {status['stack_thread_alive']}")
        
        # ============================================================
        # PASSO 4: Envia mensagens de teste (opcional)
        # ============================================================
        logger.info("\n[PASSO 4] Enviando mensagens de teste...")
        
        # Envia mensagem da conta 1 para a conta 2
        test_phone = "5511777777777"  # Substitua por um número de teste
        logger.info(f"Enviando mensagem da conta 1 para {test_phone}")
        result1 = client1.send_text(test_phone, "Olá! Esta é uma mensagem da conta 1.")
        logger.info(f"  Resultado: {result1}")
        
        # Envia mensagem da conta 2 para a conta 1
        logger.info(f"Enviando mensagem da conta 2 para {test_phone}")
        result2 = client2.send_text(test_phone, "Olá! Esta é uma mensagem da conta 2.")
        logger.info(f"  Resultado: {result2}")
        
        # ============================================================
        # PASSO 5: Mantém as contas conectadas e escuta mensagens
        # ============================================================
        logger.info("\n[PASSO 5] Mantendo contas conectadas...")
        logger.info("As contas estão online e prontas para receber mensagens.")
        logger.info("Pressione Ctrl+C para desconectar e sair.\n")
        
        # Loop principal - mantém as contas conectadas
        try:
            while True:
                # Verifica status periodicamente
                time.sleep(30)
                
                # Verifica se as contas ainda estão online
                online1 = client1.is_online()
                online2 = client2.is_online()
                
                if not online1:
                    logger.warning(f"Conta 1 ({account1_id}) está offline")
                if not online2:
                    logger.warning(f"Conta 2 ({account2_id}) está offline")
                
                # Log de status a cada 30 segundos
                logger.debug(f"Status: Conta1={online1}, Conta2={online2}")
                
        except KeyboardInterrupt:
            logger.info("\nInterrompido pelo usuário")
        
    except Exception as e:
        logger.error(f"Erro durante execução: {e}", exc_info=True)
    
    finally:
        # ============================================================
        # PASSO 6: Desconecta e remove as contas
        # ============================================================
        logger.info("\n[PASSO 6] Desconectando e removendo contas...")
        
        try:
            # Desconecta todas as contas
            manager.disconnect_all()
            logger.info("✓ Todas as contas desconectadas")
            
            # Remove todas as contas
            manager.remove_all()
            logger.info("✓ Todas as contas removidas")
            
        except Exception as e:
            logger.error(f"Erro ao limpar contas: {e}", exc_info=True)
        
        logger.info("\n" + "=" * 60)
        logger.info("Exemplo finalizado")
        logger.info("=" * 60)


if __name__ == "__main__":
    # Configuração básica de logging
    logger.add(
        "logs/multiple_accounts_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )
    
    main()

