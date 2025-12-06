# Gerenciamento de Múltiplas Contas

A API de alto nível foi refatorada para suportar múltiplas contas simultaneamente, cada uma completamente isolada.

## Arquitetura

### Isolamento Completo

Cada conta (`ZowsupClient`) é completamente isolada:
- **Profile isolado**: Cada conta usa seu próprio `YowProfile` com `profile_name` único
- **Stack isolado**: Cada conta tem sua própria `YowStack` independente
- **Bot isolado**: Cada conta tem seu próprio `YowBot` em thread separada
- **SendLayer isolado**: Cada conta tem seu próprio `SendLayer` com callbacks isolados
- **Estado isolado**: Conexão, auto responder e callbacks são independentes por conta

### AccountManager

O `AccountManager` é um singleton que gerencia todas as contas ativas:

```python
from app.account_manager import AccountManager

# Obtém a instância singleton
manager = AccountManager.get_instance()
```

## Uso Básico

### Adicionar uma Conta

```python
# Adiciona uma conta com configuração padrão
client = manager.add_account("5511999999999")

# Adiciona uma conta com configurações específicas
client = manager.add_account(
    "5511888888888",
    env="ios",  # android, ios, smb_android, smb_ios
    proxy="host:port:user:pass",  # ou "DIRECT"
    auto_connect=True  # conecta automaticamente
)
```

### Listar Contas

```python
# Lista IDs de todas as contas
account_ids = manager.list_accounts()
print(f"Contas ativas: {account_ids}")

# Obtém um cliente específico
client = manager.get_account("5511999999999")
if client:
    status = client.get_status()
    print(f"Status: {status}")
```

### Remover uma Conta

```python
# Remove e desconecta
manager.remove_account("5511999999999", disconnect=True)

# Remove sem desconectar (útil se já desconectou manualmente)
manager.remove_account("5511999999999", disconnect=False)
```

## Exemplo Completo

```python
from app.account_manager import AccountManager
from loguru import logger

# Obtém o gerenciador
manager = AccountManager.get_instance()

# Adiciona múltiplas contas
client1 = manager.add_account("5511999999999", env="android")
client2 = manager.add_account("5511888888888", env="ios")

# Configura auto responder para cada conta
client1.enable_auto_reply("Olá! Esta é a conta 1.")
client2.enable_auto_reply("Olá! Esta é a conta 2.")

# Envia mensagens de diferentes contas
client1.send_text("5511777777777", "Mensagem da conta 1")
client2.send_text("5511777777777", "Mensagem da conta 2")

# Verifica status
for account_id in manager.list_accounts():
    client = manager.get_account(account_id)
    status = client.get_status()
    logger.info(f"Conta {account_id}: {status}")

# Limpeza
manager.disconnect_all()
manager.remove_all()
```

## Logs e Debug

Todos os logs incluem identificação da conta no formato `[ZowsupClient:account_id]`:

```
[ZowsupClient:5511999999999] Inicializando cliente isolado (env=android, proxy=DIRECT)
[ZowsupClient:5511999999999] Cliente inicializado com sucesso (isolado)
[ZowsupClient:5511999999999] Iniciando conexão (wait_login=True)
[ZowsupClient:5511999999999] Login concluído com sucesso
[ZowsupClient:5511999999999] send_text(to=5511777777777, text_len=20, wait_for_id=False, use_direct_layer=False)
```

## Métodos Úteis

### ZowsupClient

- `get_account_id()`: Retorna o ID da conta
- `get_status()`: Retorna dict com status completo
- `is_connected()`: Verifica se está conectado
- `get_send_layer()`: Retorna referência direta ao SendLayer

### AccountManager

- `add_account()`: Adiciona uma nova conta
- `get_account()`: Obtém cliente de uma conta
- `remove_account()`: Remove uma conta
- `list_accounts()`: Lista IDs de todas as contas
- `get_all_clients()`: Retorna dict com todos os clientes
- `is_account_active()`: Verifica se conta está ativa
- `disconnect_all()`: Desconecta todas as contas
- `remove_all()`: Remove todas as contas
- `get_account_count()`: Retorna número de contas

## Isolamento Técnico

### Profile Isolation

Cada conta usa seu próprio `profile_name` (o `account_id`), garantindo:
- Configurações isoladas no banco de dados
- Chaves Axolotl isoladas
- Sessões criptográficas independentes

### Stack Isolation

Cada `YowBot` cria sua própria `YowStack` com:
- Layers independentes
- Props isolados por stack
- Eventos isolados

### Thread Safety

O `AccountManager` usa locks para garantir thread-safety:
- Operações de adicionar/remover são thread-safe
- Cada conta roda em sua própria thread
- Não há compartilhamento de estado entre contas

## Limitações e Considerações

1. **SysVar Global**: O `SysVar` ainda é global, mas cada conta usa seu próprio `profile_name` para isolamento de dados
2. **Recursos do Sistema**: Múltiplas contas consomem mais memória e conexões de rede
3. **Rate Limiting**: WhatsApp pode aplicar rate limits por conta ou globalmente

## Migração de Código Existente

Se você já usa `ZowsupClient` diretamente, continue funcionando:

```python
# Código antigo (ainda funciona)
client = ZowsupClient("5511999999999")
client.connect()
client.send_text("5511888888888", "Olá!")
```

Para múltiplas contas, use o `AccountManager`:

```python
# Código novo (recomendado para múltiplas contas)
manager = AccountManager.get_instance()
client = manager.add_account("5511999999999")
client.send_text("5511888888888", "Olá!")
```

