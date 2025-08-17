# Opportunity Bot

Bot de detecção de oportunidades 24/7 para marketplaces de CS:GO.

## Funcionalidades

- 🔍 Monitoramento em tempo real via WebSocket
- 🎯 Filtros configuráveis de lucro e liquidez
- 📱 Notificações automáticas no Discord
- 🚀 Operação independente do bot principal
- ⚡ Baixo consumo de recursos

## Estrutura

```
opportunity-bot/
├── main.py                 # Bot principal
├── config/
│   └── settings.py         # Configurações
├── core/
│   ├── marketplace_scanner.py  # Scanner WebSocket
│   └── discord_poster.py      # Postagem Discord
├── filters/
│   ├── profit_filter.py       # Filtro de lucro
│   └── liquidity_filter.py    # Filtro de liquidez
└── requirements.txt
```

## Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na pasta do bot:

```env
# CSGOEmpire
CSGOEMPIRE_API_KEY=sua_api_key_aqui

# Discord
DISCORD_TOKEN=seu_token_aqui
CSGOEMPIRE_CHANNEL_ID=123456789

# Filtros
MIN_PROFIT_PERCENTAGE=5.0
MIN_LIQUIDITY_SCORE=0.7
MIN_PRICE=1.0
MAX_PRICE=1000.0

# Configurações
SCAN_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
```

### Como Obter as Credenciais

1. **CSGOEmpire API Key**: Acesse https://csgoempire.com/api
2. **Discord Token**: Crie um bot em https://discord.com/developers/applications
3. **Channel ID**: ID do canal onde as oportunidades serão postadas

## Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Configure as variáveis de ambiente

3. Execute o bot:
```bash
python main.py
```

## Como Funciona

1. **Conexão WebSocket**: Conecta ao CSGOEmpire via WebSocket
2. **Monitoramento**: Escuta eventos de novos itens e atualizações
3. **Filtros**: Aplica filtros de lucro e liquidez
4. **Notificação**: Envia oportunidades encontradas para o Discord
5. **Reconexão**: Reconecta automaticamente em caso de desconexão

## Filtros

### Filtro de Lucro
- Atualmente aceita todos os itens
- Futuramente implementará comparação com outros marketplaces

### Filtro de Liquidez
- Atualmente aceita todos os itens
- Futuramente implementará análise de volume e tempo de venda

## Logs

O bot gera logs detalhados incluindo:
- Status de conexão
- Oportunidades encontradas
- Erros e reconexões
- Estatísticas de operação

## Monitoramento

O bot inclui:
- Health checks automáticos
- Reconexão automática
- Logs estruturados
- Tratamento de erros robusto

## Próximas Funcionalidades

- [ ] Integração com CSFloat
- [ ] Integração com WhiteMarket
- [ ] Filtros avançados de lucro
- [ ] Análise de liquidez baseada em dados históricos
- [ ] Dashboard web para configuração
- [ ] Múltiplos canais do Discord por marketplace

## Suporte

Para suporte, consulte a documentação principal do bot ou entre em contato com a equipe de desenvolvimento.
