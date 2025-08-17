# 🆘 Solução de Problemas - Railway

## ❌ Erro: "Service Unavailable"

### Causas Comuns

1. **Falha na inicialização do bot**
2. **Problemas de conexão com Supabase**
3. **Configuração incorreta das variáveis de ambiente**
4. **Timeout no health check**

### Soluções

#### 1. Verificar Variáveis de Ambiente

Certifique-se de que TODAS estas variáveis estão configuradas no Railway:

```env
# OBRIGATÓRIAS
CSGOEMPIRE_API_KEY=sua_api_key_aqui
DISCORD_TOKEN=seu_token_aqui
CSGOEMPIRE_CHANNEL_ID=123456789
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua_chave_anonima_aqui

# OPCIONAIS (mas recomendadas)
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role_aqui
MIN_PROFIT_PERCENTAGE=5.0
MIN_LIQUIDITY_SCORE=0.7
MIN_PRICE=1.0
MAX_PRICE=1000.0
```

#### 2. Verificar Tabela Supabase

O bot precisa da tabela `market_data` com estas colunas:

```sql
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    market_hash_name TEXT NOT NULL,
    price_buff163 DECIMAL(10,2),
    price_csgoempire DECIMAL(10,2),
    price_csfloat DECIMAL(10,2),
    price_whitemarket DECIMAL(10,2),
    liquidity_score DECIMAL(3,2),
    volume_24h INTEGER,
    avg_sale_time INTEGER,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 3. Verificar Logs do Railway

1. Acesse o projeto no Railway
2. Clique na aba "Deployments"
3. Clique no deployment mais recente
4. Verifique os logs para erros específicos

#### 4. Testar Conexão Supabase

Verifique se consegue acessar o Supabase:
- URL está correta?
- Chave anônima está válida?
- Tabela `market_data` existe?

#### 5. Reiniciar o Projeto

1. No Railway, vá para "Settings"
2. Clique em "Restart Project"
3. Aguarde o novo deploy

## 🔍 Debug Passo a Passo

### Passo 1: Verificar Configuração
```bash
# No Railway, verifique se todas as variáveis estão definidas
echo "Verificando variáveis..."
echo "CSGOEMPIRE_API_KEY: $CSGOEMPIRE_API_KEY"
echo "DISCORD_TOKEN: $DISCORD_TOKEN"
echo "SUPABASE_URL: $SUPABASE_URL"
```

### Passo 2: Testar Conexão Supabase
```bash
# Teste se consegue conectar ao Supabase
curl -H "apikey: $SUPABASE_ANON_KEY" \
     -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
     "$SUPABASE_URL/rest/v1/market_data?select=count&limit=1"
```

### Passo 3: Verificar Health Check
```bash
# Teste o endpoint de health check
curl "https://seu-projeto.railway.app/health"
```

## 🚨 Problemas Específicos

### Bot Não Conecta ao Discord
- Token do Discord está correto?
- Bot foi convidado para o servidor?
- Permissões estão configuradas?

### Falha na Conexão CSGOEmpire
- API key está válida?
- Rate limit não foi excedido?
- Servidor do CSGOEmpire está online?

### Erro de Database
- Tabela `market_data` existe?
- Colunas estão com nomes corretos?
- Permissões de leitura estão configuradas?

## 📞 Suporte

Se os problemas persistirem:

1. **Verifique os logs** no Railway
2. **Teste localmente** primeiro
3. **Verifique as credenciais** de todos os serviços
4. **Confirme a estrutura** da tabela Supabase

## 🔄 Deploy de Teste

Para testar localmente antes do Railway:

```bash
# 1. Configure o .env
cp env.example .env
# Edite o .env com suas credenciais

# 2. Instale dependências
pip install -r requirements.txt

# 3. Execute o bot
python3 main.py
```

## ✅ Checklist de Verificação

- [ ] Todas as variáveis de ambiente configuradas
- [ ] Tabela `market_data` existe no Supabase
- [ ] Bot do Discord criado e convidado
- [ ] API key do CSGOEmpire válida
- [ ] Health check responde corretamente
- [ ] Logs não mostram erros críticos
