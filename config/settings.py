"""
Configurações simples para o Opportunity Bot.
"""
import os
from typing import Optional
from pathlib import Path

# Tenta carregar variáveis do arquivo .env se estiver disponível
try:
    from dotenv import load_dotenv
    # Procura .env no diretório atual e nos pais
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Arquivo .env carregado: {env_path}")
    else:
        # Tenta carregar do diretório atual
        load_dotenv()
        print("✅ Tentativa de carregar .env do diretório atual")
except ImportError:
    print("⚠️ python-dotenv não disponível, usando apenas variáveis de ambiente do sistema")

class Settings:
    """Configurações do bot carregadas de variáveis de ambiente."""
    
    def __init__(self):
        # Configurações do CSGOEmpire
        self.CSGOEMPIRE_API_KEY: str = os.getenv('CSGOEMPIRE_API_KEY', '')
        
        # Configurações do Discord
        self.DISCORD_WEBHOOK_URL: str = os.getenv('DISCORD_WEBHOOK_URL', '')
        self.DISCORD_BOT_TOKEN: Optional[str] = os.getenv('DISCORD_BOT_TOKEN')
        self.DISCORD_CHANNEL_ID: Optional[str] = os.getenv('DISCORD_CHANNEL_ID')
        
        # Configurações do Supabase
        self.SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
        self.SUPABASE_KEY: str = os.getenv('SUPABASE_KEY', '')
        
        # Filtros de preço (USD)
        self.MIN_PRICE: float = float(os.getenv('MIN_PRICE', '1.0'))
        self.MAX_PRICE: float = float(os.getenv('MAX_PRICE', '100.0'))
        
        # Filtros de oportunidade
        self.MIN_PROFIT_PERCENTAGE: float = float(os.getenv('MIN_PROFIT_PERCENTAGE', '5.0'))
        self.MIN_LIQUIDITY_SCORE: float = float(os.getenv('MIN_LIQUIDITY_SCORE', '30.0'))
        
        # Fator de conversão centavos para dólar (CSGOEmpire)
        self.COIN_TO_USD_FACTOR: float = float(os.getenv('COIN_TO_USD_FACTOR', '0.614'))
        
        # Configurações do WebSocket
        self.WEBSOCKET_RECONNECT_DELAY: int = int(os.getenv('WEBSOCKET_RECONNECT_DELAY', '5'))
        self.WEBSOCKET_MAX_RECONNECT_ATTEMPTS: int = int(os.getenv('WEBSOCKET_MAX_RECONNECT_ATTEMPTS', '10'))
        
        # Configurações de logging
        self.LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
        
        # Validações básicas
        self._validate_settings()
    
    def _validate_settings(self):
        """Valida se as configurações essenciais estão presentes."""
        # Log das variáveis encontradas para debug
        print(f"🔍 Debug - Variáveis de ambiente:")
        print(f"  CSGOEMPIRE_API_KEY: {'✅ Definida' if self.CSGOEMPIRE_API_KEY else '❌ Ausente'}")
        print(f"  DISCORD_WEBHOOK_URL: {'✅ Definida' if self.DISCORD_WEBHOOK_URL else '❌ Ausente'}")
        print(f"  SUPABASE_URL: {'✅ Definida' if self.SUPABASE_URL else '❌ Ausente'}")
        print(f"  SUPABASE_KEY: {'✅ Definida' if self.SUPABASE_KEY else '❌ Ausente'}")
        
        required_settings = [
            ('CSGOEMPIRE_API_KEY', self.CSGOEMPIRE_API_KEY),
            ('DISCORD_WEBHOOK_URL', self.DISCORD_WEBHOOK_URL),
            ('SUPABASE_URL', self.SUPABASE_URL),
            ('SUPABASE_KEY', self.SUPABASE_KEY)
        ]
        
        missing_settings = [name for name, value in required_settings if not value]
        
        if missing_settings:
            print(f"❌ Configurações obrigatórias ausentes: {', '.join(missing_settings)}")
            print(f"💡 Certifique-se de que as variáveis estão definidas no Railway ou no arquivo .env")
            print(f"🔍 Listando TODAS as variáveis de ambiente disponíveis:")
            
            # Lista todas as variáveis de ambiente para debug
            env_vars = dict(os.environ)
            for key, value in sorted(env_vars.items()):
                # Mascara valores sensíveis
                if any(sensitive in key.lower() for sensitive in ['key', 'token', 'secret', 'password']):
                    masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                    print(f"    {key}: {masked_value}")
                else:
                    print(f"    {key}: {value}")
            
            # Para debugging no Railway, vamos permitir execução com warning
            print(f"⚠️ MODO DEBUG: Continuando execução mesmo sem todas as variáveis")
            print(f"⚠️ Bot pode não funcionar corretamente!")
            return
            
            # Descomente a linha abaixo para parar execução (produção)
            # raise ValueError(f"Configurações obrigatórias ausentes: {', '.join(missing_settings)}")
        
        print(f"✅ Todas as configurações obrigatórias estão presentes")
    
    def __str__(self) -> str:
        """Representação string das configurações."""
        return f"""Settings:
  - Preço: ${self.MIN_PRICE:.2f} - ${self.MAX_PRICE:.2f}
  - Lucro mínimo: {self.MIN_PROFIT_PERCENTAGE:.1f}%
  - Liquidez mínima: {self.MIN_LIQUIDITY_SCORE:.1f}
  - Fator conversão: {self.COIN_TO_USD_FACTOR}
  - WebSocket: {self.WEBSOCKET_MAX_RECONNECT_ATTEMPTS} tentativas
  - Log: {self.LOG_LEVEL}"""
