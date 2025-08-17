"""
Scanner de marketplace usando WebSocket para o Opportunity Bot.
"""

import asyncio
import logging
import json
import uuid
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
import socketio
import aiohttp

from config.settings import Settings
from filters.profit_filter import ProfitFilter
from filters.liquidity_filter import LiquidityFilter

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
        self.profit_filter = ProfitFilter(self.settings.MIN_PROFIT_PERCENTAGE)
        self.liquidity_filter = LiquidityFilter(self.settings.MIN_LIQUIDITY_SCORE)
        
        # Callback para oportunidades encontradas
        self.opportunity_callback: Optional[Callable] = None
        
        # Dados de autenticação
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        
        # Setup dos eventos do WebSocket
        self._setup_socket_events()
    
    def _setup_socket_events(self):
        """Configura os eventos do WebSocket."""
        
        @self.sio.event
        async def connect():
            logger.info("🔌 WebSocket conectado ao CSGOEmpire")
            self.is_connected = True
            self.reconnect_attempts = 0
            
            # Identifica e configura filtros
            await self._identify_and_configure()
        
        @self.sio.event
        async def disconnect():
            logger.info("🔌 WebSocket desconectado do CSGOEmpire")
            self.is_connected = False
        
        @self.sio.event
        async def new_item(data):
            """Novo item listado."""
            await self._handle_new_item(data)
        
        @self.sio.event
        async def updated_item(data):
            """Item atualizado."""
            await self._handle_updated_item(data)
        
        @self.sio.event
        async def auction_update(data):
            """Atualização de leilão."""
            await self._handle_auction_update(data)
        
        @self.sio.event
        async def auction_end(data):
            """Fim de leilão."""
            await self._handle_auction_end(data)
        
        @self.sio.event
        async def deleted_item(data):
            """Item deletado."""
            await self._handle_deleted_item(data)
    
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
        """Processa um item e verifica se é uma oportunidade."""
        try:
            # Extrai dados do item
            item = self._extract_item_data(data)
            if not item:
                return
            
            # Aplica filtros
            if self._check_filters(item):
                logger.info(f"🎯 Oportunidade encontrada: {item.get('name', 'Unknown')}")
                
                # Chama callback se configurado
                if self.opportunity_callback:
                    await self.opportunity_callback(item, "csgoempire")
            
        except Exception as e:
            logger.error(f"Erro ao processar item: {e}")
    
    def _extract_item_data(self, data: Dict) -> Optional[Dict]:
        """Extrai dados relevantes do item."""
        try:
            # Estrutura pode variar dependendo do evento
            if 'item' in data:
                item_data = data['item']
            else:
                item_data = data
            
            # Extrai campos básicos
            extracted = {
                'id': item_data.get('id'),
                'name': item_data.get('name'),
                'market_hash_name': item_data.get('market_hash_name'),
                'price': item_data.get('price'),
                'float_value': item_data.get('float_value'),
                'rarity': item_data.get('rarity'),
                'type': item_data.get('type'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Remove campos None
            extracted = {k: v for k, v in extracted.items() if v is not None}
            
            return extracted if extracted else None
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do item: {e}")
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
    
    async def connect(self) -> bool:
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            # Obtém metadata para autenticação
            if not await self._get_socket_metadata():
                return False
            
            # Conecta ao WebSocket
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://trade.csgoempire.com',
                'Referer': 'https://trade.csgoempire.com/'
            }
            
            qs = f"uid={self.user_id}&token={self.socket_token}"
            
            await self.sio.connect(
                f'https://trade.csgoempire.com/?{qs}',
                socketio_path='s/',
                headers=headers,
                transports=['websocket']
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            return False
    
    async def _get_socket_metadata(self) -> bool:
        """Obtém metadata para autenticação do WebSocket."""
        try:
            if not self.settings.CSGOEMPIRE_API_KEY:
                logger.error("❌ API key do CSGOEmpire não configurada")
                return False
            
            # Faz requisição para obter metadata
            url = "https://csgoempire.com/api/v2/user/metadata"
            headers = {
                'Authorization': f'Bearer {self.settings.CSGOEMPIRE_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"❌ Erro ao obter metadata: {response.status}")
                        return False
                    
                    data = await response.json()
                    
                    self.user_id = data.get('user', {}).get('id')
                    self.socket_token = data.get('socket_token')
                    self.socket_signature = data.get('socket_signature')
                    
                    if not all([self.user_id, self.socket_token, self.socket_signature]):
                        logger.error("❌ Dados de autenticação incompletos")
                        return False
                    
                    logger.info("✅ Metadata obtida com sucesso")
                    return True
                    
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
