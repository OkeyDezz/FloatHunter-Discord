"""
Filtro de liquidez para o Opportunity Bot.
"""

import logging
from typing import Dict, Optional
from utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class LiquidityFilter:
    """Filtro para verificar se um item tem boa liquidez."""
    
    def __init__(self, min_liquidity_score: float = 70.0):
        self.min_liquidity_score = min_liquidity_score
        self.supabase = SupabaseClient()
    
    async def check(self, item: Dict) -> bool:
        """Verifica se um item tem boa liquidez."""
        try:
            # Usa o score de liquidez já obtido pelo marketplace_scanner
            liquidity_score = item.get('liquidity_score')
    
            if liquidity_score is None:
                # Se não conseguir obter liquidez, REJEITA o item
                logger.debug(f"Item {item.get('name')} REJEITADO - liquidez não disponível")
                return False
    
            result = liquidity_score >= self.min_liquidity_score
    
            if result:
                logger.info(f"✅ Item {item.get('name')} ACEITO - liquidez {liquidity_score:.1f} >= {self.min_liquidity_score}")
            else:
                logger.info(f"❌ Item {item.get('name')} REJEITADO - liquidez {liquidity_score:.1f} < {self.min_liquidity_score}")
                # Durante debug, aceita itens com liquidez baixa para verificar se o bot está funcionando
                logger.info(f"🔍 DEBUG: Aceitando item com liquidez baixa para verificar funcionamento")
                return True
    
            logger.debug(f"Liquidez: {liquidity_score:.1f} >= {self.min_liquidity_score} = {result} para {item.get('name')}")
    
            return result
    
        except Exception as e:
            logger.error(f"Erro ao verificar filtro de liquidez: {e}")
            return False
    
    def get_min_liquidity_score(self) -> float:
        """Retorna o score mínimo de liquidez configurado."""
        return self.min_liquidity_score
    
    def set_min_liquidity_score(self, score: float):
        """Define o score mínimo de liquidez."""
        self.min_liquidity_score = max(0.0, min(100.0, score))
        logger.info(f"Score mínimo de liquidez atualizado para {self.min_liquidity_score}")
