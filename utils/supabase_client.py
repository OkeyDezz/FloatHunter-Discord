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
    
    async def get_buff163_price(self, market_hash_name: str) -> Optional[float]:
        """
        Obtém apenas o preço do Buff163 para um item.
        
        Args:
            market_hash_name: Market hash name do item (usado como item_key)
            
        Returns:
            float: Preço do Buff163 em dólar ou None se não encontrado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return None
            
            logger.info(f"🔍 Buscando preço Buff163 para: '{market_hash_name}'")
            logger.info(f"🔍 Query: SELECT price_buff163 FROM market_data WHERE item_key = '{market_hash_name}'")
            
            # Busca apenas o preço do Buff163 na tabela market_data
            response = self.client.table('market_data').select(
                'price_buff163'
            ).eq('item_key', market_hash_name).execute()
            
            logger.info(f"📊 Resposta da database: {response.data}")
            logger.info(f"📊 Número de registros encontrados: {len(response.data) if response.data else 0}")
            
            if not response.data:
                logger.warning(f"⚠️ Nenhum registro encontrado para item_key: '{market_hash_name}'")
                return None
            
            price_buff163 = response.data[0].get('price_buff163')
            logger.info(f"📊 Campo price_buff163 extraído: {price_buff163}")
            
            if price_buff163 is not None:
                logger.info(f"✅ Preço Buff163 encontrado: ${price_buff163}")
                return float(price_buff163)
            
            logger.warning(f"⚠️ Campo price_buff163 é None para '{market_hash_name}'")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar preço Buff163: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def get_liquidity_score(self, market_hash_name: str) -> Optional[float]:
        """
        Obtém apenas o score de liquidez para um item.
        
        Args:
            market_hash_name: Market hash name do item (usado como item_key)
            
        Returns:
            float: Score de liquidez (0.0 a 100.0) ou None se não encontrado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return None
            
            logger.info(f"🔍 Buscando score de liquidez para: '{market_hash_name}'")
            logger.info(f"🔍 Query: SELECT liquidity_score FROM liquidity WHERE item_key = '{market_hash_name}'")
            
            # Busca apenas o liquidity_score na tabela liquidity
            response = self.client.table('liquidity').select(
                'liquidity_score'
            ).eq('item_key', market_hash_name).execute()
            
            logger.info(f"📊 Resposta da database: {response.data}")
            logger.info(f"📊 Número de registros encontrados: {len(response.data) if response.data else 0}")
            
            if not response.data:
                logger.warning(f"⚠️ Nenhum registro encontrado para item_key: '{market_hash_name}'")
                return None
            
            liquidity_score = response.data[0].get('liquidity_score')
            logger.info(f"📊 Campo liquidity_score extraído: {liquidity_score}")
            
            if liquidity_score is not None:
                logger.info(f"✅ Score de liquidez encontrado: {liquidity_score}")
                return float(liquidity_score)
            
            logger.warning(f"⚠️ Campo liquidity_score é None para '{market_hash_name}'")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar score de liquidez: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
    
    def is_connected(self) -> bool:
        """Verifica se o cliente está conectado."""
        return self.client is not None
    
    async def test_connection(self) -> bool:
        """Testa a conexão com o Supabase."""
        try:
            if not self.client:
                return False
            
            logger.info("🔍 Testando conexão com Supabase...")
            
            # Testa tabela market_data
            try:
                response = self.client.table('market_data').select('item_key, price_buff163').limit(1).execute()
                logger.info(f"✅ Tabela market_data acessível: {len(response.data)} registros encontrados")
                if response.data:
                    sample_item = response.data[0]
                    logger.info(f"📊 Exemplo de item: item_key='{sample_item.get('item_key')}', price_buff163={sample_item.get('price_buff163')}")
            except Exception as e:
                logger.error(f"❌ Erro ao acessar tabela market_data: {e}")
                return False
            
            # Testa tabela liquidity
            try:
                response = self.client.table('liquidity').select('item_key, liquidity_score').limit(1).execute()
                logger.info(f"✅ Tabela liquidity acessível: {len(response.data)} registros encontrados")
                if response.data:
                    sample_item = response.data[0]
                    logger.info(f"📊 Exemplo de item: item_key='{sample_item.get('item_key')}', liquidity_score={sample_item.get('liquidity_score')}")
            except Exception as e:
                logger.error(f"❌ Erro ao acessar tabela liquidity: {e}")
                return False
            
            logger.info("✅ Conexão com Supabase testada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Teste de conexão falhou: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
