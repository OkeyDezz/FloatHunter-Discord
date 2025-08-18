# 🔄 Sistema de Restart Automático - Opportunity Bot

## 📋 Visão Geral

O Opportunity Bot agora possui um **sistema robusto de reconexão** que resolve o problema de conexões perdidas após algumas horas de execução. O sistema implementa:

1. **Reconexão inteligente** com backoff exponencial
2. **Restart automático** após falhas consecutivas
3. **Fallback com cron scheduler** para restart a cada hora
4. **Monitoramento de saúde** da conexão WebSocket

## 🚀 Como Funciona

### **A. Sistema de Reconexão Inteligente**

#### **Backoff Exponencial**
```
Tentativa 1: Aguarda 1s
Tentativa 2: Aguarda 2s  
Tentativa 3: Aguarda 4s
Tentativa 4: Aguarda 8s
Tentativa 5: Aguarda 16s
...
Máximo: 5 minutos (300s)
```

#### **Critérios de Restart**
- **10 falhas consecutivas** → Restart forçado
- **1 hora sem conexão estável** → Restart forçado
- **5 minutos sem dados** → Inicia processo de reconexão

### **B. Fallback com Cron Scheduler**

#### **Verificação Automática**
- **A cada hora** (0 * * * *)
- **Verifica health check** do bot
- **Reinicia automaticamente** se necessário
- **Logs detalhados** de todas as operações

## 🔧 Configuração

### **A. Railway (Automático)**

O sistema de reconexão inteligente funciona **automaticamente** no Railway. Não é necessária configuração adicional.

### **B. Cron Scheduler (Opcional)**

Para ativar o fallback com cron scheduler:

#### **1. Conectar ao Railway via SSH**
```bash
railway login
railway shell
```

#### **2. Executar script de configuração**
```bash
cd /app
chmod +x scripts/cron_setup.sh
./scripts/cron_setup.sh
```

#### **3. Verificar configuração**
```bash
crontab -l
```

**Saída esperada:**
```
0 * * * * /app/scripts/restart_bot.sh
```

## 📊 Logs e Monitoramento

### **A. Logs de Reconexão**
```
⚠️ Sem dados recebidos há 300s
⚠️ Última conexão estável há 3600s
🚨 Forçando restart após 1.0h sem conexão estável
🚨 INICIANDO RESTART COMPLETO DO SCANNER
✅ Restart completo bem-sucedido!
```

### **B. Logs de Cron Scheduler**
```
Mon Aug 19 10:00:01 UTC 2025: Executando restart automático do Opportunity Bot
Mon Aug 19 10:00:01 UTC 2025: Bot está rodando (PID: 12345), verificando saúde...
Mon Aug 19 10:00:01 UTC 2025: Bot está saudável, não é necessário restart
Mon Aug 19 10:00:01 UTC 2025: Restart automático concluído
```

### **C. Arquivos de Log**
- **`bot.log`**: Log principal do bot
- **`restart_bot.log`**: Log dos restarts automáticos
- **`opportunity_bot.log`**: Log de oportunidades encontradas

## 🎯 Benefícios

### **A. Estabilidade**
- ✅ **Conexão 24/7** sem interrupções
- ✅ **Recuperação automática** de falhas
- ✅ **Sem perda de oportunidades** por desconexão

### **B. Performance**
- ✅ **Backoff inteligente** evita spam de reconexão
- ✅ **Restart seletivo** apenas quando necessário
- ✅ **Monitoramento contínuo** da saúde da conexão

### **C. Manutenção**
- ✅ **Zero intervenção manual** necessária
- ✅ **Logs detalhados** para troubleshooting
- ✅ **Fallback duplo** (reconexão + cron)

## 🔍 Troubleshooting

### **A. Verificar Status do Bot**
```bash
# Verificar se está rodando
ps aux | grep "python main.py"

# Verificar health check
curl http://localhost:8080/health

# Verificar logs
tail -f bot.log
tail -f restart_bot.log
```

### **B. Problemas Comuns**

#### **1. Bot não reconecta**
- Verificar logs de reconexão
- Verificar se API key ainda é válida
- Verificar se CSGOEmpire está funcionando

#### **2. Cron não executa**
- Verificar se cron está ativo: `service cron status`
- Verificar crontab: `crontab -l`
- Verificar permissões do script: `ls -la scripts/restart_bot.sh`

#### **3. Muitos restarts**
- Verificar configurações de timeout
- Verificar estabilidade da conexão
- Ajustar parâmetros de backoff se necessário

## ⚙️ Configurações Avançadas

### **A. Parâmetros de Reconexão**
```python
# Em marketplace_scanner.py
self._max_consecutive_failures = 10      # Máximo de falhas consecutivas
self._force_restart_after = 3600        # Força restart após 1 hora
self._max_reconnect_backoff = 300       # Delay máximo: 5 minutos
```

### **B. Timeouts de Health Check**
```python
# Em marketplace_scanner.py
if time_since_data > 300:  # 5 minutos sem dados
    await self._handle_connection_loss()
```

### **C. Intervalo do Cron**
```bash
# Em scripts/cron_setup.sh
# 0 * * * * = A cada hora
# */30 * * * * = A cada 30 minutos
# 0 */2 * * * = A cada 2 horas
```

## 🚀 Próximos Passos

1. **Deploy automático** no Railway
2. **Teste do sistema** de reconexão
3. **Configuração opcional** do cron scheduler
4. **Monitoramento** dos logs de reconexão
5. **Ajuste fino** dos parâmetros se necessário

## 📞 Suporte

Se encontrar problemas com o sistema de restart automático:

1. **Verificar logs** detalhados
2. **Verificar configurações** do Railway
3. **Testar health check** manualmente
4. **Verificar status** do cron scheduler
5. **Consultar documentação** do CSGOEmpire

---

**🎯 Resultado Esperado:** Bot rodando 24/7 com reconexão automática e zero perda de oportunidades! 🚀
