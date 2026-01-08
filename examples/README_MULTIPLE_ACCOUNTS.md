# Exemplos de Múltiplas Contas Simultâneas

Este diretório contém exemplos de como usar o sistema de thread única para gerenciar múltiplas contas WhatsApp simultaneamente.

## Arquitetura de Thread Única

O sistema agora usa apenas **2 threads principais** para gerenciar todas as contas:

1. **StackLoopManager**: Uma thread que processa todos os stacks de todas as contas
2. **PingManager**: Uma thread que envia pings para todas as contas

Isso reduz drasticamente o uso de recursos do sistema comparado ao modelo anterior onde cada conta tinha suas próprias threads.

## Arquivos de Exemplo

### `multiple_accounts_example.py`
Exemplo completo e detalhado com:
- Adição de múltiplas contas
- Conexão simultânea
- Callbacks personalizados
- Envio de mensagens
- Monitoramento de status
- Desconexão limpa

### `multiple_accounts_simple.py`
Versão simplificada para uso rápido:
- Código mínimo necessário
- Conexão automática
- Verificação básica de status

## Como Usar

### Exemplo Básico

```python
from zowsuplib.app.account_manager import AccountManager

# Obtém o gerenciador singleton
manager = AccountManager.get_instance()

# Adiciona e conecta primeira conta
client1 = manager.add_account("5511999999999", env="android", auto_connect=True)

# Adiciona e conecta segunda conta
client2 = manager.add_account("5511888888888", env="android", auto_connect=True)

# Verifica status
print(f"Conta 1 online: {client1.is_online()}")
print(f"Conta 2 online: {client2.is_online()}")

# Envia mensagens
client1.send_text("5511777777777", "Olá da conta 1!")
client2.send_text("5511777777777", "Olá da conta 2!")

# Desconecta tudo ao final
manager.disconnect_all()
manager.remove_all()
```

### Exemplo com Callbacks

```python
from zowsuplib.app.account_manager import AccountManager
from loguru import logger

def on_message(account_id, msg_type, from_jid, msg_data):
    logger.info(f"[{account_id}] Mensagem de {from_jid}: {msg_data}")

manager = AccountManager.get_instance()

client1 = manager.add_account("5511999999999", env="android", auto_connect=True)
client1.set_message_callback(
    lambda t, f, d: on_message("5511999999999", t, f, d)
)

client2 = manager.add_account("5511888888888", env="android", auto_connect=True)
client2.set_message_callback(
    lambda t, f, d: on_message("5511888888888", t, f, d)
)

# Mantém rodando para receber mensagens
import time
while True:
    time.sleep(60)
```

## Executando os Exemplos

### Exemplo Completo
```bash
python examples/multiple_accounts_example.py
```

### Exemplo Simples
```bash
python examples/multiple_accounts_simple.py
```

## Configuração

Antes de executar, certifique-se de:

1. **Substituir os números de telefone** nos exemplos pelos seus números reais
2. **Configurar o ambiente** (`env`) apropriado:
   - `"android"` - WhatsApp padrão Android
   - `"ios"` - WhatsApp padrão iOS
   - `"smb_android"` - WhatsApp Business Android
   - `"smb_ios"` - WhatsApp Business iOS

3. **Configurar logging** (opcional):
   ```python
   from loguru import logger
   logger.add("logs/app_{time}.log", rotation="1 day")
   ```

## Benefícios da Thread Única

### Antes (Modelo Antigo)
- 3 contas = 6 threads (3 stacks + 3 pings)
- 10 contas = 20 threads (10 stacks + 10 pings)
- Alto consumo de memória e CPU

### Agora (Modelo Novo)
- 3 contas = 2 threads (1 stack manager + 1 ping manager)
- 10 contas = 2 threads (1 stack manager + 1 ping manager)
- Baixo consumo de recursos, mesmo com muitas contas

## Isolamento de Contas

Cada conta mantém **isolamento completo**:
- ✅ Stack isolado
- ✅ Profile isolado
- ✅ Estado de conexão isolado
- ✅ Fila de pings isolada
- ✅ Callbacks isolados

## Troubleshooting

### Conta não conecta
- Verifique se o número está correto
- Tente outro tipo de ambiente (`env`)
- Verifique os logs para erros de handshake

### Mensagens não chegam
- Verifique se `is_online()` retorna `True`
- Confirme que o callback está configurado
- Verifique os logs para erros

### Muitas threads ainda aparecem
- Threads de ping antigas podem ainda estar rodando
- Reinicie o processo para limpar threads antigas
- Verifique se está usando a versão mais recente do código

## API Reference

### AccountManager

```python
# Métodos principais
manager.add_account(account_id, env=None, proxy=None, auto_connect=True)
manager.get_account(account_id)
manager.remove_account(account_id, disconnect=True)
manager.list_accounts()
manager.disconnect_all()
manager.remove_all()
```

### ZowsupClient

```python
# Métodos principais
client.connect(wait_login=True)
client.disconnect()
client.is_online()
client.is_connected()
client.send_text(to, text)
client.send_media(to, media_path, media_type)
```

## Suporte

Para mais informações, consulte:
- `docs/MULTIPLE_ACCOUNTS.md` - Documentação completa
- `zowsuplib/app/account_manager.py` - Código fonte
- `zowsuplib/app/stack_loop_manager.py` - Gerenciador de stacks
- `zowsuplib/app/ping_manager.py` - Gerenciador de pings

