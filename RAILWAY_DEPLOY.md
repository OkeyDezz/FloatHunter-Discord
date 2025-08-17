# 🚀 Deploy no Railway

## 📋 Pré-requisitos

1. **Conta no Railway** ([railway.app](https://railway.app))
2. **Repositório GitHub** com o código do bot
3. **Variáveis de ambiente** configuradas

## 🔧 Configuração

### 1. Conectar Repositório
- Acesse [railway.app](https://railway.app)
- Clique em "New Project"
- Selecione "Deploy from GitHub repo"
- Escolha o repositório `FloatHunter-Discord`

### 2. Configurar Variáveis de Ambiente
No Railway, vá em **Variables** e adicione:

```env
# OBRIGATÓRIAS
CSGOEMPIRE_API_KEY=sua_api_key_aqui
DISCORD_TOKEN=seu_token_aqui
CSGOEMPIRE_CHANNEL_ID=123456789
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua_chave_anonima_aqui

# OPCIONAIS (valores padrão)
COIN_TO_USD_FACTOR=0.614
MIN_PROFIT_PERCENTAGE=5.0
MIN_LIQUIDITY_SCORE=70.0
MIN_PRICE=1.0
MAX_PRICE=1000.0
PORT=8000
```

### 3. Configurar Deploy

#### **Opção 1: Apenas Health Server (Recomendado para primeiro deploy)**
- **Start Command**: `python3 start_health.py`
- **Health Check Path**: `/health`
- **Port**: `8000`

#### **Opção 2: Bot Completo com Health Server**
- **Start Command**: `python3 start_full_bot.py`
- **Health Check Path**: `/health`
- **Port**: `8000`

#### **Opção 3: Bot Original**
- **Start Command**: `python3 main.py`
- **Health Check Path**: `/health`
- **Port**: `8000`

## 🚀 Deploy

### Primeiro Deploy (Recomendado)
1. Use **Opção 1** (`start_health.py`)
2. Deploy e aguarde funcionar
3. Verifique logs para confirmar health server rodando

### Deploy Completo
1. Após health server funcionar, mude para **Opção 2** (`start_full_bot.py`)
2. Redeploy
3. Verifique logs para confirmar bot funcionando

## 🔍 Verificação

### 1. Health Check
```bash
# Teste o endpoint de health
curl "https://seu-projeto.railway.app/health"
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "uptime_seconds": 30,
  "service": "opportunity-bot",
  "version": "1.0.0",
  "port": 8000
}
```

### 2. Status Detalhado
```bash
# Teste o endpoint de status
curl "https://seu-projeto.railway.app/status"
```

### 3. Logs
No Railway, vá em **Deployments** → **View Logs** e verifique:
- ✅ "Servidor de health check iniciado na porta 8000"
- ✅ "Health check disponível em: /health"
- ✅ Sem erros críticos

## 🚨 Troubleshooting

### Service Unavailable
Se ainda ocorrer "service unavailable":

1. **Verifique logs** no Railway
2. **Confirme variáveis** de ambiente
3. **Teste localmente** primeiro:
   ```bash
   python3 start_health.py
   curl http://localhost:8000/health
   ```

### Health Check Falha
1. **Verifique porta**: Confirme `PORT=8000`
2. **Verifique logs**: Procure por erros de inicialização
3. **Teste endpoints**: Use curl para testar localmente

### Bot Não Inicia
1. **Use Opção 1** primeiro (apenas health server)
2. **Verifique credenciais**: Supabase, Discord, CSGOEmpire
3. **Teste conexões** uma por vez

## 📊 Monitoramento

### Logs Importantes
- 🚀 "Servidor de health check iniciado"
- ✅ "Health server está funcionando!"
- 🤖 "Iniciando bot completo..."
- 🔍 "Conexão com Supabase OK"
- 🤖 "Discord inicializado com sucesso"

### Métricas
- **Uptime**: Verificado via `/health`
- **Status**: Detalhado via `/status`
- **Logs**: Disponíveis no Railway

## 🔄 Atualizações

### Deploy Automático
- Configure **GitHub Actions** para deploy automático
- Ou use **Railway CLI** para deploy manual

### Rollback
- Railway mantém histórico de deploys
- Clique em deploy anterior para rollback

## ✅ Checklist de Deploy

- [ ] Repositório conectado ao Railway
- [ ] Variáveis de ambiente configuradas
- [ ] Health server funcionando (`/health` responde)
- [ ] Logs sem erros críticos
- [ ] Bot funcionando (se usando Opção 2 ou 3)
- [ ] Discord recebendo mensagens
- [ ] CSGOEmpire conectando
- [ ] Supabase funcionando

## 🆘 Suporte

Se problemas persistirem:

1. **Verifique logs** no Railway
2. **Teste localmente** primeiro
3. **Confirme credenciais** de todos os serviços
4. **Use Opção 1** para isolar problemas
5. **Verifique estrutura** das tabelas Supabase
