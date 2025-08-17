#!/bin/bash

echo "🚀 Instalando Opportunity Bot..."

# Verifica se Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

# Verifica se pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 não encontrado. Instale pip primeiro."
    exit 1
fi

echo "✅ Python 3 e pip encontrados"

# Cria ambiente virtual
echo "🔧 Criando ambiente virtual..."
python3 -m venv venv

# Ativa ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Atualiza pip
echo "🔧 Atualizando pip..."
pip install --upgrade pip

# Instala dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Copia arquivo de exemplo
if [ ! -f .env ]; then
    echo "📝 Copiando arquivo de configuração..."
    cp env.example .env
    echo "⚠️  Configure o arquivo .env com suas credenciais antes de executar o bot"
else
    echo "✅ Arquivo .env já existe"
fi

echo ""
echo "🎉 Instalação concluída!"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure o arquivo .env com suas credenciais"
echo "2. Ative o ambiente virtual: source venv/bin/activate"
echo "3. Execute o bot: python3 main.py"
echo ""
echo "📚 Para mais informações, consulte o README.md"
