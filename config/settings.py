"""
Configurações do Opportunity Bot.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

class Settings:
    """Configurações do Opportunity Bot."""
    
    # Configurações do CSGOEmpire
    CSGOEMPIRE_API_KEY: Optional[str] = os.getenv('CSGOEMPIRE_API_KEY')
    
    # Configurações do Discord
    DISCORD_TOKEN: Optional[str] = os.getenv('DISCORD_TOKEN')
    CSGOEMPIRE_CHANNEL_ID: Optional[int] = int(os.getenv('CSGOEMPIRE_CHANNEL_ID', '0'))
    
    # Configurações de filtros
    MIN_PROFIT_PERCENTAGE: float = float(os.getenv('MIN_PROFIT_PERCENTAGE', '5.0'))
    MIN_LIQUIDITY_SCORE: float = float(os.getenv('MIN_LIQUIDITY_SCORE', '0.7'))
    MIN_PRICE: float = float(os.getenv('MIN_PRICE', '1.0'))
    MAX_PRICE: float = float(os.getenv('MAX_PRICE', '1000.0'))
    
    # Configurações de scan
    SCAN_INTERVAL_SECONDS: int = int(os.getenv('SCAN_INTERVAL_SECONDS', '30'))
    WEBSOCKET_RECONNECT_DELAY: int = int(os.getenv('WEBSOCKET_RECONNECT_DELAY', '5'))
    
    # Configurações de logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_TO_FILE: bool = os.getenv('LOG_TO_FILE', 'false').lower() == 'true'
    
    @classmethod
    def validate(cls) -> bool:
        """Valida se as configurações obrigatórias estão presentes."""
        required_configs = [
            ('CSGOEMPIRE_API_KEY', cls.CSGOEMPIRE_API_KEY),
            ('DISCORD_TOKEN', cls.DISCORD_TOKEN),
            ('CSGOEMPIRE_CHANNEL_ID', cls.CSGOEMPIRE_CHANNEL_ID),
        ]
        
        missing_configs = []
        for name, value in required_configs:
            if not value:
                missing_configs.append(name)
        
        if missing_configs:
            print(f"❌ Configurações obrigatórias ausentes: {', '.join(missing_configs)}")
            return False
        
        return True
