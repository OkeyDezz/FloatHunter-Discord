#!/bin/bash

# Script de restart automático do Opportunity Bot
# Para ser usado com cron scheduler: 0 * * * * /path/to/opportunity-bot/scripts/restart_bot.sh

# Configurações
BOT_DIR="/app"  # Diretório do bot no Railway
LOG_FILE="$BOT_DIR/restart_bot.log"
PID_FILE="$BOT_DIR/bot.pid"

# Log da execução
echo "$(date): Executando restart automático do Opportunity Bot" >> "$LOG_FILE"

# Verifica se o bot está rodando
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "$(date): Bot está rodando (PID: $PID), verificando saúde..." >> "$LOG_FILE"
        
        # Verifica se o bot está respondendo (health check)
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo "$(date): Bot está saudável, não é necessário restart" >> "$LOG_FILE"
            exit 0
        else
            echo "$(date): Bot não está respondendo ao health check, forçando restart..." >> "$LOG_FILE"
            kill -TERM $PID
            sleep 10
            
            # Se ainda estiver rodando, força kill
            if ps -p $PID > /dev/null 2>&1; then
                echo "$(date): Forçando kill do processo..." >> "$LOG_FILE"
                kill -KILL $PID
                sleep 5
            fi
        fi
    else
        echo "$(date): PID file existe mas processo não está rodando, removendo PID file..." >> "$LOG_FILE"
        rm -f "$PID_FILE"
    fi
else
    echo "$(date): PID file não encontrado, bot pode não estar rodando" >> "$LOG_FILE"
fi

# Aguarda um pouco antes de reiniciar
sleep 5

# Reinicia o bot
echo "$(date): Reiniciando Opportunity Bot..." >> "$LOG_FILE"
cd "$BOT_DIR"

# Inicia o bot em background
nohup python main.py > bot.log 2>&1 &
NEW_PID=$!

# Salva o novo PID
echo $NEW_PID > "$PID_FILE"

# Verifica se iniciou com sucesso
sleep 10
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "$(date): Bot reiniciado com sucesso (PID: $NEW_PID)" >> "$LOG_FILE"
    
    # Aguarda health check
    sleep 30
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "$(date): Bot está respondendo ao health check após restart" >> "$LOG_FILE"
    else
        echo "$(date): AVISO: Bot não está respondendo ao health check após restart" >> "$LOG_FILE"
    fi
else
    echo "$(date): ERRO: Falha ao reiniciar bot" >> "$LOG_FILE"
    exit 1
fi

echo "$(date): Restart automático concluído" >> "$LOG_FILE"

