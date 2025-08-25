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
            
            # Inicialização mais simples e compatível
            logger.info(f"🔧 Inicializando cliente Supabase...")
            logger.info(f"   URL: {self.settings.SUPABASE_URL}")
            logger.info(f"   Key: {self.settings.SUPABASE_KEY[:10]}...")
            
            # Tenta inicialização básica
            self.client = create_client(
                supabase_url=self.settings.SUPABASE_URL,
                supabase_key=self.settings.SUPABASE_KEY
            )
            
            logger.info("✅ Cliente Supabase inicializado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar cliente Supabase: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Tenta inicialização alternativa
            try:
                logger.info("🔄 Tentando inicialização alternativa...")
                self.client = create_client(
                    self.settings.SUPABASE_URL,
                    self.settings.SUPABASE_KEY
                )
                logger.info("✅ Cliente Supabase inicializado (método alternativo)")
            except Exception as e2:
                logger.error(f"❌ Falha na inicialização alternativa: {e2}")
                self.client = None
    
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
            
            # Primeira tentativa: busca exata
            response = self.client.table('market_data').select(
                'price_buff163'
            ).eq('item_key', market_hash_name).execute()
            
            logger.info(f"📊 Busca exata - Resposta: {response.data}")
            
            if response.data and len(response.data) > 0:
                price_buff163 = response.data[0].get('price_buff163')
                if price_buff163 is not None:
                    logger.info(f"✅ Preço Buff163 encontrado (busca exata): ${price_buff163}")
                    return float(price_buff163)
            
            # Segunda tentativa: busca por similaridade (contains)
            logger.info(f"🔍 Tentando busca por similaridade...")
            response = self.client.table('market_data').select(
                'item_key, price_buff163'
            ).ilike('item_key', f'%{market_hash_name}%').limit(5).execute()
            
            logger.info(f"📊 Busca por similaridade - Resposta: {response.data}")
            
            if response.data and len(response.data) > 0:
                # Mostra todos os itens similares encontrados
                for i, item in enumerate(response.data):
                    logger.info(f"📊 Item similar {i+1}: '{item.get('item_key')}' - Preço: ${item.get('price_buff163')}")
                
                # Tenta encontrar o mais similar
                for item in response.data:
                    item_key = item.get('item_key', '')
                    if market_hash_name.lower() in item_key.lower():
                        price_buff163 = item.get('price_buff163')
                        if price_buff163 is not None:
                            logger.info(f"✅ Preço Buff163 encontrado (similaridade): ${price_buff163}")
                            return float(price_buff163)
            
            logger.warning(f"⚠️ Nenhum preço Buff163 encontrado para: '{market_hash_name}'")
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
            
            # Primeira tentativa: busca exata
            response = self.client.table('liquidity').select(
                'liquidity_score'
            ).eq('item_key', market_hash_name).execute()
            
            logger.info(f"📊 Busca exata - Resposta: {response.data}")
            
            if response.data and len(response.data) > 0:
                liquidity_score = response.data[0].get('liquidity_score')
                if liquidity_score is not None:
                    logger.info(f"✅ Score de liquidez encontrado (busca exata): {liquidity_score}")
                    return float(liquidity_score)
            
            # Segunda tentativa: busca por similaridade (contains)
            logger.info(f"🔍 Tentando busca por similaridade...")
            response = self.client.table('liquidity').select(
                'item_key, liquidity_score'
            ).ilike('item_key', f'%{market_hash_name}%').limit(5).execute()
            
            logger.info(f"📊 Busca por similaridade - Resposta: {response.data}")
            
            if response.data and len(response.data) > 0:
                # Mostra todos os itens similares encontrados
                for i, item in enumerate(response.data):
                    logger.info(f"📊 Item similar {i+1}: '{item.get('item_key')}' - Liquidez: {item.get('liquidity_score')}")
                
                # Tenta encontrar o mais similar
                for item in response.data:
                    item_key = item.get('item_key', '')
                    if market_hash_name.lower() in item_key.lower():
                        liquidity_score = item.get('liquidity_score')
                        if liquidity_score is not None:
                            logger.info(f"✅ Score de liquidez encontrado (similaridade): {liquidity_score}")
                            return float(liquidity_score)
            
            logger.warning(f"⚠️ Nenhum score de liquidez encontrado para: '{market_hash_name}'")
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

    async def get_buff163_price_advanced(self, base_name: str, is_stattrak: bool, is_souvenir: bool, condition: str) -> Optional[float]:
        """
        Obtém o preço do Buff163 para um item usando a mesma lógica do bot principal.
        Consulta pelos campos name_base, stattrak, souvenir e condition separadamente.
        
        Args:
            base_name: Nome base do item
            is_stattrak: Se é StatTrak
            is_souvenir: Se é Souvenir
            condition: Condição do item
            
        Returns:
            float: Preço do Buff163 em dólar ou None se não encontrado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return None
            
            logger.info(f"🔍 Buscando preço Buff163 para: {base_name}")
            logger.info(f"   - StatTrak: {is_stattrak}")
            logger.info(f"   - Souvenir: {is_souvenir}")
            logger.info(f"   - Condição: {condition}")
            
            # Primeira tentativa: busca usando os campos separados (mesma lógica do bot principal)
            logger.info(f"🔍 Buscando por campos separados...")
            
            # Remove parênteses da condição se presente (para compatibilidade)
            clean_condition = condition
            if condition and condition.startswith('(') and condition.endswith(')'):
                clean_condition = condition[1:-1].strip()
            
            # Constrói a query usando os campos separados
            query = self.client.table('market_data').select('price_buff163')
            
            # Filtra por name_base
            query = query.eq('name_base', base_name)
            
            # Filtra por stattrak
            query = query.eq('stattrak', is_stattrak)
            
            # Filtra por souvenir
            query = query.eq('souvenir', is_souvenir)
            
            # Filtra por condition
            if clean_condition:
                query = query.eq('condition', clean_condition)
            
            response = query.execute()
            logger.info(f"📊 Busca por campos separados - Resposta: {response.data}")
            
            if response.data and len(response.data) > 0:
                price_buff163 = response.data[0].get('price_buff163')
                if price_buff163 is not None:
                    logger.info(f"✅ Preço Buff163 encontrado (campos separados): ${price_buff163}")
                    return float(price_buff163)
            
            # Segunda tentativa: busca usando item_key construído (formato antigo)
            market_data_name = self._build_market_data_name(base_name, is_stattrak, is_souvenir, condition)
            logger.info(f"🔍 Tentando busca por item_key: '{market_data_name}'")
            
            response = self.client.table('market_data').select('price_buff163').eq('item_key', market_data_name).execute()
            logger.info(f"📊 Busca por item_key - Resposta: {response.data}")
            
            if response.data and len(response.data) > 0:
                price_buff163 = response.data[0].get('price_buff163')
                if price_buff163 is not None:
                    logger.info(f"✅ Preço Buff163 encontrado (item_key): ${price_buff163}")
                    return float(price_buff163)
            
            # Terceira tentativa: busca por similaridade usando name_base
            logger.info(f"🔍 Tentando busca por similaridade...")
            response = self.client.table('market_data').select('item_key, price_buff163, name_base, stattrak, souvenir, condition').ilike('name_base', f'%{base_name}%').limit(10).execute()
            
            logger.info(f"📊 Busca por similaridade - Resposta: {response.data}")
            
            if response.data and len(response.data) > 0:
                # Mostra todos os itens similares encontrados
                logger.info(f"📊 Itens similares encontrados:")
                for i, item in enumerate(response.data):
                    logger.info(f"   {i+1}. '{item.get('item_key')}' - Preço: ${item.get('price_buff163')}")
                    logger.info(f"      name_base: {item.get('name_base')}, stattrak: {item.get('stattrak')}, souvenir: {item.get('souvenir')}, condition: {item.get('condition')}")
                
                # Tenta encontrar o mais similar
                for item in response.data:
                    item_name_base = item.get('name_base', '')
                    item_stattrak = item.get('stattrak', False)
                    item_souvenir = item.get('souvenir', False)
                    item_condition = item.get('condition', '')
                    
                    # Verifica se os campos correspondem
                    if (item_name_base == base_name and 
                        item_stattrak == is_stattrak and 
                        item_souvenir == is_souvenir and 
                        item_condition == clean_condition):
                        
                        price_buff163 = item.get('price_buff163')
                        if price_buff163 is not None:
                            logger.info(f"✅ Preço Buff163 encontrado por similaridade (campos exatos): ${price_buff163}")
                            return float(price_buff163)
                
                # Se não encontrou exato, aceita o primeiro com name_base igual
                for item in response.data:
                    if item.get('name_base') == base_name:
                        price_buff163 = item.get('price_buff163')
                        if price_buff163 is not None:
                            logger.info(f"✅ Preço Buff163 encontrado por fallback (name_base): ${price_buff163}")
                            return float(price_buff163)
            
            logger.warning(f"⚠️ Nenhum preço Buff163 encontrado para: {base_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar preço Buff163: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def get_liquidity_score_advanced(self, base_name: str, is_stattrak: bool, is_souvenir: bool, condition: str) -> Optional[float]:
        """
        Obtém o score de liquidez para um item usando o formato correto da tabela liquidity.
        
        Args:
            base_name: Nome base do item
            is_stattrak: Se é StatTrak
            is_souvenir: Se é Souvenir
            condition: Condição do item
            
        Returns:
            float: Score de liquidez (0.0 a 100.0) ou None se não encontrado
        """
        try:
            if not self.client:
                logger.error("❌ Cliente Supabase não inicializado")
                return None
            
            logger.info(f"🔍 Buscando score de liquidez para: {base_name}")
            logger.info(f"   - StatTrak: {is_stattrak}")
            logger.info(f"   - Souvenir: {is_souvenir}")
            logger.info(f"   - Condição: {condition}")
            
            # Constrói o nome no formato da tabela liquidity
            liquidity_name = self._build_liquidity_name(base_name, is_stattrak, is_souvenir, condition)
            logger.info(f"🔍 Nome para busca na tabela liquidity: '{liquidity_name}'")
            
            # Busca usando o nome construído
            response = self.client.table('liquidity').select('liquidity_score').eq('item_key', liquidity_name).execute()
            
            logger.info(f"📊 Resposta da database: {response.data}")
            logger.info(f"📊 Número de registros encontrados: {len(response.data) if response.data else 0}")
            
            if response.data and len(response.data) > 0:
                liquidity_score = response.data[0].get('liquidity_score')
                if liquidity_score is not None:
                    logger.info(f"✅ Score de liquidez encontrado: {liquidity_score}")
                    return float(liquidity_score)
            
            # Se não encontrou, tenta busca por similaridade
            logger.info(f"🔍 Tentando busca por similaridade...")
            response = self.client.table('liquidity').select('item_key, liquidity_score').ilike('item_key', f'%{base_name}%').limit(10).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"📊 Itens similares encontrados:")
                for i, item in enumerate(response.data):
                    logger.info(f"   {i+1}. '{item.get('item_key')}' - Liquidez: {item.get('liquidity_score')}")
                
                # Tenta encontrar o mais similar
                for item in response.data:
                    item_key = item.get('item_key', '')
                    if self._is_similar_item(item_key, base_name, is_stattrak, is_souvenir, condition):
                        liquidity_score = item.get('liquidity_score')
                        if liquidity_score is not None:
                            logger.info(f"✅ Score de liquidez encontrado por similaridade: {liquidity_score}")
                            return float(liquidity_score)
            
            logger.warning(f"⚠️ Nenhum score de liquidez encontrado para: {base_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar score de liquidez: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _build_liquidity_name(self, base_name: str, is_stattrak: bool, is_souvenir: bool, condition: str) -> str:
        """
        Constrói o nome no formato da tabela liquidity.
        
        Args:
            base_name: Nome base do item
            is_stattrak: Se é StatTrak
            is_souvenir: Se é Souvenir
            condition: Condição do item
            
        Returns:
            str: Nome no formato da tabela liquidity
        """
        try:
            # Remove "★" se presente no início
            if base_name.startswith('★'):
                base_name = base_name[1:].strip()
            
            # Se é Souvenir, adiciona no início (sem espaço após |)
            if is_souvenir:
                liquidity_name = f"Souvenir|{base_name}"
            else:
                liquidity_name = base_name
            
            # Se é StatTrak, adiciona antes da condição (sem espaço após |)
            if is_stattrak:
                if condition:
                    liquidity_name = f"{liquidity_name}|StatTrak|{condition}"
                else:
                    liquidity_name = f"{liquidity_name}|StatTrak"
            elif condition:
                liquidity_name = f"{liquidity_name}|{condition}"
            
            logger.info(f"🔧 Nome construído para liquidity: '{liquidity_name}'")
            return liquidity_name
            
        except Exception as e:
            logger.error(f"❌ Erro ao construir nome para liquidity: {e}")
            return base_name
    
    def _is_similar_item(self, item_key: str, base_name: str, is_stattrak: bool, is_souvenir: bool, condition: str) -> bool:
        """
        Verifica se um item da tabela liquidity é similar ao item buscado.
        
        Args:
            item_key: Nome do item na tabela liquidity
            base_name: Nome base do item
            is_stattrak: Se é StatTrak
            is_souvenir: Se é Souvenir
            condition: Condição do item
            
        Returns:
            bool: True se os itens são similares
        """
        try:
            # Remove "★" se presente
            if item_key.startswith('★'):
                item_key = item_key[1:].strip()
            
            # Verifica se contém o nome base
            if base_name.lower() not in item_key.lower():
                return False
            
            # Verifica StatTrak
            has_stattrak = "StatTrak" in item_key
            if is_stattrak != has_stattrak:
                return False
            
            # Verifica Souvenir
            has_souvenir = "Souvenir" in item_key
            if is_souvenir != has_souvenir:
                return False
            
            # Verifica condição (se especificada)
            if condition:
                if condition.lower() not in item_key.lower():
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar similaridade: {e}")
            return False

    def _build_market_data_name(self, base_name: str, is_stattrak: bool, is_souvenir: bool, condition: str) -> str:
        """
        Constrói o nome no formato da tabela market_data.
        
        Args:
            base_name: Nome base do item
            is_stattrak: Se é StatTrak
            is_souvenir: Se é Souvenir
            condition: Condição do item
            
        Returns:
            str: Nome no formato da tabela market_data
        """
        try:
            # Remove "★" se presente no início
            if base_name.startswith('★'):
                base_name = base_name[1:].strip()
            
            # Remove parênteses da condição se presente
            if condition and condition.startswith('(') and condition.endswith(')'):
                condition = condition[1:-1].strip()
            
            # Se é Souvenir, adiciona no início (sem espaço após |)
            if is_souvenir:
                market_data_name = f"Souvenir|{base_name}"
            else:
                market_data_name = base_name
            
            # Se é StatTrak, adiciona antes da condição (sem espaço após |)
            if is_stattrak:
                if condition:
                    market_data_name = f"{market_data_name}|StatTrak|{condition}"
                else:
                    market_data_name = f"{market_data_name}|StatTrak"
            elif condition:
                market_data_name = f"{market_data_name}|{condition}"
            
            logger.info(f"🔧 Nome construído para market_data: '{market_data_name}'")
            return market_data_name
            
        except Exception as e:
            logger.error(f"❌ Erro ao construir nome para market_data: {e}")
            return base_name
    
    def _is_similar_market_data_item(self, item_key: str, base_name: str, is_stattrak: bool, is_souvenir: bool, condition: str) -> bool:
        """
        Verifica se um item da tabela market_data é similar ao item buscado.
        
        Args:
            item_key: Nome do item na tabela market_data
            base_name: Nome base do item
            is_stattrak: Se é StatTrak
            is_souvenir: Se é Souvenir
            condition: Condição do item
            
        Returns:
            bool: True se os itens são similares
        """
        try:
            # Remove "★" se presente
            if item_key.startswith('★'):
                item_key = item_key[1:].strip()
            
            # Verifica se contém o nome base
            if base_name.lower() not in item_key.lower():
                return False
            
            # Verifica StatTrak
            has_stattrak = "StatTrak" in item_key
            if is_stattrak != has_stattrak:
                return False
            
            # Verifica Souvenir
            has_souvenir = "Souvenir" in item_key
            if is_souvenir != has_souvenir:
                return False
            
            # Verifica condição (se especificada)
            if condition:
                if condition.lower() not in item_key.lower():
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar similaridade: {e}")
            return False
