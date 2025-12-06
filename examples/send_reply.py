"""
Exemplo de envio de mensagens marcando outra como resposta (reply/quote).

Este exemplo demonstra como enviar mensagens que respondem a outras mensagens,
mostrando a mensagem original como uma citação.
"""

from app.account_manager import AccountManager
from loguru import logger
import time


def main():
    # Obtém o gerenciador
    manager = AccountManager.get_instance()
    
    logger.info("=== Exemplo: Enviar mensagens como reply ===")
    
    # Número da conta
    account_phone = "5511999999999"  # Substitua pelo número da sua conta
    
    # Adiciona e conecta a conta
    client = manager.add_account(account_phone, env="smb_android", auto_connect=False)
    client.connect(wait_login=True)
    
    if not client.is_connected():
        logger.error("Falha ao conectar conta")
        return
    
    logger.info("✓ Conta conectada")
    
    # Exemplo 1: Responder a uma mensagem individual
    logger.info("\n--- Exemplo 1: Reply em conversa individual ---")
    try:
        # ID da mensagem original (você precisa ter esse ID de uma mensagem recebida)
        original_message_id = "3EB0123456789ABCDEF"  # Substitua por um ID real
        
        result = client.send_text_reply(
            to="5511888888888",  # Destinatário
            text="Entendi sua mensagem anterior!",
            reply_to_message_id=original_message_id
        )
        
        logger.info(f"✓ Mensagem de reply enviada: {result.data}")
    except Exception as e:
        logger.error(f"Erro ao enviar reply individual: {e}")
    
    # Exemplo 2: Responder a uma mensagem em grupo
    logger.info("\n--- Exemplo 2: Reply em grupo ---")
    try:
        # ID da mensagem original no grupo
        original_message_id = "3EB0123456789ABCDEF"  # Substitua por um ID real
        
        result = client.send_text_reply(
            to="120363123456789012@g.us",  # Grupo
            text="Concordo com você!",
            reply_to_message_id=original_message_id,
            reply_to_participant="5511999999999@s.whatsapp.net",  # Quem enviou a mensagem original
            quoted_text="Mensagem original que está sendo respondida"
        )
        
        logger.info(f"✓ Mensagem de reply em grupo enviada: {result.data}")
    except Exception as e:
        logger.error(f"Erro ao enviar reply em grupo: {e}")
    
    # Exemplo 3: Usar send_text com opção reply (método alternativo)
    logger.info("\n--- Exemplo 3: Reply usando opções do send_text ---")
    try:
        # Método 1: Apenas o ID da mensagem
        result = client.send_text(
            "5511888888888",
            "Resposta usando opções",
            reply="3EB0123456789ABCDEF"
        )
        logger.info(f"✓ Reply via opções (string): {result.data}")
        
        # Método 2: Dict com mais informações
        result = client.send_text(
            "120363123456789012@g.us",
            "Resposta em grupo via opções",
            reply={
                "message_id": "3EB0123456789ABCDEF",
                "participant": "5511999999999@s.whatsapp.net"
            }
        )
        logger.info(f"✓ Reply via opções (dict): {result.data}")
    except Exception as e:
        logger.error(f"Erro ao enviar reply via opções: {e}")
    
    # Exemplo 4: Auto reply com reply automático
    logger.info("\n--- Exemplo 4: Auto reply que responde com reply ---")
    
    def auto_reply_with_reply(sender, text):
        """Handler customizado que responde com reply."""
        # Em um caso real, você precisaria ter o message_id da mensagem recebida
        # Por enquanto, este é apenas um exemplo conceitual
        return "Resposta automática"
    
    # Habilita auto reply
    client.enable_auto_reply(
        custom_handler=auto_reply_with_reply
    )
    
    logger.info("Auto reply habilitado (responderá automaticamente)")
    logger.info("Aguardando mensagens... (pressione Ctrl+C para parar)")
    
    try:
        while True:
            time.sleep(60)
            if client.is_connected():
                logger.info("Conta ainda conectada...")
            else:
                logger.warning("Conta desconectada")
                break
    except KeyboardInterrupt:
        logger.info("\nDesabilitando auto reply e desconectando...")
        client.disable_auto_reply()
        client.disconnect()
        logger.info("Desconectado.")


if __name__ == "__main__":
    main()

