# Proxy Configuration and Persistence

Este documento explica como usar o sistema de configuração e persistência de proxy no ZowsupLib.

## Visão Geral

O sistema de proxy permite configurar proxies HTTP com validação automática e persistência no banco de dados. Os proxies são automaticamente carregados ao conectar novas instâncias do cliente.

## Funcionalidades

### 1. **Configuração de Proxy com Validação**
- ✅ **Validação automática** antes de configurar
- ✅ **Teste de conectividade** com timeout
- ✅ **Persistência no banco** de dados
- ✅ **Carregamento automático** ao conectar

### 2. **Formatos de Proxy Suportados**
- `"host:port"` - Proxy HTTP sem autenticação
- `"host:port:username:password"` - Proxy HTTP com autenticação
- `"DIRECT"` - Desativa proxy (conexão direta)

### 3. **Persistência Automática**
- ✅ **Salvamento automático** no banco de dados
- ✅ **Carregamento automático** na inicialização
- ✅ **Remoção completa** quando solicitado

## Uso Básico

### Configuração de Proxy

```python
from zowsuplib.app.api import ZowsupClient

# Criar cliente
client = ZowsupClient(account_id="5511999999999")

# Proxy sem autenticação
success = client.set_proxy("192.168.1.100:8080")
if success:
    print("Proxy configurado!")
else:
    print("Proxy inválido!")

# Proxy com autenticação
client.set_proxy("proxy.company.com:3128:user:password")

# Desativar proxy
client.set_proxy("DIRECT")
```

### Persistência Automática

```python
# Configurar proxy (salvo automaticamente no DB)
client.set_proxy("192.168.1.100:8080")

# Em outra execução/instância, o proxy é carregado automaticamente
client2 = ZowsupClient(account_id="5511999999999")
# Proxy já está configurado automaticamente!
```

### Remoção de Proxy

```python
# Remove proxy da instância e do banco de dados
client.remove_proxy()
```

## Persistência no Banco de Dados

### Estrutura dos Dados

O proxy é armazenado na tabela `accounts` com os seguintes campos:

- `proxy_host`: Endereço do servidor proxy
- `proxy_port`: Porta do servidor proxy
- `proxy_username`: Nome de usuário (opcional)
- `proxy_password`: Senha (opcional)

### Carregamento Automático

Ao criar uma nova instância do `ZowsupClient`, o proxy é automaticamente carregado do banco de dados se existir uma configuração salva.

```python
# O proxy é carregado automaticamente aqui
client = ZowsupClient(account_id="5511999999999")
```

## Validação de Proxy

### Processo de Validação

1. **Parsing do formato** do proxy string
2. **Validação de host e porta**
3. **Teste de conectividade** HTTP
4. **Verificação de resposta** 200 OK
5. **Persistência no banco** se válido

### Timeout de Teste

- **Timeout padrão**: 10 segundos
- **URL de teste**: `https://www.google.com` (configurável)
- **Tentativa única**: Sem retry automático

### Tratamento de Erros

```python
# Formato inválido
try:
    client.set_proxy("invalid-format")
except ValueError as e:
    print(f"Erro de formato: {e}")

# Proxy não responde
success = client.set_proxy("192.168.999.999:8080")
if not success:
    print("Proxy não está funcionando")
```

## Casos de Uso

### Ambiente Corporativo

```python
# Configurar proxy corporativo uma vez
client = ZowsupClient(account_id="5511999999999")
client.set_proxy("proxy.empresa.com:8080")

# Todas as próximas instâncias usarão o proxy automaticamente
client2 = ZowsupClient(account_id="5511999999999")
# Já tem proxy configurado!
```

### Desenvolvimento com Proxy Local

```python
# Usar Burp Suite ou similar para desenvolvimento
client = ZowsupClient(account_id="5511999999999")
client.set_proxy("127.0.0.1:8080")

# Debug de requisições HTTPS
```

### Rotação de Proxies

```python
# Lista de proxies
proxies = [
    "proxy1.example.com:3128",
    "proxy2.example.com:3128",
    "proxy3.example.com:3128"
]

for proxy in proxies:
    if client.set_proxy(proxy):
        print(f"Proxy {proxy} configurado com sucesso")
        break
    else:
        print(f"Proxy {proxy} falhou, tentando próximo...")
```

## Configuração Avançada

### URL de Teste Personalizada

```python
# Usar URL específica para teste
client.set_proxy(
    "proxy.example.com:8080",
    test_url="https://httpbin.org/ip"
)
```

### Verificação de Configuração

```python
# Verificar se proxy está configurado
current_proxy = client.get_proxy()
if current_proxy:
    print(f"Proxy atual: {current_proxy}")
else:
    print("Nenhum proxy configurado")
```

## Solução de Problemas

### Proxy Não Funciona

1. **Verificar conectividade**:
   ```bash
   curl -x http://proxy.host:port https://www.google.com
   ```

2. **Testar autenticação**:
   ```bash
   curl -x http://user:pass@proxy.host:port https://www.google.com
   ```

3. **Verificar formato**:
   - Host: domínio ou IP válido
   - Porta: 1-65535
   - Credenciais: apenas se requeridas

### Problemas de Persistência

1. **Verificar banco de dados**:
   ```sql
   SELECT proxy_host, proxy_port, proxy_username
   FROM accounts WHERE phone = '5511999999999';
   ```

2. **Limpar configuração manualmente**:
   ```python
   client.remove_proxy()
   ```

### Logs de Debug

O sistema registra todas as operações de proxy:

```
INFO - Testando proxy 192.168.1.100:8080...
INFO - ✅ Proxy validado com sucesso - resposta HTTP 200
INFO - ✅ Proxy configurado com sucesso: 192.168.1.100:8080
INFO - ✅ Proxy salvo no banco de dados
INFO - ✅ Proxy carregado do banco de dados: 192.168.1.100:8080
```

## Segurança

### Considerações de Segurança

- ✅ **Credenciais criptografadas** no banco de dados
- ✅ **Validação de entrada** para prevenir injeção
- ✅ **Logs seguros** (sem exposição de senhas)
- ⚠️ **Armazenamento local** (considere criptografia adicional para produção)

### Recomendações

1. **Use HTTPS proxies** quando possível
2. **Monitore logs** para detectar uso indevido
3. **Rotacione credenciais** periodicamente
4. **Considere VPN** para ambientes críticos

## API Reference

### `set_proxy(proxy_string, test_url="https://www.google.com") -> bool`

Configura um proxy após validação.

**Parâmetros:**
- `proxy_string`: String de proxy no formato "host:port" ou "host:port:user:pass"
- `test_url`: URL para testar conectividade (padrão: Google)

**Retorno:** `True` se configurado com sucesso, `False` se falhou

### `get_proxy() -> Optional[str]`

Obtém a configuração de proxy atual da conta.

**Retorno:** String do proxy no formato "host:port[:user[:pass]]" ou `None` se não houver proxy

### `remove_proxy() -> bool`

Remove configuração de proxy do banco de dados e instância.

**Retorno:** `True` se removido com sucesso

### `force_key_exchange(contact_jid, send_test_message=False) -> bool`

Força uma nova troca de chaves criptográficas com um contato específico.

**Parâmetros:**
- `contact_jid`: JID do contato (ex: "5511999999999@s.whatsapp.net")
- `send_test_message`: Se True, tenta enviar uma mensagem de teste

**Retorno:** `True` se conseguiu forçar a troca, `False` em caso de erro

### Carregamento Automático

O proxy é carregado automaticamente na inicialização do `ZowsupClient` se existir configuração salva no banco de dados.

## Exemplo Completo

Veja o arquivo `example_proxy.py` para um exemplo prático completo de uso do sistema de proxy.
