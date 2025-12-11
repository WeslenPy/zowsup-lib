# Enviando Mensagens para Grupos

Este documento explica como enviar mensagens para grupos no WhatsApp usando a API Zowsup.

## Formato de JID de Grupo

Os grupos WhatsApp usam um formato especial de JID que termina com `@g.us`:

- **Formato**: `{GROUP_ID}@g.us`
- **Exemplo**: `120363423921763948@g.us`

## Detecção Automática de Grupos

A função `Jid.normalize()` detecta automaticamente se um destino é um grupo:

```python
from yowsup.common.tools import Jid

# Número de telefone → @s.whatsapp.net
Jid.normalize("5511999999999")
# Retorna: "5511999999999@s.whatsapp.net"

# ID de grupo (com hífen ou 15+ caracteres) → @g.us
Jid.normalize("120363423921763948")
# Retorna: "120363423921763948@g.us"

# JID completo já formatado → mantém como está
Jid.normalize("120363423921763948@g.us")
# Retorna: "120363423921763948@g.us"
```

### Regras de Detecção

O `Jid.normalize()` considera um grupo se:
1. O ID contém um hífen (`-`), OU
2. O ID tem 15 ou mais caracteres E não contém `.`, `:` ou `@`

## Enviando Mensagens para Grupos

### Método 1: Usando o ID do Grupo

```python
from app.account_manager import AccountManager

manager = AccountManager.get_instance()
client = manager.add_account("5511999999999")

# Envia usando apenas o ID do grupo (sem @g.us)
# O Jid.normalize() adiciona @g.us automaticamente
client.send_text("120363423921763948", "Olá grupo!")
```

### Método 2: Usando JID Completo

```python
# Envia usando JID completo
client.send_text("120363423921763948@g.us", "Olá grupo!")
```

### Método 3: Usando SendLayer Diretamente

```python
# Para envio mais rápido (bypass do sistema de comandos)
client.send_text(
    "120363423921763948@g.us",
    "Olá grupo!",
    use_direct_layer=True
)
```

## Fluxo de Envio para Grupos

### 1. SendLayer (`sendMsgDirect`)

```python
# Em app/yowbot_layer.py
def sendMsgDirect(self, cmdParams, options):
    to, message, *other = cmdParams
    
    # Normaliza o JID (adiciona @g.us se necessário)
    target = Jid.normalize(to.split(",")[0])
    
    # Detecta se é grupo
    if target.endswith("@g.us"):
        # Envia indicador de "digitando" para grupo
        entity = OutgoingChatstateProtocolEntity(
            ChatstateProtocolEntity.STATE_TYPING,
            target,
            Jid.normalize(self.bot.botId)
        )
    else:
        # Envia indicador de "digitando" para contato individual
        entity = OutgoingChatstateProtocolEntity(
            ChatstateProtocolEntity.STATE_TYPING,
            target
        )
    
    # Envia a mensagem
    self.toLower(messageEntity)
```

### 2. AxolotlSendLayer (`sendToGroup`)

A camada de criptografia Axolotl trata grupos de forma especial:

```python
# Em yowsup/layers/axolotl/layer_send.py
def sendToGroup(self, node, retryReceiptEntity=None):
    """
    Sequência de envio para grupo:
    1. Verifica se existe senderKeyRecord para o grupo
    2. Se não existe:
       - Cria senderKeyRecord
       - Obtém lista de participantes do grupo
       - Para cada participante sem sessão, obtém chaves
       - Envia mensagem com dist key para todos os participantes
    3. Se existe:
       - Envia skmsg (SenderKey Message) sem dist key
    """
    groupJid = node["to"]
    senderKeyRecord = self.manager.load_senderkey(node["to"])
    
    if senderKeyRecord.isEmpty():
        # Primeira vez enviando para este grupo
        # Solicita informações do grupo para obter participantes
        groupInfoIq = InfoGroupsIqProtocolEntity(groupJid)
        self._sendIq(groupInfoIq, sendToGroup)
    else:
        # Já tem senderKey, envia diretamente
        self.sendToGroupWithSessions(node)
```

### 3. Criptografia SenderKey

Grupos usam **SenderKey** em vez de sessões individuais:
- **SenderKey**: Chave compartilhada para todos os participantes do grupo
- **Vantagem**: Mais eficiente que criptografar para cada participante individualmente
- **Tipo de mensagem**: `skmsg` (SenderKey Message)

## Exemplo Completo

```python
from app.account_manager import AccountManager
from loguru import logger

# Obtém o gerenciador
manager = AccountManager.get_instance()

# Adiciona conta
client = manager.add_account("5511999999999", env="android")

# Aguarda login
import time
time.sleep(5)

# Envia mensagem para grupo usando ID
group_id = "120363423921763948"
result = client.send_text(group_id, "Olá pessoal do grupo!")
logger.info(f"Mensagem enviada: {result.data}")

# Envia mensagem para grupo usando JID completo
group_jid = "120363423921763948@g.us"
result = client.send_text(group_jid, "Segunda mensagem!")
logger.info(f"Mensagem enviada: {result.data}")

# Envia com wait_for_id para obter o ID da mensagem
result = client.send_text(
    group_id,
    "Mensagem com ID",
    wait_for_id=True,
    wait_msg_id_timeout=10
)
logger.info(f"ID da mensagem: {result.data.get('message_id')}")
```

## Obtendo o ID do Grupo

### Método 1: Do Log de Mensagens Recebidas

Quando você recebe uma mensagem de um grupo, o campo `sender` contém o JID do grupo:

```python
def on_message(message, logger, caller):
    if message.HasField("participant"):
        # É mensagem de grupo
        group_jid = message.sender  # Ex: "120363423921763948@g.us"
        participant = message.participant  # Quem enviou no grupo
        text = message.text_message.text
        
        logger.info(f"Mensagem no grupo {group_jid} de {participant}: {text}")
```

### Método 2: Usando groupInfo

```python
# Obtém informações do grupo (incluindo ID)
# Isso requer um comando customizado ou acesso direto ao SendLayer
```

## Diferenças entre Grupo e Contato Individual

| Aspecto | Contato Individual | Grupo |
|---------|-------------------|-------|
| **JID** | `{phone}@s.whatsapp.net` | `{group_id}@g.us` |
| **Criptografia** | Sessão individual (WhisperMessage) | SenderKey (SenderKeyMessage) |
| **Participantes** | 1 (apenas o destinatário) | Múltiplos (todos do grupo) |
| **Indicador "digitando"** | Simples | Inclui JID do remetente |
| **Participant** | Não aplicável | Campo `participant` identifica quem enviou |

## Tratamento de Erros

### Grupo Não Encontrado

Se o grupo não existir ou você não for membro:

```python
try:
    result = client.send_text("999999999999999@g.us", "Teste")
except ZowsupError as e:
    logger.error(f"Erro ao enviar: {e.code} - {e}")
```

### SenderKey Não Disponível

Na primeira vez que você envia para um grupo:
1. O sistema solicita informações do grupo
2. Obtém lista de participantes
3. Cria sessões para participantes sem sessão
4. Cria o SenderKey
5. Envia a mensagem

Isso pode levar alguns segundos na primeira vez.

## Notas Importantes

1. **Você precisa ser membro do grupo** para enviar mensagens
2. **O ID do grupo** geralmente é um número longo (15+ dígitos)
3. **Primeira mensagem** pode demorar mais (criação de SenderKey)
4. **Mensagens de grupo** são criptografadas com SenderKey (mais eficiente)
5. **Participant field**: Quando você recebe mensagem de grupo, o campo `participant` identifica quem enviou

## Exemplo com Auto Responder para Grupos

```python
# Habilita auto responder que ignora grupos
client.enable_auto_reply(
    "Olá! Esta é uma resposta automática.",
    ignore_groups=True  # Não responde em grupos
)

# Ou responde apenas em grupos específicos
def group_handler(sender, text):
    # sender será o JID do grupo (ex: "120363423921763948@g.us")
    if "120363423921763948@g.us" in sender:
        return "Resposta para este grupo específico!"
    return None

client.enable_auto_reply(
    custom_handler=group_handler,
    ignore_groups=False
)
```

