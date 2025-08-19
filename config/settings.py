"""
Configurações simples para o Opportunity Bot.
"""
import os
from typing import Optional

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
        required_settings = [
            ('CSGOEMPIRE_API_KEY', self.CSGOEMPIRE_API_KEY),
            ('DISCORD_WEBHOOK_URL', self.DISCORD_WEBHOOK_URL),
            ('SUPABASE_URL', self.SUPABASE_URL),
            ('SUPABASE_KEY', self.SUPABASE_KEY)
        ]
        
        missing_settings = [name for name, value in required_settings if not value]
        
        if missing_settings:
            raise ValueError(f"Configurações obrigatórias ausentes: {', '.join(missing_settings)}")
    
    def __str__(self) -> str:
        """Representação string das configurações."""
        return f"""Settings:
  - Preço: ${self.MIN_PRICE:.2f} - ${self.MAX_PRICE:.2f}
  - Lucro mínimo: {self.MIN_PROFIT_PERCENTAGE:.1f}%
  - Liquidez mínima: {self.MIN_LIQUIDITY_SCORE:.1f}
  - Fator conversão: {self.COIN_TO_USD_FACTOR}
  - WebSocket: {self.WEBSOCKET_MAX_RECONNECT_ATTEMPTS} tentativas
  - Log: {self.LOG_LEVEL}"""
