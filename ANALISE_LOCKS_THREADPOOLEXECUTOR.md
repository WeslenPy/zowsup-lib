# Análise de Locks e Migração para ThreadPoolExecutor

## Resumo Executivo

Análise completa dos pontos do projeto que usam locks e avaliação de possíveis migrações para `ThreadPoolExecutor` para evitar travamentos.

---

## ✅ Já Implementado

### 1. `_CommandDispatcher.call()` - **MIGRADO**
- **Localização**: `zowsuplib/app/api.py:88-136`
- **Status**: ✅ Implementado com ThreadPoolExecutor
- **Benefício**: Handlers bloqueantes não travam mais a thread principal

---

## 🔴 Pontos Críticos que Precisam de Atenção

### 2. Operações de Banco de Dados em Callbacks do Stack

#### 2.1. `onSuccess()` - Atualização de Status
- **Localização**: `zowsuplib/app/yowbot_layer.py:1118-1119`
- **Problema**: `update_account_status()` é chamado diretamente na thread do stack
- **Impacto**: Se DB travar, pode bloquear processamento de mensagens
- **Recomendação**: Executar em thread separada (não crítico para ordem)

```python
# ANTES (pode travar):
update_account_status(self.bot.botId, is_logged_in=True, has_restriction=False)

# DEPOIS (assíncrono):
def _update_status_async(phone, **kwargs):
    update_account_status(phone, **kwargs)

threading.Thread(
    target=_update_status_async,
    args=(self.bot.botId,),
    kwargs={"is_logged_in": True, "has_restriction": False},
    daemon=True
).start()
```

#### 2.2. `onAck()` - Registro de Mensagens Enviadas
- **Localização**: `zowsuplib/app/yowbot_layer.py:1174-1179, 1192-1197`
- **Problema**: `register_sent_message()` bloqueia thread do stack
- **Impacto**: Alto - chamado para cada ACK recebido
- **Recomendação**: Usar fila assíncrona ou ThreadPoolExecutor dedicado

#### 2.3. `_register_sent_message()` - Múltiplos Locais
- **Localização**: `zowsuplib/app/yowbot_layer.py:2028-2044`
- **Problema**: Chamado em vários pontos críticos (sendMsgDirect, sendMessageReaction, etc.)
- **Impacto**: Alto - pode travar envio de mensagens
- **Recomendação**: Executar em thread separada ou fila assíncrona

---

## 🟡 Pontos que Podem Melhorar (Mas Não Críticos)

### 3. `assureContactsAndSend()` - Operações de DB
- **Localização**: `zowsuplib/app/yowbot_layer.py:1600-1747`
- **Status**: ⚠️ Já está dentro de handler (ThreadPoolExecutor)
- **Problema**: `self.db._store.isNewContact()` e `self.db._store.addContact()` podem bloquear
- **Impacto**: Médio - já protegido pelo executor, mas pode melhorar cache
- **Recomendação**: Adicionar cache de contatos para reduzir queries de DB

### 4. `_check_account_restriction()` - Query de DB
- **Localização**: `zowsuplib/app/yowbot_layer.py:1488-1517`
- **Status**: ⚠️ Já está dentro de handler (ThreadPoolExecutor)
- **Problema**: Query de DB a cada verificação
- **Impacto**: Médio - pode ser cacheado
- **Recomendação**: Adicionar cache com TTL de 5 minutos

### 5. `toLower()` com Lock
- **Localização**: `zowsuplib/yowsup/layers/__init__.py:83-87`
- **Status**: ⚠️ NÃO RECOMENDADO MUDAR
- **Razão**: Parte crítica do protocolo de layers, precisa manter ordem
- **Impacto**: Baixo - lock é rápido, apenas protege envio

---

## 🟢 Pontos que Estão OK (Não Precisam Mudança)

### 6. `SessionLifecycleManager` - Locks de Metadados
- **Localização**: `zowsuplib/app/session_manager.py`
- **Status**: ✅ OK
- **Razão**: Locks protegem apenas estruturas de dados em memória (rápido)
- **Operações**: Apenas atualização de dicionários, não operações bloqueantes

### 7. `AccountSessionRegistry` - Locks de Registro
- **Localização**: `zowsuplib/app/session_manager.py:33-128`
- **Status**: ✅ OK
- **Razão**: Operações rápidas em estruturas de dados

### 8. `BlockingQueueSegmentedStream` - Lock de Queue
- **Localização**: `zowsuplib/consonance/streams/segmented/blockingqueue.py`
- **Status**: ✅ OK
- **Razão**: Lock protege apenas operações de queue (rápido)

### 9. `YowIqProtocolLayer` - Lock de Ping Queue
- **Localização**: `zowsuplib/yowsup/layers/protocol_iq/layer.py`
- **Status**: ✅ OK
- **Razão**: Lock protege apenas estrutura de dados (rápido)

### 10. `SqlAxolotlStore` - Lock de Inicialização
- **Localização**: `zowsuplib/yowsup/axolotl/store/sqlaxolotlstore.py:968`
- **Status**: ✅ OK
- **Razão**: Lock protege apenas inicialização de sub-stores (rápido)

---

## 📋 Recomendações Prioritárias

### Prioridade ALTA 🔴

1. **Fila Assíncrona para `register_sent_message()`**
   - Criar fila com worker thread dedicado
   - Evita bloquear thread do stack em cada ACK
   - Impacto: Alto - chamado frequentemente

2. **ThreadPoolExecutor para `update_account_status()` em callbacks**
   - Executar assincronamente em `onSuccess()`, `onDisconnected()`, etc.
   - Não afeta ordem crítica
   - Impacto: Médio - chamado em eventos importantes

### Prioridade MÉDIA 🟡

3. **Cache para `_check_account_restriction()`**
   - Cachear resultado por 5 minutos
   - Reduz queries de DB desnecessárias
   - Impacto: Médio - melhora performance

4. **Cache para `isNewContact()`**
   - Cachear contatos verificados recentemente
   - Reduz queries de DB em `assureContactsAndSend()`
   - Impacto: Médio - melhora performance

### Prioridade BAIXA 🟢

5. **Otimizações de locks existentes**
   - Converter `Lock()` para `RLock()` onde apropriado
   - Reduzir escopo de locks
   - Impacto: Baixo - melhorias incrementais

---

## 🛠️ Implementação Recomendada

### Solução 1: Fila Assíncrona para Operações de DB

```python
# Em yowbot_layer.py
class YowBotLayer:
    def __init__(self, bot):
        # ... código existente ...
        
        # Fila assíncrona para operações de DB não críticas
        self._db_queue = queue.Queue(maxsize=1000)
        self._db_worker_thread = threading.Thread(
            target=self._db_worker,
            name=f"db-worker-{bot.botId}",
            daemon=True
        )
        self._db_worker_thread.start()
    
    def _db_worker(self):
        """Worker thread para processar operações de DB assíncronas."""
        while True:
            try:
                operation = self._db_queue.get(timeout=1)
                if operation is None:  # Sentinel para parar
                    break
                
                func, args, kwargs = operation
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Erro em operação de DB assíncrona: {e}")
                finally:
                    self._db_queue.task_done()
            except queue.Empty:
                continue
    
    def _register_sent_message_async(self, msg_id, recipient_jid, message_type, status, error_code=None):
        """Versão assíncrona de _register_sent_message."""
        if self.bot.botId is None:
            return
        
        try:
            from zowsuplib.app.db import register_sent_message
            self._db_queue.put((
                register_sent_message,
                (self.bot.botId, msg_id, recipient_jid, message_type, status, error_code),
                {}
            ), block=False)
        except queue.Full:
            logger.warning(f"Fila de DB cheia, ignorando registro de mensagem {msg_id}")
```

### Solução 2: ThreadPoolExecutor para Callbacks

```python
# Em yowbot_layer.py
class YowBotLayer:
    def __init__(self, bot):
        # ... código existente ...
        
        # Executor para operações de DB em callbacks
        self._callback_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=5,
            thread_name_prefix=f"callback-db-{bot.botId}"
        )
    
    @ProtocolEntityCallback("success")
    def onSuccess(self, successProtocolEntity):
        # ... código existente ...
        
        # Atualiza status assincronamente
        if self.bot.botId is not None:
            self._callback_executor.submit(
                update_account_status,
                self.bot.botId,
                is_logged_in=True,
                has_restriction=False
            )
```

### Solução 3: Cache para Verificações Frequentes

```python
# Em yowbot_layer.py
class YowBotLayer:
    def __init__(self, bot):
        # ... código existente ...
        
        # Cache para restrições de conta (TTL: 5 minutos)
        self._restriction_cache = {}
        self._restriction_cache_ttl = 300  # 5 minutos
    
    def _check_account_restriction(self):
        """Verifica restrições com cache."""
        if self.bot.botId is None:
            return False
        
        # Verifica cache
        cache_key = self.bot.botId
        if cache_key in self._restriction_cache:
            cached_value, timestamp = self._restriction_cache[cache_key]
            if time.time() - timestamp < self._restriction_cache_ttl:
                return cached_value
        
        # Cache miss: busca no DB
        try:
            from zowsuplib.app.db import SessionLocal
            from zowsuplib.app import models
            
            db = SessionLocal()
            try:
                has_restriction = (
                    db.query(models.Account.has_restriction)
                    .filter_by(phone=self.bot.botId)
                    .scalar()
                )
                # Atualiza cache
                self._restriction_cache[cache_key] = (bool(has_restriction), time.time())
                return bool(has_restriction)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Erro ao verificar restrições: {e}")
            return False
```

---

## 📊 Resumo de Impacto

| Localização | Tipo | Impacto | Prioridade | Status |
|------------|------|---------|------------|--------|
| `_CommandDispatcher.call()` | Handler execution | 🔴 Alto | ALTA | ✅ Implementado |
| `register_sent_message()` em callbacks | DB operation | 🔴 Alto | ALTA | ⚠️ Precisa implementar |
| `update_account_status()` em callbacks | DB operation | 🟡 Médio | ALTA | ⚠️ Precisa implementar |
| `_check_account_restriction()` | DB query | 🟡 Médio | MÉDIA | ⚠️ Pode cachear |
| `isNewContact()` | DB query | 🟡 Médio | MÉDIA | ⚠️ Pode cachear |
| `toLower()` com lock | Protocol layer | 🟢 Baixo | BAIXA | ✅ OK (não mudar) |
| SessionManager locks | Metadata | 🟢 Baixo | BAIXA | ✅ OK |
| Outros locks | Estruturas de dados | 🟢 Baixo | BAIXA | ✅ OK |

---

## 🎯 Conclusão

**Pontos que DEVEM ser migrados:**
1. ✅ `_CommandDispatcher.call()` - **JÁ IMPLEMENTADO**
2. ⚠️ `register_sent_message()` - **PRECISA IMPLEMENTAR** (fila assíncrona)
3. ⚠️ `update_account_status()` em callbacks - **PRECISA IMPLEMENTAR** (executor)

**Pontos que PODEM melhorar:**
- Cache para verificações frequentes de DB
- Otimizações de locks existentes

**Pontos que NÃO devem mudar:**
- Locks de protocolo de layers (críticos para ordem)
- Locks de estruturas de dados rápidas (já otimizados)

