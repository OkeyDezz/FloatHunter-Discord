"""
Filtro de lucro para o Opportunity Bot.
"""

import logging
from typing import Dict, Optional
from utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class ProfitFilter:
    """Filtro para verificar se um item tem potencial de lucro."""
    
    def __init__(self, min_profit_percentage: float = 5.0):
        self.min_profit_percentage = min_profit_percentage
        self.supabase = SupabaseClient()
    
    async def check(self, item: Dict) -> bool:
        """
        Verifica se o item atende aos critérios de lucro.
        
        Args:
            item: Dicionário com dados do item
            
        Returns:
            bool: True se o item atende aos critérios
        """
        try:
            # Calcula potencial de lucro
            profit_potential = await self.calculate_profit_potential(item)
            
            if profit_potential is None:
                # Se não conseguir calcular, aceita o item (fallback)
                logger.debug(f"Item {item.get('name')} aceito por fallback (lucro não calculável)")
                return True
            
            # Verifica se atende ao percentual mínimo
            return profit_potential >= self.min_profit_percentage
            
        except Exception as e:
            logger.error(f"Erro ao verificar filtro de lucro: {e}")
            return False
    
    async def calculate_profit_potential(self, item: Dict) -> Optional[float]:
        """
        Calcula o potencial de lucro do item comparando com o preço do Buff163.
        
        Args:
            item: Dicionário com dados do item
            
        Returns:
            float: Percentual de lucro potencial ou None se não puder calcular
        """
        try:
            market_hash_name = item.get('market_hash_name')
            current_price = item.get('price')
            
            if not market_hash_name or not current_price:
                logger.debug("Dados insuficientes para calcular lucro")
                return None
            
            # Obtém preços de referência do Supabase (especialmente Buff163)
            reference_prices = await self.supabase.get_reference_prices(market_hash_name)
            
            if not reference_prices:
                logger.debug(f"Sem preços de referência para {market_hash_name}")
                return None
            
            # Prioriza o preço do Buff163 como referência principal
            buff163_price = reference_prices.get('buff163')
            
            if buff163_price:
                # Calcula lucro baseado no preço do Buff163
                profit_percentage = ((buff163_price - current_price) / current_price) * 100
                logger.debug(f"Lucro calculado vs Buff163: {profit_percentage:.2f}% para {item.get('name')}")
                logger.debug(f"Preço atual: ${current_price}, Preço Buff163: ${buff163_price}")
                return profit_percentage
            
            # Fallback: usa o menor preço disponível se Buff163 não estiver disponível
            if len(reference_prices) > 0:
                best_reference_price = min(reference_prices.values())
                profit_percentage = ((best_reference_price - current_price) / current_price) * 100
                logger.debug(f"Lucro calculado vs melhor preço disponível: {profit_percentage:.2f}% para {item.get('name')}")
                return profit_percentage
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular potencial de lucro: {e}")
            return None
    
    def get_min_profit_percentage(self) -> float:
        """Retorna o percentual mínimo de lucro configurado."""
        return self.min_profit_percentage
    
    def set_min_profit_percentage(self, percentage: float):
        """Define o percentual mínimo de lucro."""
        self.min_profit_percentage = max(0.0, percentage)
        logger.info(f"Percentual mínimo de lucro atualizado para {self.min_profit_percentage}%")
