"""
Scanner de marketplace para o Opportunity Bot.
"""

import asyncio
import logging
import socketio
import aiohttp
from typing import Dict, Optional, Callable
from datetime import datetime
from config.settings import Settings
from filters.profit_filter import ProfitFilter
from filters.liquidity_filter import LiquidityFilter
from utils.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class MarketplaceScanner:
    """Scanner de marketplace usando WebSocket."""
    
    def __init__(self):
        self.settings = Settings()
        self.sio = socketio.AsyncClient()
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Filtros
        self.profit_filter = ProfitFilter(
            self.settings.MIN_PROFIT_PERCENTAGE, 
            self.settings.COIN_TO_USD_FACTOR
        )
        self.liquidity_filter = LiquidityFilter(self.settings.MIN_LIQUIDITY_SCORE)
        
        # Supabase client
        self.supabase = SupabaseClient()
        
        # Callback para oportunidades encontradas
        self.opportunity_callback: Optional[Callable] = None
        
        # Dados de autenticação
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        
        # Setup dos eventos do WebSocket
        self._setup_socket_events()
    
    def _setup_socket_events(self):
        """Configura os handlers de eventos do Socket.IO."""
        
        @self.sio.event
        async def connect():
            """Evento de conexão."""
            logger.info("🔌 Conectado ao WebSocket do CSGOEmpire")
        
        @self.sio.event
        async def disconnect():
            """Evento de desconexão."""
            logger.info("🔌 Desconectado do WebSocket do CSGOEmpire")
            self.is_connected = False
        
        @self.sio.event
        async def connect_error(data):
            """Erro de conexão."""
            logger.error(f"❌ Erro de conexão WebSocket: {data}")
            self.is_connected = False
        
        @self.sio.event(namespace='/trade')
        async def connect():
            """Conectado ao namespace /trade."""
            logger.info("🔌 Conectado ao namespace /trade")
        
        @self.sio.event(namespace='/trade')
        async def disconnect():
            """Desconectado do namespace /trade."""
            logger.info("🔌 Desconectado do namespace /trade")
            self.is_connected = False
        
        @self.sio.event(namespace='/trade')
        async def authenticated(data):
            """Evento de autenticação bem-sucedida."""
            logger.info("✅ WebSocket autenticado com sucesso")
            self.authenticated = True
            self.is_connected = True
        
        @self.sio.event(namespace='/trade')
        async def new_item(data):
            """Novo item disponível."""
            await self._process_item(data, 'new_item')
        
        @self.sio.event(namespace='/trade')
        async def updated_item(data):
            """Item atualizado."""
            await self._process_item(data, 'updated_item')
        
        @self.sio.event(namespace='/trade')
        async def removed_item(data):
            """Item removido."""
            await self._process_item(data, 'removed_item')
        
        @self.sio.event(namespace='/trade')
        async def timesync(data):
            """Sincronização de tempo."""
            logger.debug("⏰ Timesync recebido")
        
        @self.sio.event(namespace='/trade')
        async def error(data):
            """Erro do servidor."""
            logger.error(f"❌ Erro do servidor WebSocket: {data}")
    
    async def _identify_and_configure(self):
        """Identifica e configura filtros no WebSocket."""
        try:
            if not all([self.user_id, self.socket_token, self.socket_signature]):
                logger.error("❌ Dados de autenticação incompletos")
                return
            
            # Identificação
            await self.sio.emit('identify', {
                'uid': self.user_id,
                'authorizationToken': self.socket_token,
                'signature': self.socket_signature,
                'uuid': str(uuid.uuid4())
            })
            
            # Configura eventos permitidos
            await self.sio.emit('allowedEvents', {
                'events': ['new_item', 'updated_item', 'auction_update', 'auction_end', 'deleted_item']
            })
            
            # Configura filtros de preço
            await self.sio.emit('filters', {
                'price_min': self.settings.MIN_PRICE,
                'price_max': self.settings.MAX_PRICE
            })
            
            # Inscreve nos canais
            await self.sio.emit('subscribe', {'room': 'trading'})
            await self.sio.emit('subscribe', {'room': 'auctions'})
            
            logger.info("✅ WebSocket configurado e autenticado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar WebSocket: {e}")
    
    async def _handle_new_item(self, data: Dict):
        """Processa novo item."""
        try:
            logger.debug(f"Novo item: {data}")
            await self._process_item(data, "new_item")
        except Exception as e:
            logger.error(f"Erro ao processar novo item: {e}")
    
    async def _handle_updated_item(self, data: Dict):
        """Processa item atualizado."""
        try:
            logger.debug(f"Item atualizado: {data}")
            await self._process_item(data, "updated_item")
        except Exception as e:
            logger.error(f"Erro ao processar item atualizado: {e}")
    
    async def _handle_auction_update(self, data: Dict):
        """Processa atualização de leilão."""
        try:
            logger.debug(f"Atualização de leilão: {data}")
            await self._process_item(data, "auction_update")
        except Exception as e:
            logger.error(f"Erro ao processar atualização de leilão: {e}")
    
    async def _handle_auction_end(self, data: Dict):
        """Processa fim de leilão."""
        try:
            logger.debug(f"Fim de leilão: {data}")
            # Não processa fim de leilão como oportunidade
        except Exception as e:
            logger.error(f"Erro ao processar fim de leilão: {e}")
    
    async def _handle_deleted_item(self, data: Dict):
        """Processa item deletado."""
        try:
            logger.debug(f"Item deletado: {data}")
            # Não processa itens deletados como oportunidade
        except Exception as e:
            logger.error(f"Erro ao processar item deletado: {e}")
    
    async def _process_item(self, data: Dict, event_type: str):
        """Processa um item recebido do WebSocket."""
        try:
            item = self._extract_item_data(data)
            if not item:
                return
            
            # Verifica se passa nos filtros
            if await self._check_filters(item):
                logger.info(f"🎯 Oportunidade encontrada: {item.get('name', 'Unknown')}")
                if self.opportunity_callback:
                    await self.opportunity_callback(item, "csgoempire")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
    
    def _extract_item_data(self, data: Dict) -> Optional[Dict]:
        """Extrai dados relevantes do item."""
        try:
            # Estrutura de dados usada pelo bot principal
            item_data = data.get('data', data)
            
            # Campos obrigatórios
            item_id = item_data.get('id')
            name = item_data.get('name')
            market_hash_name = item_data.get('market_hash_name')
            price = item_data.get('price')
            
            if not all([item_id, name, market_hash_name, price]):
                logger.debug(f"Dados incompletos do item: {item_data}")
                return None
            
            # Dados adicionais
            condition = item_data.get('condition', 'Unknown')
            float_value = item_data.get('float_value')
            stattrak = item_data.get('stattrak', False)
            souvenir = item_data.get('souvenir', False)
            
            return {
                'id': item_id,
                'name': name,
                'market_hash_name': market_hash_name,
                'price': price,
                'condition': condition,
                'float_value': float_value,
                'stattrak': stattrak,
                'souvenir': souvenir,
                'marketplace': 'csgoempire',
                'detected_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados do item: {e}")
            return None
    
    async def _check_filters(self, item: Dict) -> bool:
        """Verifica se o item passa pelos filtros."""
        try:
            # Filtro de preço
            if 'price' in item:
                price = float(item['price'])
                if price < self.settings.MIN_PRICE or price > self.settings.MAX_PRICE:
                    return False
            
            # Filtro de lucro
            if not await self.profit_filter.check(item):
                return False
            
            # Filtro de liquidez
            if not await self.liquidity_filter.check(item):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar filtros: {e}")
            return False
    
    async def _connect_websocket(self) -> bool:
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            if not all([self.user_id, self.socket_token, self.socket_signature]):
                logger.error("❌ Dados de autenticação incompletos")
                return False
            
            # Configura handlers
            self._setup_socket_events()
            
            # Headers usados pelo bot principal
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Origin': 'https://trade.csgoempire.com',
                'Referer': 'https://trade.csgoempire.com/'
            }
            
            # Query string com uid e token (mesmo formato do bot principal)
            qs = f"uid={self.user_id}&token={self.socket_token}"
            
            # Conecta usando a mesma URL e namespace do bot principal
            await self.sio.connect(
                f"https://trade.csgoempire.com/?{qs}",
                socketio_path='s/',
                headers=headers,
                transports=['websocket'],
                namespaces=['/trade']
            )
            
            logger.info("🔌 WebSocket conectado ao namespace /trade")
            
            # Aguarda autenticação
            for _ in range(30):  # 30 segundos timeout
                if self.authenticated:
                    break
                await asyncio.sleep(1)
            
            if self.authenticated:
                logger.info("✅ WebSocket autenticado com sucesso")
                return True
            else:
                logger.error("❌ Timeout na autenticação do WebSocket")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            return False
    
    async def connect(self) -> bool:
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            # Testa conexão com Supabase primeiro
            logger.info("🔍 Testando conexão com Supabase...")
            if not await self.supabase.test_connection():
                logger.error("❌ Falha na conexão com Supabase")
                return False
            
            logger.info("✅ Conexão com Supabase OK")
            
            # Obtém metadata para autenticação
            if not await self._get_socket_metadata():
                return False
            
            # Conecta ao WebSocket
            return await self._connect_websocket()
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            return False
    
    async def _get_socket_metadata(self) -> bool:
        """Obtém metadata para autenticação do WebSocket (seguindo docs)."""
        try:
            if not self.settings.CSGOEMPIRE_API_KEY:
                logger.error("❌ API key do CSGOEmpire não configurada")
                return False
            
            # Endpoint correto usado pelo bot principal
            url = "https://csgoempire.com/api/v2/metadata/socket"
            headers = {
                "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Origin": "https://csgoempire.com",
                "Referer": "https://csgoempire.com/"
            }
            
            async with aiohttp.ClientSession() as session:
                # Tentativa principal com Authorization
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        js_data = data.get('data') or data
                        
                        self.user_id = js_data.get('user', {}).get('id')
                        self.socket_token = js_data.get('socket_token')
                        self.socket_signature = js_data.get('socket_signature') or js_data.get('token_signature')
                        self.user_model = js_data.get('user')
                        
                        if all([self.user_id, self.socket_token, self.socket_signature, self.user_model]):
                            logger.info("✅ Metadata obtida com sucesso")
                            return True
                        else:
                            logger.error("❌ Dados de autenticação incompletos na resposta principal")
                    else:
                        try:
                            txt = await response.text()
                        except Exception:
                            txt = ''
                        logger.error(f"❌ Erro ao obter metadata: {response.status} {txt[:200]}")
                
                # Fallback com token na querystring (alguns ambientes bloqueiam Authorization)
                logger.info("🔄 Tentando fallback com token na querystring...")
                async with session.get(
                    url,
                    params={"token": self.settings.CSGOEMPIRE_API_KEY},
                    headers={k: v for k, v in headers.items() if k != "Authorization"}
                ) as response2:
                    if response2.status == 200:
                        data2 = await response2.json()
                        js_data2 = data2.get('data') or data2
                        
                        self.user_id = js_data2.get('user', {}).get('id')
                        self.socket_token = js_data2.get('socket_token')
                        self.socket_signature = js_data2.get('socket_signature') or js_data2.get('token_signature')
                        self.user_model = js_data2.get('user')
                        
                        if all([self.user_id, self.socket_token, self.socket_signature, self.user_model]):
                            logger.info("✅ Metadata obtida com sucesso via fallback")
                            return True
                        else:
                            logger.error("❌ Dados de autenticação incompletos no fallback")
                    else:
                        try:
                            txt2 = await response2.text()
                        except Exception:
                            txt2 = ''
                        logger.error(f"❌ Erro ao obter metadata (fallback): {response2.status} {txt2[:200]}")
                
                return False
                    
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadata: {e}")
            return False
    
    def set_opportunity_callback(self, callback: Callable):
        """Define callback para oportunidades encontradas."""
        self.opportunity_callback = callback
    
    async def disconnect(self):
        """Desconecta do WebSocket."""
        try:
            if self.is_connected:
                await self.sio.disconnect()
                logger.info("WebSocket desconectado")
        except Exception as e:
            logger.error(f"Erro ao desconectar WebSocket: {e}")
    
    async def run_forever(self):
        """Executa o scanner indefinidamente."""
        while True:
            try:
                if not self.is_connected:
                    logger.info("🔄 Tentando conectar ao WebSocket...")
                    if await self.connect():
                        logger.info("✅ Conectado ao WebSocket")
                    else:
                        logger.error("❌ Falha ao conectar")
                        await asyncio.sleep(self.settings.WEBSOCKET_RECONNECT_DELAY)
                        continue
                
                # Mantém conexão ativa
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Erro no loop principal: {e}")
                await asyncio.sleep(self.settings.WEBSOCKET_RECONNECT_DELAY)
