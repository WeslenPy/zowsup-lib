# Fluxograma Detalhado do Processo de Autenticação - ZowsupLib

Este documento descreve o fluxo completo e detalhado do processo de autenticação no ZowsupLib, desde a inicialização do `ZowsupClient` até a finalização do auth, incluindo todas as classes e métodos envolvidos.

## Visão Geral

O processo de autenticação segue esta sequência:
1. **Inicialização do ZowsupClient**
2. **Conexão TCP**
3. **Handshake Noise Protocol**
4. **Autenticação Final**
5. **Finalização**

---

## Fluxograma Completo

```mermaid
flowchart TD
    Start([Início: ZowsupClient.__init__]) --> InitLog[Utils.init_log<br/>Inicializa sistema de logs]
    InitLog --> BuildConfig[ZowsupClient._build_account_config<br/>Cria configuração isolada por conta]
    BuildConfig --> LoadEnv[Carrega env do DB ou usa default<br/>DeviceEnv.__init__]
    LoadEnv --> LoadProxy[Carrega/Configura proxy<br/>NetworkEnv.__init__]
    LoadProxy --> InitStack[ZowsupClient._init_send_layer_stack<br/>Inicializa stack com SendLayer]
    
    InitStack --> CreateBot[YowBot.__init__<br/>Cria instância do bot]
    CreateBot --> CreateProfile[YowProfile.__init__<br/>Cria profile isolado]
    CreateProfile --> CreateSendLayer[SendLayer.__init__<br/>Cria camada de envio]
    CreateSendLayer --> BuildStack[YowStackBuilder.pushDefaultLayers<br/>Constrói stack de camadas]
    
    BuildStack --> SetProps[YowBot._stack.setProp<br/>Define propriedades: env, ID_TYPE, botId]
    SetProps --> InitComplete[Inicialização Completa]
    
    InitComplete --> ConnectCall{ZowsupClient.connect<br/>chamado?}
    ConnectCall -->|Sim| StartThread[ZowsupClient._start_stack_thread<br/>Inicia thread do stack]
    ConnectCall -->|Não| WaitConnect[Aguarda chamada de connect]
    WaitConnect --> ConnectCall
    
    StartThread --> BotRun[YowBot.run<br/>Executa em thread separada]
    BotRun --> EmitConnect[YowBot._stack.broadcastEvent<br/>EVENT_STATE_CONNECT]
    EmitConnect --> StackLoop[YowStack.loop<br/>Inicia loop de eventos]
    
    StackLoop --> NetworkLayer[YowNetworkLayer recebe<br/>EVENT_STATE_CONNECT]
    NetworkLayer --> CreateDispatcher[YowNetworkLayer.__create_dispatcher<br/>Cria dispatcher de conexão]
    CreateDispatcher --> TCPConnect[AsyncoreConnectionDispatcher.connect<br/>ou SocketConnectionDispatcher.connect<br/>Estabelece conexão TCP]
    
    TCPConnect -->|Sucesso| OnConnected[YowNetworkLayer.onConnected<br/>Conexão TCP estabelecida]
    TCPConnect -->|Erro| TCPError[Erro de Conexão TCP]
    TCPError --> Disconnect[Desconecta e finaliza]
    
    OnConnected --> EmitConnected[YowNetworkLayer.emitEvent<br/>EVENT_STATE_CONNECTED]
    EmitConnected --> AuthLayer[YowAuthenticationProtocolLayer.on_connected<br/>Recebe EVENT_STATE_CONNECTED]
    AuthLayer --> EmitAuth[YowAuthenticationProtocolLayer.broadcastEvent<br/>EVENT_AUTH]
    
    EmitAuth --> NoiseLayer[YowNoiseLayer.on_auth<br/>Recebe EVENT_AUTH]
    NoiseLayer --> CheckBotType{BotType é<br/>REG_COMPANION?}
    
    CheckBotType -->|Sim| RegMode[Modo Registro/Companion]
    CheckBotType -->|Não| LoginMode[Modo Login Normal]
    
    %% Modo Registro
    RegMode --> RegGetInfo[YowNoiseLayer.getProp<br/>'reg_info': keypair, regid, identity, signedprekey]
    RegGetInfo --> RegBuildConfig[YowNoiseLayer._build_client_config<br/>ClientConfig com username=None]
    RegBuildConfig --> RegSendHeader[YowNoiseLayer.toLower<br/>HEADER = b'WA\x06\x03']
    RegSendHeader --> RegCreateWorker[WANoiseProtocolHandshakeWorker.__init__<br/>Cria worker de handshake]
    RegCreateWorker --> RegStartWorker[WANoiseProtocolHandshakeWorker.start<br/>Inicia handshake em thread]
    RegStartWorker --> HandshakeWorker[Worker Thread: Handshake]
    
    %% Modo Login
    LoginMode --> LoadProfile[YowNoiseLayer._profile.config<br/>Carrega configuração do profile]
    LoadProfile --> LoadKeys[Carrega chaves:<br/>- local_static (client_static_keypair)<br/>- username<br/>- device]
    LoadKeys --> CheckStatic{client_static_keypair<br/>existe?}
    
    CheckStatic -->|Não| StaticError[Erro: chave estática não definida]
    StaticError --> Disconnect
    
    CheckStatic -->|Sim| CheckEdge{edge_routing_info<br/>existe?}
    CheckEdge -->|Sim| SendEdgeHeader[YowNoiseLayer.toLower<br/>EDGE_HEADER = b'ED\x00\x01']
    SendEdgeHeader --> SendEdgeInfo[YowNoiseLayer.toLower<br/>edge_routing_info]
    SendEdgeInfo --> SendMainHeader[YowNoiseLayer.toLower<br/>HEADER = b'WA\x06\x03']
    CheckEdge -->|Não| SendMainHeader
    
    SendMainHeader --> GetRemoteStatic[YowNoiseLayer._profile.config<br/>server_static_public]
    GetRemoteStatic --> BuildClientConfig[YowNoiseLayer._build_client_config<br/>Cria ClientConfig com username e pushname]
    BuildClientConfig --> CheckRS{Remote Static<br/>RS existe?}
    
    CheckRS -->|Sim| HasRS[Usa chave RS salva]
    CheckRS -->|Não| NoRS[Sem chave RS]
    
    HasRS --> CreateWorkerIK[WANoiseProtocolHandshakeWorker.__init__<br/>rs=remote_static]
    NoRS --> CreateWorkerXX[WANoiseProtocolHandshakeWorker.__init__<br/>rs=None]
    
    CreateWorkerIK --> StartWorkerIK[WANoiseProtocolHandshakeWorker.start<br/>Inicia handshake IK]
    CreateWorkerXX --> StartWorkerXX[WANoiseProtocolHandshakeWorker.start<br/>Inicia handshake XX]
    
    StartWorkerIK --> HandshakeWorker
    StartWorkerXX --> HandshakeWorker
    RegStartWorker --> HandshakeWorker
    
    %% Handshake Worker Thread
    HandshakeWorker --> ProtocolStart[WANoiseProtocol.start<br/>Inicia protocolo Noise]
    ProtocolStart --> StateInit[WANoiseProtocol._machine.start<br/>Estado: INIT → HANDSHAKE]
    StateInit --> CreateHandshake[WAHandshake.__init__<br/>version_major=6, version_minor=3]
    CreateHandshake --> SetHandshakeMode[WAHandshake.setmode<br/>WAHandshake.setIdentity<br/>WAHandshake.setRegistrationId<br/>WAHandshake.setSignedPreKey<br/>WAHandshake.setDeviceId]
    
    SetHandshakeMode --> HandshakePerform[WAHandshake.perform<br/>client_config, stream, s, rs]
    HandshakePerform --> CheckRS2{rs presente?}
    
    CheckRS2 -->|Sim| IKHandshake[Handshake IK]
    CheckRS2 -->|Não| XXHandshake[Handshake XX]
    
    %% Handshake IK
    IKHandshake --> IKInit[WAHandshake._handshakestate.initialize<br/>HandshakePattern: IKHandshakePattern<br/>initiator=True, prologue=b'WA\x06\x03']
    IKInit --> IKCreatePayload[WAHandshake._create_full_payload<br/>Cria ClientPayload com username e pushname]
    IKCreatePayload --> IKWriteMessage[WAHandshake._handshakestate.write_message<br/>client_payload.SerializeToString]
    IKWriteMessage --> IKSplit[ByteUtil.split<br/>ephemeral, static, payload]
    IKSplit --> IKCreateHello[wa5_pb2.HandshakeMessage.ClientHello<br/>ephemeral, static, payload]
    IKCreateHello --> IKSend[SegmentedStream.write_segment<br/>Envia ClientHello]
    
    IKSend --> IKWait[SegmentedStream.read_segment<br/>Aguarda ServerHello]
    IKWait --> IKParse[wa5_pb2.HandshakeMessage.ParseFromString<br/>Parse ServerHello]
    IKParse --> IKCheckStatic{ServerHello tem<br/>campo 'static'?}
    
    IKCheckStatic -->|Sim| IKNewRS[NewRemoteStaticException<br/>Nova chave estática detectada]
    IKNewRS --> XXFallback[Fallback para XX]
    IKCheckStatic -->|Não| IKReadMessage[WAHandshake._handshakestate.read_message<br/>server_hello.ephemeral + static + payload]
    
    IKReadMessage --> IKGetCipher[Obtém CipherStatePair<br/>cipherstatepair]
    IKGetCipher --> HandshakeSuccess[Handshake Concluído]
    
    %% Handshake XX
    XXHandshake --> XXInit[WAHandshake._handshakestate.initialize<br/>HandshakePattern: XXHandshakePattern<br/>initiator=True, prologue=b'WA\x06\x03']
    XXInit --> XXCreatePayload[WAHandshake._create_full_payload<br/>Cria ClientPayload]
    XXCreatePayload --> XXWriteMessage1[WAHandshake._handshakestate.write_message<br/>b'' - apenas ephemeral]
    XXWriteMessage1 --> XXCreateHello[wa5_pb2.HandshakeMessage.ClientHello<br/>ephemeral]
    XXCreateHello --> XXSend[SegmentedStream.write_segment<br/>Envia ClientHello]
    
    XXSend --> XXWait[SegmentedStream.read_segment<br/>Aguarda ServerHello]
    XXWait --> XXParse[wa5_pb2.HandshakeMessage.ParseFromString<br/>Parse ServerHello]
    XXParse --> XXReadMessage[WAHandshake._handshakestate.read_message<br/>server_hello.ephemeral + static + payload]
    XXReadMessage --> XXValidateCert[CertMan.is_valid<br/>Valida certificado do servidor]
    
    XXValidateCert -->|Inválido| CertError[Erro: Certificado inválido]
    CertError --> HandshakeFailed[Handshake Falhou]
    HandshakeFailed --> Disconnect
    
    XXValidateCert -->|Válido| XXWriteMessage2[WAHandshake._handshakestate.write_message<br/>client_payload.SerializeToString]
    XXWriteMessage2 --> XXSplit[ByteUtil.split<br/>static, payload]
    XXSplit --> XXCreateFinish[wa5_pb2.HandshakeMessage.ClientFinish<br/>static, payload]
    XXCreateFinish --> XXSendFinish[SegmentedStream.write_segment<br/>Envia ClientFinish]
    XXSendFinish --> XXGetCipher[Obtém CipherStatePair<br/>cipherstatepair]
    XXGetCipher --> HandshakeSuccess
    
    %% Fallback XX
    XXFallback --> XXFallbackSwitch[WAHandshake._handshakestate.switch<br/>FallbackPatternModifier + XXHandshakePattern]
    XXFallbackSwitch --> XXFallbackRead[WAHandshake._handshakestate.read_message<br/>server_hello já recebido]
    XXFallbackRead --> XXFallbackValidate[CertMan.is_valid<br/>Valida certificado]
    XXFallbackValidate -->|Inválido| CertError
    XXFallbackValidate -->|Válido| XXFallbackWrite[WAHandshake._handshakestate.write_message<br/>client_payload]
    XXFallbackWrite --> XXFallbackSplit[ByteUtil.split<br/>static, payload]
    XXFallbackSplit --> XXFallbackFinish[wa5_pb2.HandshakeMessage.ClientFinish]
    XXFallbackFinish --> XXFallbackSend[SegmentedStream.write_segment<br/>Envia ClientFinish]
    XXFallbackSend --> XXFallbackGetCipher[Obtém CipherStatePair]
    XXFallbackGetCipher --> HandshakeSuccess
    
    %% Após Handshake
    HandshakeSuccess --> SaveRS[Salva nova RS se obtida<br/>YowNoiseLayer._rs = handshake.rs]
    SaveRS --> CreateTransport[WANoiseTransport.__init__<br/>stream, cipherstate[0], cipherstate[1]]
    CreateTransport --> ProtocolFinish[WANoiseProtocol._machine.finish<br/>Estado: HANDSHAKE → TRANSPORT]
    ProtocolFinish --> CallbackFinish[WANoiseProtocolHandshakeWorker.finish_callback<br/>on_handshake_finished]
    
    CallbackFinish --> OnHandshakeFinished[YowNoiseLayer.on_handshake_finished<br/>Handshake concluído com sucesso]
    OnHandshakeFinished --> SaveClientConfig[Salva ClientConfig no profile<br/>se necessário]
    SaveClientConfig --> EnableSegments[YowNoiseLayer.setProp<br/>YowNoiseSegmentsLayer.PROP_ENABLED = True]
    EnableSegments --> EmitAuthed[YowNoiseLayer.broadcastEvent<br/>EVENT_AUTHED]
    
    EmitAuthed --> AuthProtocolLayer[YowAuthenticationProtocolLayer.on_authed<br/>Recebe EVENT_AUTHED]
    AuthProtocolLayer --> SendAuthMessage[YowAuthenticationProtocolLayer.send_auth<br/>Envia mensagem de autenticação]
    SendAuthMessage --> TransportSend[WANoiseTransport.send<br/>Dados criptografados]
    TransportSend --> WaitResponse[Aguarda resposta do servidor]
    
    WaitResponse --> TransportRecv[WANoiseTransport.recv<br/>Recebe dados descriptografados]
    TransportRecv --> ParseResponse[Parse mensagem de resposta]
    ParseResponse --> CheckResponse{Tipo de resposta?}
    
    CheckResponse -->|success| OnSuccess[SendLayer.onSuccess<br/>ProtocolEntityCallback 'success']
    CheckResponse -->|failure| OnFailure[SendLayer.onFailure<br/>ProtocolEntityCallback 'failure']
    CheckResponse -->|stream:error| OnStreamError[SendLayer.onStreamError<br/>ProtocolEntityCallback 'stream:error']
    
    OnSuccess --> SetConnected[SendLayer.isConnected = True<br/>_login_failed = False]
    SetConnected --> ClearLoginFlag[SendLayer._login_in_progress = False]
    ClearLoginFlag --> SetEvent[SendLayer.loginEvent.set<br/>Acorda waitLogin]
    SetEvent --> UpdateDB[update_account_status<br/>is_logged_in=True]
    UpdateDB --> LoginSuccess([Login Concluído com Sucesso])
    
    OnFailure --> LoginFailed([Login Falhou])
    OnStreamError --> LoginFailed
    
    %% Estilos
    classDef startEnd fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    classDef process fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef error fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef success fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef handshake fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    
    class Start,InitComplete,LoginSuccess,LoginFailed,Disconnect startEnd
    class InitLog,BuildConfig,LoadEnv,LoadProxy,InitStack,CreateBot,CreateProfile,CreateSendLayer,BuildStack,SetProps,StartThread,BotRun,EmitConnect,StackLoop,NetworkLayer,CreateDispatcher,TCPConnect,OnConnected,EmitConnected,AuthLayer,EmitAuth,NoiseLayer,RegMode,RegGetInfo,RegBuildConfig,RegSendHeader,RegCreateWorker,RegStartWorker,LoadProfile,LoadKeys,GetRemoteStatic,BuildClientConfig,HasRS,NoRS,CreateWorkerIK,CreateWorkerXX,StartWorkerIK,StartWorkerXX,ProtocolStart,StateInit,CreateHandshake,SetHandshakeMode,HandshakePerform,IKInit,IKCreatePayload,IKWriteMessage,IKSplit,IKCreateHello,IKSend,IKWait,IKParse,IKReadMessage,IKGetCipher,XXInit,XXCreatePayload,XXWriteMessage1,XXCreateHello,XXSend,XXWait,XXParse,XXReadMessage,XXValidateCert,XXWriteMessage2,XXSplit,XXCreateFinish,XXSendFinish,XXGetCipher,XXFallbackSwitch,XXFallbackRead,XXFallbackValidate,XXFallbackWrite,XXFallbackSplit,XXFallbackFinish,XXFallbackSend,XXFallbackGetCipher,SaveRS,CreateTransport,ProtocolFinish,CallbackFinish,OnHandshakeFinished,SaveClientConfig,EnableSegments,EmitAuthed,AuthProtocolLayer,SendAuthMessage,TransportSend,WaitResponse,TransportRecv,ParseResponse,SetConnected,ClearLoginFlag,SetEvent,UpdateDB process
    class ConnectCall,CheckBotType,CheckStatic,CheckEdge,CheckRS,CheckRS2,IKCheckStatic,CheckResponse decision
    class TCPError,StaticError,CertError,HandshakeFailed,OnFailure,OnStreamError error
    class HandshakeSuccess,LoginSuccess success
    class IKHandshake,XXHandshake,XXFallback,HandshakeWorker handshake
```

---

## Descrição Detalhada por Etapa

### 1. Inicialização do ZowsupClient

**Classe:** `ZowsupClient`  
**Arquivo:** `zowsuplib/app/api.py`

#### Métodos e Ordem de Execução:

1. **`ZowsupClient.__init__`** (linha 1219)
   - Inicializa sistema de logs: `Utils.init_log()`
   - Cria configuração: `self._build_account_config()`
   - Carrega ambiente: `DeviceEnv(device_env_name, random=True)`
   - Configura proxy: `NetworkEnv(NetworkEnv.TYPE_DIRECT)` ou `NetworkEnv(NetworkEnv.TYPE_PROXY, proxyStr=proxy)`
   - Carrega proxy do DB: `self._load_proxy_from_db()`
   - Inicializa stack: `self._init_send_layer_stack(device_env, self.network_env)`

2. **`ZowsupClient._init_send_layer_stack`** (método interno)
   - Cria `YowBot`: `YowBot(bot_id=account_id, env=BotEnv(...), bot_type=YowBotType.TYPE_RUN_AUTO)`
   - Obtém `SendLayer`: `self.send_layer = self.bot.sendLayer`

### 2. Inicialização do YowBot

**Classe:** `YowBot`  
**Arquivo:** `zowsuplib/app/yowbot.py`

#### Métodos e Ordem de Execução:

1. **`YowBot.__init__`** (linha 39)
   - Cria `YowStackBuilder`: `YowStackBuilder()`
   - Cria `SendLayer`: `SendLayer(self)`
   - Cria `BotEnv`: `BotEnv(deviceEnv=DeviceEnv(...), networkEnv=NetworkEnv(...))`
   - Cria `YowProfile`: `YowProfile(self.botId)`
   - Constrói stack: `stackBuilder.pushDefaultLayers().push(self.sendLayer).build()`
   - Define propriedades: `self._stack.setProp("env", self.env)`, `setProp("ID_TYPE", self.idType)`, `setProp("botId", self.botId)`

### 3. Conexão TCP

**Classe:** `ZowsupClient` → `YowBot` → `YowNetworkLayer`

#### Métodos e Ordem de Execução:

1. **`ZowsupClient.connect`** (linha 1346)
   - Inicia thread: `self._stack_thread = self._start_stack_thread()`
   - Aguarda login: `self.send_layer.waitLogin()` (se `wait_login=True`)

2. **`ZowsupClient._start_stack_thread`** (método interno)
   - Cria thread: `threading.Thread(target=self._run_stack_thread)`
   - Thread executa: `self.bot.run()`

3. **`YowBot.run`** (linha 133)
   - Emite evento: `self._stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))`
   - Inicia loop: `self._stack.loop()`

4. **`YowNetworkLayer`** (recebe `EVENT_STATE_CONNECT`)
   - Cria dispatcher: `self.__create_dispatcher(dispatcher_type)`
   - Estabelece conexão: `AsyncoreConnectionDispatcher.connect()` ou `SocketConnectionDispatcher.connect()`
   - Quando conectado: `self.onConnected()`
   - Emite evento: `self.emitEvent(YowLayerEvent(EVENT_STATE_CONNECTED))`

### 4. Início do Handshake

**Classe:** `YowAuthenticationProtocolLayer` → `YowNoiseLayer`

#### Métodos e Ordem de Execução:

1. **`YowAuthenticationProtocolLayer.on_connected`** (linha 32)
   - Recebe `EVENT_STATE_CONNECTED`
   - Emite evento: `self.broadcastEvent(YowLayerEvent(self.EVENT_AUTH))`

2. **`YowNoiseLayer.on_auth`** (linha 105)
   - Recebe `EVENT_AUTH`
   - Verifica `botType`: `self.getProp("botType")`
   - Se `TYPE_REG_COMPANION_*`: Modo Registro
   - Senão: Modo Login Normal

### 5. Modo Login Normal - Preparação

**Classe:** `YowNoiseLayer`

#### Métodos e Ordem de Execução:

1. **Carregamento de Dados** (linha 214-258)
   - `self._profile.config`: Carrega configuração
   - `config.client_static_keypair`: Chave estática local
   - `self._profile.username`: Username
   - `config.device`: Device ID
   - `config.server_static_public`: Remote Static (RS) - se existir

2. **Envio de Headers** (linha 260-272)
   - Se `edge_routing_info` existe:
     - `self.toLower(self.EDGE_HEADER)`: `b'ED\x00\x01'`
     - `self.toLower(config.edge_routing_info)`
   - `self.toLower(self.HEADER)`: `b'WA\x06\x03'`

3. **Criação do ClientConfig** (linha 281)
   - `self._build_client_config(config, yowsupenv, username, passive, device)`
   - Retorna `ClientConfig` com username, pushname, useragent, etc.

4. **Criação do Handshake Worker** (linha 304-320)
   - Verifica se já está em handshake: `self._in_handshake()`
   - Reseta stream se cancelado: `self._stream.reset()`
   - Cria worker: `WANoiseProtocolHandshakeWorker(self._wa_noiseprotocol, self._stream, client_config, keypair, rs=remote_static, ...)`
   - Inicia worker: `self._handshake_worker.start()`

### 6. Handshake Worker Thread

**Classe:** `WANoiseProtocolHandshakeWorker` → `WANoiseProtocol` → `WAHandshake`

#### Métodos e Ordem de Execução:

1. **`WANoiseProtocolHandshakeWorker.run`** (worker thread)
   - Chama: `self.protocol.start(stream, client_config, s, rs, mode, identity, regid, signedprekey, deviceid)`

2. **`WANoiseProtocol.start`** (linha 103)
   - Muda estado: `self._machine.start()` (INIT → HANDSHAKE)
   - Cria handshake: `WAHandshake(self._version_major, self._version_minor)`
   - Configura handshake: `handshake.setmode(mode)`, `handshake.setIdentity(identity)`, etc.
   - Executa handshake: `handshake.perform(client_config, stream, s, rs)`

### 7. Handshake IK (se RS existe)

**Classe:** `WAHandshake`  
**Arquivo:** `zowsuplib/consonance/handshake.py`

#### Métodos e Ordem de Execução:

1. **`WAHandshake.perform`** (linha 69)
   - Verifica `rs`: Se presente, usa IK; senão, usa XX

2. **`WAHandshake._start_handshake_ik`** (linha 262)
   - Inicializa: `self._handshakestate.initialize(IKHandshakePattern(), initiator=True, prologue=self._prologue, s=s, rs=rs)`
   - Cria payload: `self._create_full_payload(client_config, s)`
   - Escreve mensagem: `self._handshakestate.write_message(client_payload.SerializeToString(), message_buffer)`
   - Divide: `ByteUtil.split(message_buffer, 32, 48, len)`: ephemeral, static, payload
   - Cria ClientHello: `wa5_pb2.HandshakeMessage.ClientHello(ephemeral, static, payload)`
   - Envia: `stream.write_segment(handshakemessage.SerializeToString())`

3. **Aguarda ServerHello**
   - Lê: `stream.read_segment()`
   - Parse: `wa5_pb2.HandshakeMessage.ParseFromString(segment_data)`
   - Verifica: `server_hello.HasField("static")` → Se sim, lança `NewRemoteStaticException`
   - Lê mensagem: `self._handshakestate.read_message(server_hello.ephemeral + static + payload, payload_buffer)`
   - Retorna: `CipherStatePair` (cipherstate[0], cipherstate[1])

### 8. Handshake XX (se RS não existe ou fallback)

**Classe:** `WAHandshake`

#### Métodos e Ordem de Execução:

1. **`WAHandshake._start_handshake_xx`** (linha 193)
   - Inicializa: `self._handshakestate.initialize(XXHandshakePattern(), initiator=True, prologue=self._prologue, s=s)`
   - Escreve mensagem vazia: `self._handshakestate.write_message(b'', ephemeral_public)` (gera apenas ephemeral)
   - Cria ClientHello: `wa5_pb2.HandshakeMessage.ClientHello(ephemeral)`
   - Envia: `stream.write_segment(handshakemessage.SerializeToString())`

2. **Aguarda ServerHello**
   - Lê: `stream.read_segment()`
   - Parse: `wa5_pb2.HandshakeMessage.ParseFromString(segment_data)`
   - Lê mensagem: `self._handshakestate.read_message(server_hello.ephemeral + static + payload, payload_buffer)`
   - Valida certificado: `CertMan.is_valid(self._handshakestate.rs, bytes(payload_buffer))`

3. **Envia ClientFinish**
   - Cria payload: `self._create_full_payload(client_config, s)`
   - Escreve mensagem: `self._handshakestate.write_message(client_payload.SerializeToString(), message_buffer)`
   - Divide: `ByteUtil.split(message_buffer, 48, len)`: static, payload
   - Cria ClientFinish: `wa5_pb2.HandshakeMessage.ClientFinish(static, payload)`
   - Envia: `stream.write_segment(outgoing_handshakemessage.SerializeToString())`
   - Retorna: `CipherStatePair`

### 9. Fallback XX (quando IK detecta nova RS)

**Classe:** `WAHandshake`

#### Métodos e Ordem de Execução:

1. **`WAHandshake._switch_handshake_xxfallback`** (linha 150)
   - Switch: `self._handshakestate.switch(FallbackPatternModifier().modify(XXHandshakePattern()), initiator=True, prologue=self._prologue, s=s)`
   - Lê ServerHello já recebido: `self._handshakestate.read_message(server_hello.ephemeral + static + payload, payload_buffer)`
   - Valida certificado: `CertMan.is_valid(self._handshakestate.rs, bytes(payload_buffer))`
   - Envia ClientFinish: Similar ao XX normal
   - Retorna: `CipherStatePair`

### 10. Criação do Transporte

**Classe:** `WANoiseProtocol` → `WANoiseTransport`

#### Métodos e Ordem de Execução:

1. **`WANoiseProtocol.start`** (após handshake)
   - Salva RS: `self._rs = handshake.rs`
   - Cria transporte: `WANoiseTransport(stream, result[0], result[1])` (cipherstates)
   - Muda estado: `self._machine.finish()` (HANDSHAKE → TRANSPORT)

2. **`WANoiseProtocolHandshakeWorker.run`** (callback)
   - Chama: `self.finish_callback(cipherstatepair)`

3. **`YowNoiseLayer.on_handshake_finished`** (callback)
   - Salva ClientConfig se necessário
   - Habilita segmentos: `self.setProp(YowNoiseSegmentsLayer.PROP_ENABLED, True)`
   - Emite evento: `self.broadcastEvent(YowLayerEvent(YowAuthenticationProtocolLayer.EVENT_AUTHED))`

### 11. Autenticação Final

**Classe:** `YowAuthenticationProtocolLayer` → `SendLayer`

#### Métodos e Ordem de Execução:

1. **`YowAuthenticationProtocolLayer.on_authed`** (recebe `EVENT_AUTHED`)
   - Envia mensagem de autenticação: `self.send_auth()`
   - Usa transporte: `WANoiseTransport.send(data)`

2. **Aguarda Resposta**
   - Recebe: `WANoiseTransport.recv()`
   - Parse: Mensagem de resposta do servidor

3. **`SendLayer.onSuccess`** (linha 1114)
   - Recebe `ProtocolEntityCallback("success")`
   - Define: `self.isConnected = True`
   - Limpa flag: `self._login_in_progress = False`
   - Acorda evento: `self.loginEvent.set()` (desbloqueia `waitLogin()`)
   - Atualiza DB: `update_account_status(self.bot.botId, is_logged_in=True)`

4. **`SendLayer.waitLogin`** (desbloqueado)
   - Retorna: `True` (login concluído)

---

## Classes e Métodos Principais

### ZowsupClient
- `__init__`: Inicialização do cliente
- `connect`: Inicia conexão e aguarda login
- `_init_send_layer_stack`: Cria stack com SendLayer
- `_start_stack_thread`: Inicia thread do stack

### YowBot
- `__init__`: Inicialização do bot
- `run`: Executa loop principal e emite eventos

### YowNetworkLayer
- `onConnected`: Callback quando TCP conecta
- `emitEvent`: Emite `EVENT_STATE_CONNECTED`

### YowAuthenticationProtocolLayer
- `on_connected`: Recebe `EVENT_STATE_CONNECTED`, emite `EVENT_AUTH`
- `on_authed`: Recebe `EVENT_AUTHED`, envia mensagem de autenticação

### YowNoiseLayer
- `on_auth`: Recebe `EVENT_AUTH`, inicia handshake
- `on_handshake_finished`: Callback quando handshake completa
- `_build_client_config`: Cria ClientConfig

### WANoiseProtocol
- `start`: Inicia protocolo, cria WAHandshake, executa handshake
- `_machine.finish`: Muda estado para TRANSPORT

### WAHandshake
- `perform`: Executa handshake (IK ou XX)
- `_start_handshake_ik`: Handshake IK
- `_start_handshake_xx`: Handshake XX
- `_switch_handshake_xxfallback`: Fallback XX
- `_create_full_payload`: Cria ClientPayload

### WANoiseTransport
- `send`: Envia dados criptografados
- `recv`: Recebe e descriptografa dados

### SendLayer
- `waitLogin`: Aguarda conclusão do login
- `onSuccess`: Callback quando recebe 'success'
- `onFailure`: Callback quando recebe 'failure'

---

## Estados do Protocolo

1. **INIT**: Estado inicial
2. **HANDSHAKE**: Handshake em progresso
3. **TRANSPORT**: Handshake concluído, transporte criptografado ativo
4. **ERROR**: Erro no protocolo

---

## Notas Importantes

1. **Isolamento**: Cada `ZowsupClient` é completamente isolado (profile, stack, bot, callbacks)
2. **Threading**: Handshake executa em thread separada (`WANoiseProtocolHandshakeWorker`)
3. **Fallback**: Sistema suporta fallback automático de IK para XX quando servidor retorna nova RS
4. **Validação**: Certificado do servidor é validado em todos os handshakes
5. **Timeout**: Handshake tem timeout configurável (padrão: 30 segundos)
6. **Stream**: Stream é resetado antes de cada novo handshake para evitar dados antigos


