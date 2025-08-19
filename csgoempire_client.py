#!/usr/bin/env python3
"""
CSGOEmpire Client - Cliente limpo e novo para CSGOEmpire.
Implementa exatamente a documentação oficial.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Optional, Callable
import aiohttp
import socketio

logger = logging.getLogger(__name__)

class CSGOEmpireClient:
    """Cliente limpo para CSGOEmpire."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.domain = "csgoempire.com"
        self.socket_endpoint = f"wss://trade.{self.domain}/trade"
        
        # Socket.IO client
        self.sio = None
        self.is_connected = False
        self.is_authenticated = False
        
        # User data
        self.user_data = None
        self.user_data_refreshed_at = None
        
        # Callbacks
        self.on_item_callback = None
        
        # Status
        self.running = False
        
        # Headers para API
        self.api_headers = {
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'CSGOEmpire Opportunity Bot'
        }
        
        logger.info("🔧 CSGOEmpire Client inicializado")
    
    async def get_user_metadata(self) -> bool:
        """Obtém metadata do usuário."""
        try:
            logger.info("🔍 Obtendo metadata do usuário...")
            
            # Verifica se precisa atualizar (válido por 30s, atualiza a cada 15s)
            if (self.user_data_refreshed_at and 
                self.user_data_refreshed_at > time.time() - 15):
                logger.debug("✅ Metadata ainda válida")
                return True
            
            url = f"https://{self.domain}/api/v2/metadata/socket"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.api_headers) as response:
                    if response.status == 200:
                        self.user_data = await response.json()
                        self.user_data_refreshed_at = time.time()
                        
                        user_name = self.user_data.get('user', {}).get('name', 'Unknown')
                        user_id = self.user_data.get('user', {}).get('id', 'Unknown')
                        
                        logger.info(f"✅ Metadata obtida: {user_name} (ID: {user_id})")
                        logger.info(f"   - Socket Token: {'✅' if self.user_data.get('socket_token') else '❌'}")
                        logger.info(f"   - Socket Signature: {'✅' if self.user_data.get('socket_signature') else '❌'}")
                        
                        return True
                    else:
                        logger.error(f"❌ Falha ao obter metadata: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadata: {e}")
            return False
    
    def setup_socket_events(self):
        """Configura eventos do Socket.IO."""
        try:
            # Cria Socket.IO client
            self.sio = socketio.AsyncClient(
                transports=['websocket'],
                logger=False,  # Desabilita logs internos
                engineio_logger=False
            )
            
            # Evento de conexão
            @self.sio.event
            async def connect():
                logger.info("🔗 Conectado ao WebSocket CSGOEmpire")
                self.is_connected = True
                
                # Aguarda um pouco antes de identificar
                await asyncio.sleep(1)
                
                # Emite identificação
                if self.user_data:
                    await self.emit_identify()
                else:
                    logger.error("❌ Dados do usuário não disponíveis")
            
            # Evento de desconexão
            @self.sio.event
            async def disconnect():
                logger.warning("🔌 Desconectado do WebSocket CSGOEmpire")
                self.is_connected = False
                self.is_authenticated = False
            
            # Evento de erro de conexão
            @self.sio.event
            async def connect_error(data):
                logger.error(f"❌ Erro de conexão: {data}")
                self.is_connected = False
            
            # Evento INIT (autenticação)
            @self.sio.event
            async def init(data):
                try:
                    logger.info(f"🚀 Evento INIT recebido")
                    
                    if data and data.get('authenticated'):
                        self.is_authenticated = True
                        user_name = data.get('name', 'Unknown')
                        logger.info(f"✅ Autenticado como: {user_name}")
                        
                        # Emite filtros para receber eventos
                        await self.emit_filters()
                        
                    else:
                        logger.info("🔄 Não autenticado - emitindo identificação...")
                        await self.emit_identify()
                        
                except Exception as e:
                    logger.error(f"❌ Erro no evento INIT: {e}")
            
            # Evento TIMESYNC
            @self.sio.event
            async def timesync(data):
                logger.debug(f"⏰ Timesync: {data}")
            
            # Evento NEW_ITEM
            @self.sio.event
            async def new_item(data):
                try:
                    item_count = len(data) if isinstance(data, list) else 1
                    logger.info(f"🆕 NOVO ITEM: {item_count} item(s)")
                    
                    if self.on_item_callback:
                        if isinstance(data, list):
                            for item in data:
                                await self.on_item_callback(item, "new_item")
                        else:
                            await self.on_item_callback(data, "new_item")
                            
                except Exception as e:
                    logger.error(f"❌ Erro no evento new_item: {e}")
            
            # Evento UPDATED_ITEM
            @self.sio.event
            async def updated_item(data):
                try:
                    item_count = len(data) if isinstance(data, list) else 1
                    logger.info(f"🔄 ITEM ATUALIZADO: {item_count} item(s)")
                    
                    if self.on_item_callback:
                        if isinstance(data, list):
                            for item in data:
                                await self.on_item_callback(item, "updated_item")
                        else:
                            await self.on_item_callback(data, "updated_item")
                            
                except Exception as e:
                    logger.error(f"❌ Erro no evento updated_item: {e}")
            
            # Evento DELETED_ITEM
            @self.sio.event
            async def deleted_item(data):
                try:
                    item_count = len(data) if isinstance(data, list) else 1
                    logger.info(f"🗑️ ITEM DELETADO: {item_count} item(s)")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no evento deleted_item: {e}")
            
            # Evento AUCTION_UPDATE
            @self.sio.event
            async def auction_update(data):
                try:
                    item_count = len(data) if isinstance(data, list) else 1
                    logger.info(f"🏷️ LEILÃO ATUALIZADO: {item_count} item(s)")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no evento auction_update: {e}")
            
            # Evento TRADE_STATUS
            @self.sio.event
            async def trade_status(data):
                try:
                    trade_type = data.get('type', 'unknown')
                    logger.info(f"📦 TRADE STATUS: {trade_type}")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no evento trade_status: {e}")
            
            # Evento DEPOSIT_FAILED
            @self.sio.event
            async def deposit_failed(data):
                try:
                    logger.warning(f"❌ DEPÓSITO FALHOU: {data}")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no evento deposit_failed: {e}")
            
            logger.info("✅ Eventos do Socket.IO configurados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar eventos: {e}")
            return False
    
    async def emit_identify(self):
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
                "uuid": f"bot-{int(time.time())}"
            }
            
            logger.info(f"🆔 Emitindo identificação para UID: {identify_data['uid']}")
            await self.sio.emit('identify', identify_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao emitir identificação: {e}")
    
    async def emit_filters(self):
        """Emite filtros para receber eventos."""
        try:
            filters = {
                "price_max": 9999999  # Filtro padrão da documentação
            }
            
            logger.info("🔍 Emitindo filtros para receber eventos")
            await self.sio.emit('filters', filters)
            
        except Exception as e:
            logger.error(f"❌ Erro ao emitir filtros: {e}")
    
    async def connect(self) -> bool:
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            logger.info("🔗 Conectando ao WebSocket CSGOEmpire...")
            
            # Obtém metadata do usuário
            if not await self.get_user_metadata():
                logger.error("❌ Falha ao obter metadata")
                return False
            
            # Configura eventos do Socket.IO
            if not self.setup_socket_events():
                logger.error("❌ Falha ao configurar eventos")
                return False
            
            # Parâmetros de conexão
            query_params = {
                'uid': self.user_data['user']['id'],
                'token': self.user_data['socket_token']
            }
            
            # Headers extras
            extra_headers = {
                'User-agent': f"{self.user_data['user']['id']} API Bot"
            }
            
            logger.info(f"🔗 Conectando a: {self.socket_endpoint}")
            logger.info(f"   - UID: {query_params['uid']}")
            logger.info(f"   - Token: {query_params['token'][:10]}...")
            
            # Conecta
            await self.sio.connect(
                self.socket_endpoint,
                query=query_params,
                headers=extra_headers,
                wait_timeout=30
            )
            
            logger.info("✅ Conectado ao WebSocket CSGOEmpire")
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha ao conectar: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta do WebSocket."""
        try:
            if self.sio and self.is_connected:
                await self.sio.disconnect()
                logger.info("✅ Desconectado do WebSocket CSGOEmpire")
            
            self.is_connected = False
            self.is_authenticated = False
            
        except Exception as e:
            logger.error(f"❌ Erro ao desconectar: {e}")
    
    async def start(self, on_item_callback: Optional[Callable] = None):
        """Inicia o cliente."""
        try:
            logger.info("🚀 Iniciando CSGOEmpire Client...")
            
            # Define callback
            if on_item_callback:
                self.on_item_callback = on_item_callback
                logger.info("✅ Callback de item configurado")
            
            # Conecta
            if not await self.connect():
                logger.error("❌ Falha ao conectar")
                return False
            
            self.running = True
            logger.info("✅ CSGOEmpire Client iniciado com sucesso")
            
            # Loop principal
            while self.running:
                try:
                    await asyncio.sleep(30)
                    
                    # Log de status
                    if self.is_connected and self.is_authenticated:
                        logger.info("💓 WebSocket ativo - monitorando itens...")
                    elif self.is_connected:
                        logger.warning("⚠️ Conectado mas não autenticado...")
                    else:
                        logger.error("❌ WebSocket desconectado")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Erro no loop principal: {e}")
                    break
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar cliente: {e}")
            return False
    
    async def stop(self):
        """Para o cliente."""
        try:
            logger.info("🛑 Parando CSGOEmpire Client...")
            
            self.running = False
            
            # Desconecta
            await self.disconnect()
            
            logger.info("✅ CSGOEmpire Client parado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao parar cliente: {e}")
    
    def get_status(self) -> Dict:
        """Retorna status do cliente."""
        return {
            'running': self.running,
            'connected': self.is_connected,
            'authenticated': self.is_authenticated,
            'user_data': bool(self.user_data)
        }
