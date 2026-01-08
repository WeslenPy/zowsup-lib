# Threads Identificadas e Nomes Atribuídos

Este documento lista todas as threads criadas no sistema e os nomes identificáveis atribuídos a cada uma.

## Threads de Gerenciamento Centralizado (Singleton)

### 1. StackLoopManager
- **Arquivo**: `zowsuplib/app/stack_loop_manager.py`
- **Nome**: `StackLoopManager`
- **Função**: Processa loops de todos os stacks em uma única thread
- **Status**: ✅ Nome atribuído

### 2. PingManager
- **Arquivo**: `zowsuplib/app/ping_manager.py`
- **Nome**: `PingManager`
- **Função**: Envia pings de todas as contas em uma única thread
- **Status**: ✅ Nome atribuído

### 3. CommandManager
- **Arquivo**: `zowsuplib/app/command_manager.py`
- **Nome**: `CommandManager`
- **Função**: Monitora resultados de commands de todas as contas em uma única thread
- **Status**: ✅ Nome atribuído

## Threads por Conta

### 4. HandshakeWorker (Login)
- **Arquivo**: `zowsuplib/yowsup/layers/noise/workers/handshake.py`
- **Nome**: `HandshakeWorker-{account_id}-{attempt_id}`
- **Exemplo**: `HandshakeWorker-559881127175-1`
- **Função**: Executa handshake de login para uma conta
- **Status**: ✅ Nome atribuído

### 5. HandshakeWorker (Registro)
- **Arquivo**: `zowsuplib/yowsup/layers/noise/workers/handshake.py`
- **Nome**: `HandshakeWorker-Reg-{account_id}-{attempt_id}`
- **Exemplo**: `HandshakeWorker-Reg-559881127175-1`
- **Função**: Executa handshake de registro para uma conta
- **Status**: ✅ Nome atribuído

### 6. Connect Thread
- **Arquivo**: `zowsuplib/app/api.py`
- **Nome**: `connect-{account_id}`
- **Exemplo**: `connect-559881127175`
- **Função**: Inicia conexão de uma conta em thread dedicada
- **Status**: ✅ Nome atribuído

### 7. AccountInit Thread
- **Arquivo**: `zowsuplib/app/api.py`
- **Nome**: `AccountInit-{account_id}`
- **Exemplo**: `AccountInit-559881127175`
- **Função**: Inicializa conta de forma assíncrona
- **Status**: ✅ Nome atribuído

### 8. LivenessMonitor
- **Arquivo**: `zowsuplib/app/yowbot_layer.py`
- **Nome**: `LivenessMonitor-{account_id}`
- **Exemplo**: `LivenessMonitor-559881127175`
- **Função**: Monitora atividade da conta e força reconnect se necessário
- **Status**: ✅ Nome atribuído

### 9. YowPingThread (Fallback)
- **Arquivo**: `zowsuplib/yowsup/layers/protocol_iq/layer.py`
- **Nome**: `YowPing-{account_id}`
- **Exemplo**: `YowPing-559881127175`
- **Função**: Thread local de ping (usado apenas se PingManager não estiver disponível)
- **Status**: ✅ Nome atribuído

### 10. YowQrCodeThread
- **Arquivo**: `zowsuplib/app/yowbot_layer.py`
- **Nome**: `YowQrCode-{account_id}`
- **Exemplo**: `YowQrCode-559881127175`
- **Função**: Gera e exibe QR code para pairing
- **Status**: ✅ Nome atribuído

### 11. PrekeyRetry Thread
- **Arquivo**: `zowsuplib/yowsup/layers/axolotl/layer_control.py`
- **Nome**: `PrekeyRetry-{account_id}`
- **Exemplo**: `PrekeyRetry-559881127175`
- **Função**: Retenta envio de prekeys após erro 503
- **Status**: ✅ Nome atribuído

### 12. MediaUploader
- **Arquivo**: `zowsuplib/yowsup/layers/protocol_media/mediauploader.py`
- **Nome**: `MediaUploader-{account_jid}-{target_jid}`
- **Exemplo**: `MediaUploader-559881127175-559885700260`
- **Função**: Faz upload de mídia de forma assíncrona
- **Status**: ✅ Nome atribuído

## Threads de Scripts/Utilitários

### 13. YowBot Thread
- **Arquivo**: `zowsuplib/app/yowbot.py`
- **Nome**: `YowBot-{bot_id}`
- **Exemplo**: `YowBot-559881127175`
- **Função**: Executa bot em thread separada (modo legado)
- **Status**: ✅ Nome atribuído

### 14. CmdProcess Thread
- **Arquivo**: `zowsuplib/script/cmdprocess.py`
- **Nome**: `CmdProcess-{bot_id}-{command_name}`
- **Exemplo**: `CmdProcess-559881127175-send`
- **Função**: Processa comando em thread separada
- **Status**: ✅ Nome atribuído

### 15. InteractiveProcess Thread
- **Arquivo**: `zowsuplib/script/interactiveprocess.py`
- **Nome**: `InteractiveProcess-{bot_id}`
- **Exemplo**: `InteractiveProcess-559881127175`
- **Função**: Processa comandos interativos em thread separada
- **Status**: ✅ Nome atribuído

## Resumo

### Threads Centralizadas (3)
- `StackLoopManager` - 1 thread para todos os stacks
- `PingManager` - 1 thread para todos os pings
- `CommandManager` - 1 thread para monitoramento de commands

### Threads por Conta (variável)
- `HandshakeWorker-{account_id}-{attempt_id}` - 1 por tentativa de handshake
- `connect-{account_id}` - 1 por conexão
- `AccountInit-{account_id}` - 1 por inicialização
- `LivenessMonitor-{account_id}` - 1 por conta
- `YowPing-{account_id}` - 1 por conta (apenas fallback)
- `YowQrCode-{account_id}` - 1 por conta (apenas durante registro)
- `PrekeyRetry-{account_id}` - 1 por retry de prekeys
- `MediaUploader-{account}-{target}` - 1 por upload de mídia

### Threads de Scripts (variável)
- `YowBot-{bot_id}` - 1 por bot (modo legado)
- `CmdProcess-{bot_id}-{cmd}` - 1 por comando
- `InteractiveProcess-{bot_id}` - 1 por processo interativo

## Benefícios

1. **Identificação fácil**: Cada thread tem um nome descritivo que indica sua função
2. **Debug facilitado**: Fácil identificar qual thread está causando problemas
3. **Monitoramento**: Nomes consistentes facilitam monitoramento e profiling
4. **Rastreabilidade**: Fácil rastrear qual conta/operação está em cada thread

## Convenção de Nomenclatura

- **Gerenciadores**: `{ManagerName}` (ex: `StackLoopManager`)
- **Workers**: `{WorkerType}-{account_id}-{identifier}` (ex: `HandshakeWorker-559881127175-1`)
- **Operações**: `{Operation}-{account_id}` (ex: `connect-559881127175`)
- **Scripts**: `{ScriptType}-{bot_id}-{optional}` (ex: `CmdProcess-559881127175-send`)

