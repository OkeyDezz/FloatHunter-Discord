# 🚀 Deploy no Railway - Opportunity Bot

## ✅ Problemas Resolvidos

1. **Erro de Build do aiohttp**: Resolvido usando Python 3.11 e versões estáveis
2. **Variáveis do Supabase**: Adicionadas todas as configurações necessárias
3. **Health Check**: Implementado servidor de health check para o Railway

## 🔧 Configuração no Railway

### Passo 1: Conectar Repositório

1. Acesse [Railway.app](https://railway.app)
2. Faça login com sua conta GitHub
3. Clique em "New Project"
4. Selecione "Deploy from GitHub repo"
5. Escolha: `OkeyDezz/FloatHunter-Discord`

### Passo 2: Configurar Variáveis de Ambiente

No Railway, adicione estas variáveis:

```env
# CSGOEmpire
CSGOEMPIRE_API_KEY=sua_api_key_aqui

# Discord
DISCORD_TOKEN=seu_token_do_bot_aqui
CSGOEMPIRE_CHANNEL_ID=123456789

# Supabase (OBRIGATÓRIO)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua_chave_anonima_aqui
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role_aqui

# Filtros
MIN_PROFIT_PERCENTAGE=5.0
MIN_LIQUIDITY_SCORE=0.7
MIN_PRICE=1.0
MAX_PRICE=1000.0

# Configurações
SCAN_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
```

### Passo 3: Deploy

1. O Railway detectará automaticamente os arquivos de configuração
2. Clique em "Deploy"
3. Aguarde o build (deve funcionar agora!)

## 📊 Monitoramento

### Health Check
- **URL**: `https://seu-projeto.railway.app/health`
- **Status**: Retorna `{"status": "healthy"}` se funcionando

### Logs
- Acesse a aba "Deployments" no Railway
- Clique no deployment mais recente
- Verifique os logs para debug

## 🆘 Solução de Problemas

### Build Falha
- Verifique se todas as variáveis de ambiente estão configuradas
- Confirme se o repositório está sincronizado

### Bot Não Conecta
- Verifique se o token do Discord está correto
- Confirme se o bot foi convidado para o servidor

### Erro de Database
- Verifique as credenciais do Supabase
- Confirme se as tabelas existem na database

## 🔄 Atualizações

Para atualizar o bot:
1. Faça alterações no código
2. Commit e push para o GitHub
3. O Railway fará deploy automático

## 📈 Recursos Utilizados

- **RAM**: ~200-400MB
- **CPU**: <5%
- **Storage**: <1GB
- **Network**: Baixo

## 🎯 Próximos Passos

1. ✅ Deploy no Railway
2. ✅ Configurar Discord
3. ✅ Testar funcionalidade
4. ✅ Monitorar performance
5. ✅ Expandir para outros marketplaces
