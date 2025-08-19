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
        """Verifica se um item tem potencial de lucro."""
        try:
            profit_percentage = await self.calculate_profit_potential(item)
            
            if profit_percentage is None:
                # Se não conseguir calcular lucro, REJEITA o item
                logger.debug(f"Item {item.get('name')} REJEITADO - lucro não pode ser calculado")
                return False
            
            result = profit_percentage >= self.min_profit_percentage
            
            if result:
                logger.info(f"✅ Item {item.get('name')} ACEITO - lucro {profit_percentage:.2f}% >= {self.min_profit_percentage}%")
            else:
                logger.info(f"❌ Item {item.get('name')} REJEITADO - lucro {profit_percentage:.2f}% < {self.min_profit_percentage}%")
                # Durante debug, aceita itens com lucro negativo para verificar se o bot está funcionando
                if profit_percentage < 0:
                    logger.info(f"🔍 DEBUG: Aceitando item com lucro negativo para verificar funcionamento")
                    return True
            
            logger.debug(f"Lucro: {profit_percentage:.2f}% >= {self.min_profit_percentage}% = {result} para {item.get('name')}")
            
            return result
            
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
            price_csgoempire_usd = item.get('price')  # Já vem convertido em USD
            price_buff163_usd = item.get('price_buff163')  # Já obtido pelo marketplace_scanner
            
            if price_csgoempire_usd is None:
                logger.debug("Preço CSGOEmpire não disponível")
                return None
            
            if price_buff163_usd is None:
                logger.debug(f"Preço Buff163 não disponível para {item.get('name')}")
                return None
            
            # O preço já vem convertido em USD do marketplace_scanner
            # Não precisa mais converter de coin para dólar
            
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
