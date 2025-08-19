"""
Marketplace Scanner - Monitora CSGOEmpire via WebSocket.
Implementa exatamente a documentação oficial do CSGOEmpire.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Optional, Callable
import aiohttp
import socketio

logger = logging.getLogger(__name__)

class MarketplaceScanner:
    """Scanner para CSGOEmpire usando WebSocket oficial."""
    
    def __init__(self, settings, discord_poster=None, opportunity_callback=None):
        self.settings = settings
        self.discord_poster = discord_poster
        self.opportunity_callback = opportunity_callback
        
        # WebSocket
        self.sio = None
        self.is_connected = False
        self.user_data = None
        self.user_data_refreshed_at = None
        
        # Configurações
        self.domain = "csgoempire.com"
        self.socket_endpoint = f"wss://trade.{self.domain}/trade"
        
        # Headers para API
        self.api_headers = {
            'Authorization': f'Bearer {self.settings.CSGOEMPIRE_API_KEY}',
            'User-Agent': 'CSGOEmpire Opportunity Bot'
        }
        
        # Status
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    async def refresh_user_data(self):
        """Atualiza dados do usuário (válido por 30s)."""
        try:
            # Verifica se precisa atualizar (menos de 15s atrás)
            if (self.user_data_refreshed_at and 
                self.user_data_refreshed_at > time.time() - 15):
                logger.debug("✅ Dados do usuário ainda válidos")
                return True
            
            logger.info("🔄 Atualizando dados do usuário...")
            
            # Faz requisição para metadata/socket
            async with aiohttp.ClientSession() as session:
                url = f"https://{self.domain}/api/v2/metadata/socket"
                async with session.get(url, headers=self.api_headers) as response:
                    if response.status == 200:
                        self.user_data = await response.json()
                        self.user_data_refreshed_at = time.time()
                        logger.info(f"✅ Dados do usuário atualizados: {self.user_data.get('user', {}).get('name', 'Unknown')}")
                        return True
                    else:
                        logger.error(f"❌ Falha ao obter dados do usuário: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar dados do usuário: {e}")
            return False
    
    def _create_socket(self):
        """Cria conexão Socket.IO."""
        try:
            # Cria Socket.IO client
            self.sio = socketio.AsyncClient(
                transports=['websocket'],
                logger=True,
                engineio_logger=True
            )
            
            # Configura eventos
            self._setup_socket_events()
            
            logger.info("✅ Socket.IO client criado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar Socket.IO client: {e}")
            return False
    
    def _setup_socket_events(self):
        """Configura todos os eventos do Socket.IO."""
        
        @self.sio.event
        async def connect():
            """Evento de conexão."""
            logger.info("🔗 Conectado ao WebSocket CSGOEmpire")
            self.is_connected = True
            self.reconnect_attempts = 0
            
            # Aguarda um pouco antes de identificar
            await asyncio.sleep(1)
            
            # Emite evento de identificação
            if self.user_data:
                await self._emit_identify()
            else:
                logger.error("❌ Dados do usuário não disponíveis para identificação")
        
        @self.sio.event
        async def disconnect():
            """Evento de desconexão."""
            logger.warning("🔌 Desconectado do WebSocket CSGOEmpire")
            self.is_connected = False
        
        @self.sio.event
        async def connect_error(data):
            """Erro de conexão."""
            logger.error(f"❌ Erro de conexão: {data}")
            self.is_connected = False
        
        @self.sio.event
        async def init(data):
            """Evento de inicialização."""
            try:
                logger.info(f"🚀 Evento INIT recebido: {json.dumps(data, indent=2)}")
                
                if data and data.get('authenticated'):
                    logger.info(f"✅ Autenticado como: {data.get('name', 'Unknown')}")
                    
                    # Emite filtros para receber eventos
                    await self._emit_filters()
                    
                else:
                    logger.info("🔄 Não autenticado - emitindo identificação...")
                    await self._emit_identify()
                    
            except Exception as e:
                logger.error(f"❌ Erro no evento INIT: {e}")
        
        @self.sio.event
        async def timesync(data):
            """Sincronização de tempo."""
            logger.debug(f"⏰ Timesync: {data}")
        
        @self.sio.event
        async def new_item(data):
            """Novo item disponível."""
            try:
                logger.info(f"🆕 NOVO ITEM: {len(data) if isinstance(data, list) else 1} item(s)")
                
                if isinstance(data, list):
                    for item in data:
                        await self._process_item(item, "new_item")
                else:
                    await self._process_item(data, "new_item")
                    
            except Exception as e:
                logger.error(f"❌ Erro no evento new_item: {e}")
        
        @self.sio.event
        async def updated_item(data):
            """Item atualizado."""
            try:
                logger.info(f"🔄 ITEM ATUALIZADO: {len(data) if isinstance(data, list) else 1} item(s)")
                
                if isinstance(data, list):
                    for item in data:
                        await self._process_item(item, "updated_item")
                else:
                    await self._process_item(data, "updated_item")
                    
            except Exception as e:
                logger.error(f"❌ Erro no evento updated_item: {e}")
        
        @self.sio.event
        async def deleted_item(data):
            """Item deletado."""
            try:
                logger.info(f"🗑️ ITEM DELETADO: {len(data) if isinstance(data, list) else 1} item(s)")
                logger.debug(f"IDs deletados: {data}")
            except Exception as e:
                logger.error(f"❌ Erro no evento deleted_item: {e}")
        
        @self.sio.event
        async def auction_update(data):
            """Atualização de leilão."""
            try:
                logger.info(f"🏷️ LEILÃO ATUALIZADO: {len(data) if isinstance(data, list) else 1} item(s)")
                
                if isinstance(data, list):
                    for item in data:
                        logger.debug(f"Leilão: ID {item.get('id')} - Lance: {item.get('auction_highest_bid')}")
                else:
                    logger.debug(f"Leilão: ID {data.get('id')} - Lance: {data.get('auction_highest_bid')}")
                    
            except Exception as e:
                logger.error(f"❌ Erro no evento auction_update: {e}")
        
        @self.sio.event
        async def trade_status(data):
            """Status de trade."""
            try:
                logger.info(f"📦 TRADE STATUS: {data.get('type', 'unknown')}")
                logger.debug(f"Trade: {json.dumps(data, indent=2)}")
            except Exception as e:
                logger.error(f"❌ Erro no evento trade_status: {e}")
        
        @self.sio.event
        async def deposit_failed(data):
            """Depósito falhou."""
            try:
                logger.warning(f"❌ DEPÓSITO FALHOU: {data}")
            except Exception as e:
                logger.error(f"❌ Erro no evento deposit_failed: {e}")
    
    async def _emit_identify(self):
        """Emite evento de identificação."""
        try:
            if not self.user_data:
                logger.error("❌ Dados do usuário não disponíveis")
                return
            
            identify_data = {
                "uid": self.user_data['user']['id'],
                "model": self.user_data['user'],
                "authorizationToken": self.user_data['socket_token'],
                "signature": self.user_data['socket_signature'],
                "uuid": f"bot-{int(time.time())}"  # UUID simples para bot
            }
            
            logger.info(f"🆔 Emitindo identificação para UID: {identify_data['uid']}")
            await self.sio.emit('identify', identify_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao emitir identificação: {e}")
    
    async def _emit_filters(self):
        """Emite filtros para receber eventos."""
        try:
            filters = {
                "price_max": 9999999  # Filtro padrão da documentação
            }
            
            logger.info("🔍 Emitindo filtros para receber eventos")
            await self.sio.emit('filters', filters)
            
        except Exception as e:
            logger.error(f"❌ Erro ao emitir filtros: {e}")
    
    async def _process_item(self, item: Dict, event_type: str):
        """Processa um item recebido."""
        try:
            item_id = item.get('id')
            item_name = item.get('market_name', 'Unknown')
            item_price = item.get('purchase_price', 0)
            
            logger.info(f"📦 Processando item: {item_name} (ID: {item_id}) - Preço: {item_price}")
            
            # Converte preço de centavos para USD
            price_usd = item_price * self.settings.COIN_TO_USD_FACTOR
            
            # Verifica filtros de preço
            if price_usd < self.settings.MIN_PRICE or price_usd > self.settings.MAX_PRICE:
                logger.debug(f"❌ Item {item_name} fora do range de preço: ${price_usd:.2f}")
                return
            
            # Enriquece item com dados adicionais
            enriched_item = {
                'id': item_id,
                'name': item_name,
                'price': price_usd,
                'price_csgoempire_coin': item_price,
                'suggested_price': item.get('suggested_price', 0) * self.settings.COIN_TO_USD_FACTOR,
                'market_value': item.get('market_value', 0) * self.settings.COIN_TO_USD_FACTOR,
                'wear': item.get('wear'),
                'wear_name': item.get('wear_name'),
                'rarity': item.get('item_search', {}).get('rarity'),
                'type': item.get('item_search', {}).get('type'),
                'sub_type': item.get('item_search', {}).get('sub_type'),
                'stickers': item.get('stickers', []),
                'auction_ends_at': item.get('auction_ends_at'),
                'auction_highest_bid': item.get('auction_highest_bid'),
                'auction_number_of_bids': item.get('auction_number_of_bids'),
                'published_at': item.get('published_at'),
                'event_type': event_type
            }
            
            # Busca preço Buff163 e liquidez
            await self._enrich_with_database_data(enriched_item)
            
            # Verifica se é uma oportunidade
            if await self._is_opportunity(enriched_item):
                logger.info(f"🎯 OPORTUNIDADE ENCONTRADA: {item_name}")
                
                if self.opportunity_callback:
                    await self.opportunity_callback(enriched_item, "CSGOEmpire")
                else:
                    logger.warning("⚠️ Callback de oportunidade não configurado")
            else:
                logger.debug(f"ℹ️ Item {item_name} não é oportunidade")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
    
    async def _enrich_with_database_data(self, item: Dict):
        """Enriquece item com dados do banco."""
        try:
            from utils.supabase_client import SupabaseClient
            supabase = SupabaseClient()
            
            # Extrai informações do nome do item
            item_info = self._parse_item_name(item['name'])
            
            if item_info:
                # Busca preço Buff163
                price_buff163 = await supabase.get_buff163_price_advanced(
                    base_name=item_info['base_name'],
                    is_stattrak=item_info['is_stattrak'],
                    is_souvenir=item_info['is_souvenir'],
                    condition=item_info['condition']
                )
                
                if price_buff163:
                    item['price_buff163'] = price_buff163
                    logger.debug(f"✅ Preço Buff163: ${price_buff163:.2f}")
                
                # Busca liquidez
                liquidity_score = await supabase.get_liquidity_score_advanced(
                    base_name=item_info['base_name'],
                    is_stattrak=item_info['is_stattrak'],
                    is_souvenir=item_info['is_souvenir'],
                    condition=item_info['condition']
                )
                
                if liquidity_score is not None:
                    item['liquidity_score'] = liquidity_score
                    logger.debug(f"✅ Liquidez: {liquidity_score:.1f}")
                    
        except Exception as e:
            logger.error(f"❌ Erro ao enriquecer com dados do banco: {e}")
    
    def _parse_item_name(self, market_name: str) -> Optional[Dict]:
        """Extrai informações do nome do item."""
        try:
            # Exemplo: "AK-47 | Legion of Anubis (Field-Tested)"
            if ' | ' not in market_name:
                return None
            
            parts = market_name.split(' | ')
            base_name = parts[0].strip()
            
            # Verifica StatTrak
            is_stattrak = base_name.startswith('StatTrak™ ')
            if is_stattrak:
                base_name = base_name.replace('StatTrak™ ', '')
            
            # Verifica Souvenir
            is_souvenir = base_name.startswith('Souvenir ')
            if is_souvenir:
                base_name = base_name.replace('Souvenir ', '')
            
            # Extrai condição
            condition = None
            if len(parts) > 1:
                condition_part = parts[1].strip()
                if '(' in condition_part and ')' in condition_part:
                    condition = condition_part[condition_part.find('(')+1:condition_part.find(')')].strip()
            
            return {
                'base_name': base_name,
                'is_stattrak': is_stattrak,
                'is_souvenir': is_souvenir,
                'condition': condition
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse do nome: {e}")
            return None
    
    async def _is_opportunity(self, item: Dict) -> bool:
        """Verifica se um item é uma oportunidade."""
        try:
            # Verifica se tem preço Buff163
            if 'price_buff163' not in item:
                logger.debug(f"❌ Item {item['name']} sem preço Buff163")
                return False
            
            # Verifica se tem liquidez
            if 'liquidity_score' not in item:
                logger.debug(f"❌ Item {item['name']} sem liquidez")
                return False
            
            # Verifica liquidez mínima
            if item['liquidity_score'] < self.settings.MIN_LIQUIDITY_SCORE:
                logger.debug(f"❌ Item {item['name']} liquidez baixa: {item['liquidity_score']:.1f}")
                return False
            
            # Calcula lucro
            price_csgoempire = item['price']
            price_buff163 = item['price_buff163']
            
            if price_csgoempire <= 0 or price_buff163 <= 0:
                logger.debug(f"❌ Item {item['name']} preços inválidos")
                return False
            
            profit_percentage = ((price_buff163 - price_csgoempire) / price_csgoempire) * 100
            
            # Verifica lucro mínimo
            if profit_percentage < self.settings.MIN_PROFIT_PERCENTAGE:
                logger.debug(f"❌ Item {item['name']} lucro baixo: {profit_percentage:.2f}%")
                return False
            
            logger.info(f"✅ OPORTUNIDADE: {item['name']} - Lucro: {profit_percentage:.2f}% - Liquidez: {item['liquidity_score']:.1f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar oportunidade: {e}")
            return False
    
    async def start(self):
        """Inicia o scanner."""
        try:
            logger.info("🚀 Iniciando Marketplace Scanner...")
            
            # Atualiza dados do usuário
            if not await self.refresh_user_data():
                logger.error("❌ Falha ao obter dados do usuário")
                return False
            
            # Cria Socket.IO client
            if not self._create_socket():
                logger.error("❌ Falha ao criar Socket.IO client")
                return False
            
            # Conecta ao WebSocket
            try:
                logger.info(f"🔗 Conectando ao WebSocket: {self.socket_endpoint}")
                
                # Parâmetros de conexão
                query_params = {
                    'uid': self.user_data['user']['id'],
                    'token': self.user_data['socket_token']
                }
                
                # Headers extras
                extra_headers = {
                    'User-agent': f"{self.user_data['user']['id']} API Bot"
                }
                
                # Conecta
                await self.sio.connect(
                    self.socket_endpoint,
                    query=query_params,
                    headers=extra_headers,
                    wait_timeout=30
                )
                
                self.running = True
                logger.info("✅ Marketplace Scanner iniciado com sucesso")
                return True
                
            except Exception as e:
                logger.error(f"❌ Falha ao conectar ao WebSocket: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar scanner: {e}")
            return False
    
    async def stop(self):
        """Para o scanner."""
        try:
            logger.info("🛑 Parando Marketplace Scanner...")
            
            self.running = False
            
            if self.sio and self.is_connected:
                await self.sio.disconnect()
                logger.info("✅ Scanner parado")
            else:
                logger.info("ℹ️ Scanner já estava parado")
                
        except Exception as e:
            logger.error(f"❌ Erro ao parar scanner: {e}")
    
    async def is_connected(self) -> bool:
        """Verifica se está conectado."""
        return self.is_connected and self.sio and self.sio.connected
