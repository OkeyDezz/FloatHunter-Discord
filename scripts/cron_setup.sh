#!/bin/bash

# Script para configurar cron scheduler no Railway
# Executar uma vez para configurar o restart automático

# Configurações
BOT_DIR="/app"
CRON_FILE="/tmp/crontab"
SCRIPT_PATH="$BOT_DIR/scripts/restart_bot.sh"

# Torna o script executável
chmod +x "$SCRIPT_PATH"

# Cria entrada no cron para executar a cada hora
echo "0 * * * * $SCRIPT_PATH" > "$CRON_FILE"

# Adiciona ao crontab do usuário
crontab "$CRON_FILE"

# Verifica se foi adicionado
if crontab -l | grep -q "restart_bot.sh"; then
    echo "✅ Cron scheduler configurado com sucesso!"
    echo "📅 Bot será verificado e reiniciado a cada hora se necessário"
    echo "📝 Logs em: $BOT_DIR/restart_bot.log"
else
    echo "❌ Falha ao configurar cron scheduler"
    exit 1
fi

# Limpa arquivo temporário
rm -f "$CRON_FILE"

echo "🚀 Configuração concluída!"

