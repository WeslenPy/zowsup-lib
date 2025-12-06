"""
Exemplo de envio de mensagens para grupos WhatsApp.

Este exemplo demonstra:
1. Como enviar mensagens para grupos
2. Como obter o ID do grupo
3. Diferenças entre envio para grupo e contato individual
"""

from app.account_manager import AccountManager
from loguru import logger
import time


def main():
    # Obtém o gerenciador
    manager = AccountManager.get_instance()
    
    # Adiciona conta
    logger.info("=== Adicionando conta ===")
    client = manager.add_account("5511999999999", env="android", auto_connect=True)
    
    # Aguarda login
    logger.info("=== Aguardando login ===")
    time.sleep(10)
    
    if not client.is_connected():
        logger.error("Conta não está conectada!")
        return
    
    logger.info("=== Conta conectada ===")
    
    # Exemplo 1: Enviar para grupo usando apenas o ID
    # O Jid.normalize() detecta automaticamente que é um grupo e adiciona @g.us
    logger.info("\n=== Exemplo 1: Enviar para grupo (ID apenas) ===")
    group_id = "120363423921763948"  # ID do grupo (sem @g.us)
    
    try:
        result = client.send_text(group_id, "Olá pessoal do grupo! 👋")
        logger.info(f"Mensagem enviada com sucesso: {result.data}")
    except Exception as e:
        logger.error(f"Erro ao enviar: {e}")
    
    time.sleep(2)
    
    # Exemplo 2: Enviar para grupo usando JID completo
    logger.info("\n=== Exemplo 2: Enviar para grupo (JID completo) ===")
    group_jid = "120363423921763948@g.us"  # JID completo do grupo
    
    try:
        result = client.send_text(group_jid, "Segunda mensagem para o grupo!")
        logger.info(f"Mensagem enviada com sucesso: {result.data}")
    except Exception as e:
        logger.error(f"Erro ao enviar: {e}")
    
    time.sleep(2)
    
    # Exemplo 3: Enviar e obter o ID da mensagem
    logger.info("\n=== Exemplo 3: Enviar e obter ID da mensagem ===")
    
    try:
        result = client.send_text(
            group_id,
            "Mensagem com ID",
            wait_for_id=True,
            wait_msg_id_timeout=10
        )
        if result.data and "message_id" in result.data:
            logger.info(f"ID da mensagem: {result.data['message_id']}")
        else:
            logger.warning("ID da mensagem não retornado")
    except Exception as e:
        logger.error(f"Erro ao enviar: {e}")
    
    time.sleep(2)
    
    # Exemplo 4: Comparar envio para grupo vs contato individual
    logger.info("\n=== Exemplo 4: Comparação grupo vs contato ===")
    
    # Para contato individual
    individual_phone = "5511888888888"
    logger.info(f"Enviando para contato individual: {individual_phone}")
    try:
        result = client.send_text(individual_phone, "Olá contato individual!")
        logger.info(f"Mensagem enviada: {result.data}")
    except Exception as e:
        logger.error(f"Erro: {e}")
    
    time.sleep(2)
    
    # Para grupo
    logger.info(f"Enviando para grupo: {group_id}")
    try:
        result = client.send_text(group_id, "Olá grupo!")
        logger.info(f"Mensagem enviada: {result.data}")
    except Exception as e:
        logger.error(f"Erro: {e}")
    
    # Exemplo 5: Como identificar se uma mensagem recebida é de grupo
    logger.info("\n=== Exemplo 5: Identificando mensagens de grupo ===")
    logger.info("""
    Quando você recebe uma mensagem, verifique:
    
    1. Se message.HasField("participant") → É mensagem de grupo
    2. message.sender → JID do grupo (ex: "120363423921763948@g.us")
    3. message.participant → JID de quem enviou no grupo
    
    Exemplo de callback:
    
    def on_message(message, logger, caller):
        if message.HasField("participant"):
            # É grupo
            group_jid = message.sender
            participant = message.participant
            text = message.text_message.text
            logger.info(f"Grupo {group_jid}: {participant} disse: {text}")
        else:
            # É contato individual
            sender = message.sender
            text = message.text_message.text
            logger.info(f"{sender} disse: {text}")
    """)
    
    logger.info("\n=== Exemplos concluídos ===")
    logger.info("Nota: Substitua os IDs de grupo e telefones pelos valores reais")


if __name__ == "__main__":
    main()

