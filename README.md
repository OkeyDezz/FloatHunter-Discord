# 🎯 Opportunity Bot

Bot automatizado para capturar oportunidades de arbitragem no CSGOEmpire comparando preços com Buff163.

## 🚀 Funcionalidades

- **Monitoramento em tempo real** via WebSocket do CSGOEmpire
- **Comparação automática** de preços com Buff163
- **Filtros inteligentes** por lucro e liquidez
- **Notificações automáticas** no Discord
- **Integração com Supabase** para dados de mercado
- **Health check** para Railway/Heroku

## 📋 Pré-requisitos

- Python 3.8+
- Conta no CSGOEmpire com API key
- Bot do Discord ou Webhook
- Projeto Supabase com tabelas configuradas

## 🛠️ Instalação

### 1. Clone o repositório
```bash
git clone <seu-repositorio>
cd opportunity-bot
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente
```bash
cp env.example .env
# Edite o arquivo .env com suas configurações
```

### 4. Execute o bot
```bash
python main.py
```

## ⚙️ Configuração

### Variáveis de Ambiente Obrigatórias

#### CSGOEmpire
- `CSGOEMPIRE_API_KEY`: Sua API key do CSGOEmpire

#### Discord (escolha uma opção)
- **Opção 1**: `DISCORD_WEBHOOK_URL` (webhook)
- **Opção 2**: `DISCORD_TOKEN` + `CSGOEMPIRE_CHANNEL_ID` (bot)

#### Supabase
- `SUPABASE_URL`: URL do seu projeto
- `SUPABASE_ANON_KEY`: Chave anônima

### Variáveis Opcionais

- `MIN_PRICE`: Preço mínimo em USD (padrão: $1.00)
- `MAX_PRICE`: Preço máximo em USD (padrão: $100.00)
- `MIN_PROFIT_PERCENTAGE`: Lucro mínimo % (padrão: 5.0%)
- `MIN_LIQUIDITY_SCORE`: Score de liquidez (padrão: 30.0)
- `COIN_TO_USD_FACTOR`: Fator conversão (padrão: 0.614)

## 🧪 Testes

Execute o script de teste para verificar se tudo está configurado corretamente:

```bash
python test_bot.py
```

Este script testa:
- ✅ Configurações
- ✅ Conexão com Supabase
- ✅ Discord Poster
- ✅ Filtros
- ✅ API do CSGOEmpire

## 🚀 Deploy no Railway

### 1. Conecte seu repositório
- Conecte o GitHub ao Railway
- Selecione o repositório `opportunity-bot`

### 2. Configure as variáveis de ambiente
No Railway, adicione todas as variáveis do arquivo `.env`:

```
CSGOEMPIRE_API_KEY=sua_api_key
DISCORD_TOKEN=seu_bot_token
CSGOEMPIRE_CHANNEL_ID=seu_channel_id
SUPABASE_URL=sua_url
SUPABASE_ANON_KEY=sua_chave
MIN_PRICE=1.0
MAX_PRICE=100.0
MIN_PROFIT_PERCENTAGE=5.0
MIN_LIQUIDITY_SCORE=30.0
COIN_TO_USD_FACTOR=0.614
WEBSOCKET_RECONNECT_DELAY=5
WEBSOCKET_MAX_RECONNECT_ATTEMPTS=10
LOG_LEVEL=INFO
LOG_TO_FILE=true
SCAN_INTERVAL_SECONDS=30
```

### 3. Deploy
- O Railway detectará automaticamente que é um projeto Python
- O build será executado automaticamente
- O bot iniciará usando `main.py`

## 🔧 Troubleshooting

### Bot não encontra itens

#### 1. Verifique os logs
```bash
# No Railway, vá em "Deployments" > "View Logs"
# Procure por mensagens de erro ou avisos
```

#### 2. Problemas comuns

**❌ "API key do CSGOEmpire não configurada"**
- Verifique se `CSGOEMPIRE_API_KEY` está definida no Railway
- Confirme se a API key é válida

**❌ "Falha na conexão com Supabase"**
- Verifique `SUPABASE_URL` e `SUPABASE_ANON_KEY`
- Confirme se as tabelas `market_data` e `liquidity` existem

**❌ "Discord webhook URL ou bot token não configurado"**
- Configure `DISCORD_WEBHOOK_URL` OU `DISCORD_TOKEN` + `CSGOEMPIRE_CHANNEL_ID`
- Verifique se o bot tem permissões no canal

**❌ "WebSocket desconectado após conexão"**
- Problema de autenticação com CSGOEmpire
- Verifique se a API key tem permissões de WebSocket

**❌ "Namespace /trade não está conectado"**
- Problema de conexão WebSocket
- Execute o teste de autenticação: `python test_auth.py`

**❌ "Usuário marcado como guest"**
- **PROBLEMA CRÍTICO**: Falha na autenticação WebSocket
- O servidor não reconhece o bot como usuário autenticado
- Execute: `python test_auth.py` para diagnosticar

#### 3. Teste localmente primeiro
```bash
# Execute o script de teste
python test_bot.py

# Se os testes passarem, execute o bot
python main.py
```

#### 4. Teste específico de autenticação WebSocket
```bash
# Teste apenas a autenticação WebSocket
python test_auth.py
```

Este script testa especificamente:
- ✅ Obtenção de metadata da API
- ✅ Conexão WebSocket
- ✅ Autenticação com o servidor
- ✅ Recebimento de eventos

### Logs importantes para monitorar

- `🔌 Conectado ao namespace /trade` - WebSocket conectado
- `✅ Autenticação confirmada pelo servidor` - Autenticado
- `🆕 NOVO ITEM RECEBIDO` - Itens sendo recebidos
- `🎯 OPORTUNIDADE ENCONTRADA` - Oportunidades detectadas

### Verificar status do bot

O bot inclui um health server que pode ser usado para verificar se está funcionando:

```bash
# No Railway, vá em "Settings" > "Domains"
# O health check estará disponível em: https://seu-app.railway.app/health
```

## 📊 Estrutura do Projeto

```
opportunity-bot/
├── core/
│   ├── marketplace_scanner.py    # Scanner principal
│   └── discord_poster.py        # Sistema de notificações
├── filters/
│   ├── profit_filter.py         # Filtro de lucro
│   └── liquidity_filter.py      # Filtro de liquidez
├── utils/
│   └── supabase_client.py       # Cliente Supabase
├── config/
│   └── settings.py              # Configurações
├── main.py                      # Ponto de entrada
├── test_bot.py                  # Script de teste geral
├── test_auth.py                 # Script de teste de autenticação
├── health_server.py             # Servidor de health check
└── requirements.txt             # Dependências
```

## 🔍 Como Funciona

1. **Conexão**: Bot se conecta ao WebSocket do CSGOEmpire
2. **Autenticação**: Usa API key para autenticar
3. **Monitoramento**: Escuta eventos `new_item`
4. **Filtros**: Aplica filtros de preço, lucro e liquidez
5. **Comparação**: Busca preços no Buff163 via Supabase
6. **Notificação**: Envia oportunidades para Discord
7. **Loop**: Continua monitorando indefinidamente

## 📝 Logs e Debug

### Níveis de log
- `INFO`: Informações gerais
- `DEBUG`: Detalhes técnicos
- `WARNING`: Avisos
- `ERROR`: Erros

### Habilitar logs detalhados
```bash
LOG_LEVEL=DEBUG
```

### Logs em arquivo
```bash
LOG_TO_FILE=true
```

## 🤝 Suporte

Se encontrar problemas:

1. **Execute o script de teste**: `python test_bot.py`
2. **Teste a autenticação**: `python test_auth.py`
3. **Verifique os logs** no Railway
4. **Confirme as variáveis de ambiente**
5. **Teste localmente** antes do deploy

## 📄 Licença

Este projeto é de uso pessoal. Não redistribua sem permissão.

---

**💡 Dica**: Sempre teste localmente antes de fazer deploy no Railway!