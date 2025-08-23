#!/bin/bash

# Script de deploy para o Opportunity Bot
# Uso: ./deploy.sh

set -e

echo "🚀 Iniciando deploy do Opportunity Bot..."

# Verifica se o git está configurado
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Erro: Este diretório não é um repositório git"
    exit 1
fi

# Verifica se há mudanças não commitadas
if [[ -n $(git status --porcelain) ]]; then
    echo "⚠️  Há mudanças não commitadas. Deseja continuar? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ Deploy cancelado"
        exit 1
    fi
fi

# Verifica se o arquivo .env existe
if [[ ! -f .env ]]; then
    echo "⚠️  Arquivo .env não encontrado. Copiando de env.example..."
    cp env.example .env
    echo "📝 Edite o arquivo .env com suas configurações antes de continuar"
    echo "❌ Deploy cancelado - configure o .env primeiro"
    exit 1
fi

# Verifica se as variáveis obrigatórias estão configuradas
echo "🔍 Verificando configurações..."

source .env

required_vars=(
    "CSGOEMPIRE_API_KEY"
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

# Verifica se pelo menos uma opção do Discord está configurada
if [[ -z "$DISCORD_WEBHOOK_URL" && -z "$DISCORD_TOKEN" ]]; then
    missing_vars+=("DISCORD_WEBHOOK_URL ou DISCORD_TOKEN")
fi

if [[ -z "$DISCORD_TOKEN" && -z "$CSGOEMPIRE_CHANNEL_ID" ]]; then
    missing_vars+=("CSGOEMPIRE_CHANNEL_ID (se usar DISCORD_TOKEN)")
fi

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "❌ Variáveis obrigatórias não configuradas:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    echo "📝 Configure estas variáveis no arquivo .env"
    exit 1
fi

echo "✅ Todas as variáveis obrigatórias estão configuradas"

# Executa testes
echo "🧪 Executando testes..."
if ! python test_bot.py; then
    echo "❌ Testes falharam. Corrija os problemas antes do deploy"
    exit 1
fi

echo "✅ Testes passaram com sucesso"

# Commit das mudanças
echo "📝 Fazendo commit das mudanças..."
git add .
git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S')" || true

# Push para o repositório
echo "📤 Fazendo push para o repositório..."
git push origin main

echo "✅ Deploy concluído com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo "1. Verifique se o Railway detectou o push"
echo "2. Monitore os logs em Railway > Deployments > View Logs"
echo "3. Verifique o health check em Railway > Settings > Domains"
echo ""
echo "🔍 Para verificar se está funcionando:"
echo "   - Procure por '✅ Scanner conectado, aguardando oportunidades...' nos logs"
echo "   - Verifique se recebe eventos 'new_item'"
echo "   - Confirme se as oportunidades são enviadas para o Discord"
echo ""
echo "❓ Se houver problemas, execute: python test_bot.py"
