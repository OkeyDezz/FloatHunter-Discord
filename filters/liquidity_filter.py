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
        Calcula o score de liquidez do item baseado em dados das tabelas liquidity e market_data.
        
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
            
            # Score baseado no liquidity_score da tabela liquidity
            if 'liquidity_score' in liquidity_data:
                db_score = liquidity_data['liquidity_score']
                if db_score is not None:
                    score += db_score * 0.6  # 60% do peso
            
            # Score baseado na quantidade disponível no WhiteMarket
            if 'qty_whitemarket' in liquidity_data:
                qty_whitemarket = liquidity_data['qty_whitemarket']
                if qty_whitemarket is not None and qty_whitemarket > 0:
                    # Normaliza quantidade (assumindo que >5 é bom)
                    qty_score = min(1.0, qty_whitemarket / 5.0)
                    score += qty_score * 0.2  # 20% do peso
            
            # Score baseado na quantidade disponível no CSFloat
            if 'qty_csfloat' in liquidity_data:
                qty_csfloat = liquidity_data['qty_csfloat']
                if qty_csfloat is not None and qty_csfloat > 0:
                    # Normaliza quantidade (assumindo que >5 é bom)
                    qty_score = min(1.0, qty_csfloat / 5.0)
                    score += qty_score * 0.2  # 20% do peso
            
            # Garante que o score esteja entre 0.0 e 1.0
            final_score = max(0.0, min(1.0, score))
            
            logger.debug(f"Score de liquidez calculado: {final_score:.3f} para {item.get('name')}")
            logger.debug(f"Detalhes: DB={liquidity_data.get('liquidity_score', 0):.3f}, WM={liquidity_data.get('qty_whitemarket', 0)}, CS={liquidity_data.get('qty_csfloat', 0)}")
            
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
