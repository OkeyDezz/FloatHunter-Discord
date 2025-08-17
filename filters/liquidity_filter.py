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
            # Calcula score de liquidez
            liquidity_score = await self.calculate_liquidity_score(item)
            
            if liquidity_score is None:
                # Se não conseguir calcular, aceita o item (fallback)
                logger.debug(f"Item {item.get('name')} aceito por fallback (liquidez não calculável)")
                return True
            
            # Verifica se atende ao score mínimo
            return liquidity_score >= self.min_liquidity_score
            
        except Exception as e:
            logger.error(f"Erro ao verificar filtro de liquidez: {e}")
            return False
    
    async def calculate_liquidity_score(self, item: Dict) -> Optional[float]:
        """
        Calcula o score de liquidez do item baseado em dados históricos.
        
        Args:
            item: Dicionário com dados do item
            
        Returns:
            float: Score de liquidez entre 0.0 e 1.0
        """
        try:
            market_hash_name = item.get('market_hash_name')
            
            if not market_hash_name:
                logger.debug("Market hash name não encontrado para cálculo de liquidez")
                return None
            
            # Obtém dados de liquidez do Supabase
            liquidity_data = await self.supabase.get_liquidity_data(market_hash_name)
            
            if not liquidity_data:
                logger.debug(f"Sem dados de liquidez para {market_hash_name}")
                return None
            
            # Calcula score baseado em múltiplos fatores
            score = 0.0
            
            # Score baseado no liquidity_score da database
            if 'liquidity_score' in liquidity_data:
                db_score = liquidity_data['liquidity_score']
                if db_score is not None:
                    score += db_score * 0.6  # 60% do peso
            
            # Score baseado no volume 24h
            if 'volume_24h' in liquidity_data:
                volume = liquidity_data['volume_24h']
                if volume is not None and volume > 0:
                    # Normaliza volume (assumindo que >100 é bom)
                    volume_score = min(1.0, volume / 100.0)
                    score += volume_score * 0.3  # 30% do peso
            
            # Score baseado no tempo médio de venda
            if 'avg_sale_time' in liquidity_data:
                avg_time = liquidity_data['avg_sale_time']
                if avg_time is not None and avg_time > 0:
                    # Normaliza tempo (assumindo que <24h é bom)
                    time_score = max(0.0, 1.0 - (avg_time / 24.0))
                    score += time_score * 0.1  # 10% do peso
            
            # Garante que o score esteja entre 0.0 e 1.0
            final_score = max(0.0, min(1.0, score))
            
            logger.debug(f"Score de liquidez calculado: {final_score:.3f} para {item.get('name')}")
            return final_score
            
        except Exception as e:
            logger.error(f"Erro ao calcular score de liquidez: {e}")
            return None
    
    def get_min_liquidity_score(self) -> float:
        """Retorna o score mínimo de liquidez configurado."""
        return self.min_liquidity_score
    
    def set_min_liquidity_score(self, score: float):
        """Define o score mínimo de liquidez."""
        self.min_liquidity_score = max(0.0, min(1.0, score))
        logger.info(f"Score mínimo de liquidez atualizado para {self.min_liquidity_score}")
