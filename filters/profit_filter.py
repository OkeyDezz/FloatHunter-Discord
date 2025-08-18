"""
Filtro de lucro para o Opportunity Bot.
"""

import logging
from typing import Dict, Optional
from utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class ProfitFilter:
    """Filtro para verificar se um item tem potencial de lucro."""
    
    def __init__(self, min_profit_percentage: float = 5.0, coin_to_usd_factor: float = 0.614):
        self.min_profit_percentage = min_profit_percentage
        self.supabase = SupabaseClient()
        # Fator de conversão de coin para dólar
        self.coin_to_usd_factor = coin_to_usd_factor
    
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
        Calcula o potencial de lucro comparando preço CSGOEmpire vs Buff163.
        
        Args:
            item: Dicionário com dados do item
            
        Returns:
            float: Percentual de lucro potencial ou None se não puder calcular
        """
        try:
            market_hash_name = item.get('market_hash_name')
            price_csgoempire_usd = item.get('price')  # Já vem convertido em USD
            
            if not market_hash_name or price_csgoempire_usd is None:
                logger.debug("Dados insuficientes para calcular lucro")
                return None
            
            # O preço já vem convertido em USD do marketplace_scanner
            # Não precisa mais converter de coin para dólar
            
            # Obtém preço do Buff163 em dólar
            price_buff163_usd = await self.supabase.get_buff163_price(market_hash_name)
            
            if not price_buff163_usd:
                logger.debug(f"Sem preço Buff163 para {market_hash_name}")
                return None
            
            # Calcula percentual de lucro
            profit_percentage = ((price_buff163_usd - price_csgoempire_usd) / price_csgoempire_usd) * 100
            
            logger.debug(f"Lucro calculado: {profit_percentage:.2f}% para {item.get('name')}")
            logger.debug(f"Preço CSGOEmpire: ${price_csgoempire_usd:.2f}")
            logger.debug(f"Preço Buff163: ${price_buff163_usd:.2f}")
            
            return profit_percentage
            
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
    
    def get_coin_to_usd_factor(self) -> float:
        """Retorna o fator de conversão de coin para dólar."""
        return self.coin_to_usd_factor
    
    def set_coin_to_usd_factor(self, factor: float):
        """Define o fator de conversão de coin para dólar."""
        self.coin_to_usd_factor = factor
        logger.info(f"Fator de conversão coin->USD atualizado para {self.coin_to_usd_factor}")
