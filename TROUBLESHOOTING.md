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
COIN_TO_USD_FACTOR=0.614
```

#### 2. Verificar Estrutura das Tabelas Supabase

O bot usa as tabelas existentes **SEM ALTERÁ-LAS**:

**Tabela `market_data`:**
```sql
-- Estrutura existente (NÃO ALTERAR)
item_key TEXT PRIMARY KEY,
display_name TEXT,
name_base TEXT,
stattrak BOOLEAN,
souvenir BOOLEAN,
condition TEXT,
fetched_at TIMESTAMP,
price_buff163 DECIMAL(10,2)  -- Preço em dólar
```

**Tabela `liquidity`:**
```sql
-- Estrutura existente (NÃO ALTERAR)
item_key TEXT PRIMARY KEY,
liquidity_score DECIMAL(3,2)  -- Score de 0.0 a 1.0
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
- Tabelas `market_data` e `liquidity` existem?

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
echo "COIN_TO_USD_FACTOR: $COIN_TO_USD_FACTOR"
```

### Passo 2: Testar Conexão Supabase
```bash
# Teste se consegue conectar ao Supabase
curl -H "apikey: $SUPABASE_ANON_KEY" \
     -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
     "$SUPABASE_URL/rest/v1/market_data?select=count&limit=1"

# Teste tabela liquidity
curl -H "apikey: $SUPABASE_ANON_KEY" \
     -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
     "$SUPABASE_URL/rest/v1/liquidity?select=count&limit=1"
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
- Tabelas `market_data` e `liquidity` existem?
- Colunas estão com nomes corretos?
- Permissões de leitura estão configuradas?

## 📞 Suporte

Se os problemas persistirem:

1. **Verifique os logs** no Railway
2. **Teste localmente** primeiro
3. **Verifique as credenciais** de todos os serviços
4. **Confirme a estrutura** das tabelas existentes

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
- [ ] Tabela `liquidity` existe no Supabase
- [ ] Bot do Discord criado e convidado
- [ ] API key do CSGOEmpire válida
- [ ] Health check responde corretamente
- [ ] Logs não mostram erros críticos

## 🔧 Como o Bot Funciona Agora (Simplificado)

### 1. Cálculo de Lucro (Simples)
- **Preço CSGOEmpire**: Converte de coin para dólar usando fator 0.614
- **Preço Buff163**: Obtém diretamente da tabela `market_data`
- **Cálculo**: `((preço_buff163 - preço_csgoempire_usd) / preço_csgoempire_usd) * 100`

### 2. Cálculo de Liquidez (Direto)
- **Usa diretamente**: `liquidity_score` da tabela `liquidity`
- **Sem cálculos complexos**: Apenas compara com o mínimo configurado

### 3. Busca de Dados
- **Tabela `market_data`**: Apenas `price_buff163` (preço em dólar)
- **Tabela `liquidity`**: Apenas `liquidity_score`
- **Relacionamento**: Via `item_key`

### 4. Exemplo de Funcionamento
```
Item detectado no CSGOEmpire: 1000 coin
Conversão para USD: 1000 * 0.614 = $614.00
Preço Buff163: $650.00
Lucro calculado: ((650 - 614) / 614) * 100 = 5.86%
Score liquidez: 0.8 (da tabela)
Resultado: Passa nos filtros se MIN_PROFIT_PERCENTAGE < 5.86% e MIN_LIQUIDITY_SCORE < 0.8
```
