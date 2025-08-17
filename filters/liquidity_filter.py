"""
Filtro de liquidez para o Opportunity Bot.
"""

import logging
from typing import Dict, Optional
from utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class LiquidityFilter:
    """Filtro para verificar se um item tem boa liquidez."""
    
    def __init__(self, min_liquidity_score: float = 0.7):
        self.min_liquidity_score = min_liquidity_score
        self.supabase = SupabaseClient()
    
    async def check(self, item: Dict) -> bool:
        """
        Verifica se o item atende aos critérios de liquidez.
        
        Args:
            item: Dicionário com dados do item
            
        Returns:
            bool: True se o item atende aos critérios
        """
        try:
            # Obtém score de liquidez diretamente da tabela
            liquidity_score = await self.supabase.get_liquidity_score(item.get('market_hash_name'))
            
            if liquidity_score is None:
                # Se não conseguir obter, aceita o item (fallback)
                logger.debug(f"Item {item.get('name')} aceito por fallback (liquidez não disponível)")
                return True
            
            # Verifica se atende ao score mínimo
            result = liquidity_score >= self.min_liquidity_score
            
            logger.debug(f"Liquidez: {liquidity_score:.3f} >= {self.min_liquidity_score} = {result} para {item.get('name')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao verificar filtro de liquidez: {e}")
            return False
    
    def get_min_liquidity_score(self) -> float:
        """Retorna o score mínimo de liquidez configurado."""
        return self.min_liquidity_score
    
    def set_min_liquidity_score(self, score: float):
        """Define o score mínimo de liquidez."""
        self.min_liquidity_score = max(0.0, min(1.0, score))
        logger.info(f"Score mínimo de liquidez atualizado para {self.min_liquidity_score}")
