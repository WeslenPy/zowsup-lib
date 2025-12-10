# Estratégia Anti-Banimento para Envio de Mensagens

Este documento descreve a estratégia implementada para reduzir a taxa de banimento/restrição de contas ao enviar mensagens para números desconhecidos no WhatsApp.

## Problema Identificado

Quando uma conta envia mensagens para números desconhecidos, o WhatsApp pode aplicar restrições ou banimentos devido a comportamento suspeito detectado pelo sistema. Os principais fatores que levam a isso são:

1. **Envio imediato para números não sincronizados**
2. **Falta de validação se o número existe no WhatsApp**
3. **Envio muito frequente (rate limiting)**
4. **Comportamento robótico (delays fixos e previsíveis)**
5. **Falta de verificação de restrições da conta**

## Estratégia Implementada

### 1. Verificação de Restrições da Conta

Antes de qualquer envio, o sistema verifica se a conta está com restrição:

```python
def _check_account_restriction(self):
    # Verifica no banco de dados se a conta tem has_restriction=True
    # Se sim, bloqueia o envio imediatamente
```

**Benefício**: Evita tentar enviar quando a conta já está restrita, o que poderia piorar a situação.

### 2. Rate Limiting Inteligente

Implementa controle de frequência de envio:

- **Por destinatário**: Delay mínimo entre mensagens para o mesmo destinatário
  - Contatos individuais: 3 segundos mínimo
  - Grupos: 1.5 segundos mínimo
- **Diário**: Limite máximo de mensagens por dia (padrão: 50)
- **Thread-safe**: Usa locks para garantir segurança em ambientes multi-thread

**Benefício**: Evita envios muito frequentes que são detectados como spam.

### 3. Validação de Números Antes de Enviar

Antes de enviar para um número desconhecido:

1. **Sincroniza o contato** com o WhatsApp
2. **Valida o resultado**:
   - Verifica se o número está em `inNumbers` (válido)
   - Verifica se o número está em `outNumbers` (válido)
   - Verifica se o número está em `invalidUsers` (inválido)
3. **Marca números inválidos** para evitar tentativas futuras
4. **Não envia** se o número for inválido

**Benefício**: Evita tentar enviar para números que não existem no WhatsApp, o que é um sinal forte de spam.

### 4. Delays Human-Like

Simula comportamento humano usando delays variáveis:

```python
def _human_like_delay(self, base_delay=2.0, variation=1.0):
    # Gera delay aleatório entre base_delay e base_delay + variation
    delay = base_delay + random.uniform(0, variation)
```

**Aplicado em**:
- Antes de confiar em um contato: 2.0-3.5 segundos
- Antes de enviar mensagem: 3.0-5.0 segundos
- Indicador de digitação: 1.5-2.5 segundos (grupos) ou 2.5-4.0 segundos (individuais)

**Benefício**: Comportamento menos previsível e mais natural, dificultando detecção de bot.

### 5. Controle de Sincronização

Evita sincronizações muito frequentes do mesmo número:

- **Intervalo mínimo**: 30 segundos entre sincronizações do mesmo número
- **Cache de sincronização**: Armazena timestamp da última sincronização

**Benefício**: Reduz carga no servidor e evita comportamento suspeito.

### 6. Tratamento de Erros Robusto

- **Números inválidos**: Marcados e não tentados novamente
- **Erros de sincronização**: Não tenta enviar se falhar
- **Exceções críticas**: Re-lançadas para tratamento adequado

**Benefício**: Evita loops de tentativas que podem ser detectados como spam.

## Fluxo Completo de Envio

```
1. Verifica se conta está restrita → Se sim, BLOQUEIA
2. Verifica limite diário → Se excedido, BLOQUEIA
3. Normaliza JID do destinatário
4. Verifica se número está na lista de inválidos → Se sim, BLOQUEIA
5. Verifica se contato já existe:
   - Se SIM: Aplica rate limiting e ENVIA
   - Se NÃO: Continua...
6. Verifica intervalo de sincronização → Aguarda se necessário
7. Sincroniza contato com WhatsApp
8. Valida resultado da sincronização:
   - Se inválido: Marca como inválido e BLOQUEIA
   - Se válido: Continua...
9. Aguarda delay human-like (2-3.5s)
10. Confia no contato
11. Aguarda delay human-like (3-5s)
12. Aplica rate limiting
13. Envia indicador de digitação
14. Aguarda delay human-like (1.5-6s dependendo do tipo)
15. ENVIA MENSAGEM
```

## Configurações Recomendadas

### Para Contas Novas (Menos Restritivas)
- `max_messages_per_day`: 30-50
- `min_delay_seconds` (individuais): 3-5 segundos
- `min_delay_seconds` (grupos): 1.5-3 segundos

### Para Contas Estabelecidas (Mais Permissivas)
- `max_messages_per_day`: 50-100
- `min_delay_seconds` (individuais): 2-4 segundos
- `min_delay_seconds` (grupos): 1-2 segundos

## Monitoramento

O sistema registra no banco de dados:
- Status de restrição da conta (`has_restriction`)
- Mensagens enviadas (`SentMessage`)
- Números inválidos (em memória, `_invalid_numbers`)

**Recomendação**: Monitore regularmente:
- Taxa de restrições
- Taxa de números inválidos
- Frequência de envios

## Melhores Práticas

1. **Sempre sincronize antes de enviar** para números desconhecidos
2. **Respeite os delays** - não reduza os tempos mínimos
3. **Monitore restrições** - se uma conta for restrita, pare imediatamente
4. **Valide números** antes de adicionar a uma lista de envio
5. **Use delays variáveis** - nunca use delays fixos
6. **Limite envios diários** - não exceda o limite configurado
7. **Evite envios em massa** - distribua ao longo do dia

## Troubleshooting

### Conta sendo restrita mesmo com a estratégia

1. **Verifique o limite diário**: Pode estar muito alto
2. **Aumente os delays**: Tente aumentar `min_delay_seconds`
3. **Reduza frequência**: Diminua `max_messages_per_day`
4. **Verifique números**: Muitos números inválidos podem ser um sinal de spam
5. **Aguarde entre sessões**: Não envie imediatamente após login

### Números válidos sendo marcados como inválidos

1. **Verifique a sincronização**: Pode estar falhando
2. **Aguarde mais tempo**: Alguns números podem demorar para sincronizar
3. **Verifique formato**: Certifique-se de que o número está no formato correto

## Implementação Técnica

A estratégia está implementada principalmente em:
- `app/yowbot_layer.py`: Métodos `assureContactsAndSend`, `sendMsgDirect`, e métodos auxiliares
- `yowsup/layers/protocol_contacts/protocolentities/iq_sync_result.py`: Parser para capturar números inválidos

## Conclusão

Esta estratégia reduz significativamente a taxa de banimento ao:
- Validar números antes de enviar
- Simular comportamento humano
- Respeitar limites de rate
- Verificar restrições proativamente

**Importante**: A estratégia não garante 100% de proteção, mas reduz drasticamente o risco quando seguida corretamente.

