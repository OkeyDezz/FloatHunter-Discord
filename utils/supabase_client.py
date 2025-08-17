"""
Cliente Supabase para o Opportunity Bot.
"""

import logging
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from config.settings import Settings

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Cliente para acesso ao Supabase."""
    
    def __init__(self):
        self.settings = Settings()
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa o cliente Supabase."""
        try:
            if not self.settings.SUPABASE_URL or not self.settings.SUPABASE_KEY:
                logger.error("❌ Configurações do Supabase não encontradas")
                return
            
            self.client = create_client(
                self.settings.SUPABASE_URL,
                self.settings.SUPABASE_KEY
            )
            logger.info("✅ Cliente Supabase inicializado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar cliente Supabase: {e}")
    
    async def get_reference_prices(self, market_hash_name: str) -> Optional[Dict[str, float]]:
        """
        Obtém preços de referência para um item da tabela market_data.
        
        Args:
            market_hash_name: Market hash name do item
            
        Returns:
            Dict com preços de referência ou None se não encontrado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return None
            
            # Busca preços de referência na tabela market_data
            response = self.client.table('market_data').select(
                'price_buff163, price_csgoempire, price_csfloat, price_whitemarket'
            ).eq('market_hash_name', market_hash_name).execute()
            
            if not response.data:
                logger.debug(f"Sem dados de market_data para {market_hash_name}")
                return None
            
            # Organiza preços por marketplace
            prices = {}
            item_data = response.data[0]
            
            # Adiciona preços disponíveis
            if item_data.get('price_buff163'):
                prices['buff163'] = float(item_data['price_buff163'])
            
            if item_data.get('price_csgoempire'):
                prices['csgoempire'] = float(item_data['price_csgoempire'])
            
            if item_data.get('price_csfloat'):
                prices['csfloat'] = float(item_data['price_csfloat'])
            
            if item_data.get('price_whitemarket'):
                prices['whitemarket'] = float(item_data['price_whitemarket'])
            
            logger.debug(f"Preços encontrados para {market_hash_name}: {prices}")
            return prices if prices else None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar preços de referência: {e}")
            return None
    
    async def get_liquidity_data(self, market_hash_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados de liquidez para um item da tabela market_data.
        
        Args:
            market_hash_name: Market hash name do item
            
        Returns:
            Dict com dados de liquidez ou None se não encontrado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return None
            
            # Busca dados de liquidez da tabela market_data
            response = self.client.table('market_data').select(
                'liquidity_score, volume_24h, avg_sale_time, updated_at'
            ).eq('market_hash_name', market_hash_name).execute()
            
            if not response.data:
                logger.debug(f"Sem dados de liquidez para {market_hash_name}")
                return None
            
            item = response.data[0]
            return {
                'liquidity_score': item.get('liquidity_score', 0.0),
                'volume_24h': item.get('volume_24h', 0),
                'avg_sale_time': item.get('avg_sale_time', 0),
                'updated_at': item.get('updated_at')
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar dados de liquidez: {e}")
            return None
    
    async def log_opportunity(self, item: Dict, marketplace: str, profit_potential: float):
        """
        Registra uma oportunidade encontrada na database.
        
        Args:
            item: Dados do item
            marketplace: Nome do marketplace
            profit_potential: Potencial de lucro estimado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return
            
            opportunity_data = {
                'market_hash_name': item.get('market_hash_name'),
                'name': item.get('name'),
                'price': item.get('price'),
                'marketplace': marketplace,
                'profit_potential': profit_potential,
                'detected_at': 'now()',
                'status': 'detected'
            }
            
            # Insere na tabela de oportunidades (se existir)
            try:
                response = self.client.table('opportunities').insert(opportunity_data).execute()
                if response.data:
                    logger.info(f"✅ Oportunidade registrada na database: {item.get('name')}")
                else:
                    logger.warning("⚠️ Falha ao registrar oportunidade na database")
            except Exception as e:
                logger.warning(f"⚠️ Tabela opportunities não encontrada, pulando log: {e}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao registrar oportunidade: {e}")
    
    async def get_marketplace_stats(self, marketplace: str) -> Optional[Dict[str, Any]]:
        """
        Obtém estatísticas de um marketplace da tabela market_data.
        
        Args:
            marketplace: Nome do marketplace
            
        Returns:
            Dict com estatísticas ou None se não encontrado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return None
            
            # Busca estatísticas do marketplace na tabela market_data
            price_column = f"price_{marketplace}"
            
            response = self.client.table('market_data').select(
                f'count, avg({price_column}), min({price_column}), max({price_column})'
            ).not_.is_(price_column, 'null').execute()
            
            if not response.data:
                return None
            
            stats = response.data[0]
            return {
                'total_items': stats.get('count', 0),
                'avg_price': stats.get('avg', 0.0),
                'min_price': stats.get('min', 0.0),
                'max_price': stats.get('max', 0.0)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar estatísticas: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Verifica se o cliente está conectado."""
        return self.client is not None
    
    async def test_connection(self) -> bool:
        """Testa a conexão com o Supabase."""
        try:
            if not self.client:
                return False
            
            # Tenta fazer uma query simples
            response = self.client.table('market_data').select('count').limit(1).execute()
            return True
            
        except Exception as e:
            logger.error(f"❌ Teste de conexão falhou: {e}")
            return False
