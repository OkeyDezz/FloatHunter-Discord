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
import time
import uuid

logger = logging.getLogger(__name__)

class MarketplaceScanner:
    """
    Scanner de marketplace usando WebSocket para o Opportunity Bot.
    """
    
    def __init__(self):
        self.settings = Settings()
        
        # Log das configurações carregadas
        logger.info("🔧 Configurações carregadas:")
        logger.info(f"   - MIN_PRICE: ${self.settings.MIN_PRICE:.2f}")
        logger.info(f"   - MAX_PRICE: ${self.settings.MAX_PRICE:.2f}")
        logger.info(f"   - MIN_PROFIT_PERCENTAGE: {self.settings.MIN_PROFIT_PERCENTAGE:.1f}%")
        logger.info(f"   - MIN_LIQUIDITY_SCORE: {self.settings.MIN_LIQUIDITY_SCORE:.1f}")
        logger.info(f"   - COIN_TO_USD_FACTOR: {self.settings.COIN_TO_USD_FACTOR}")
        
        self.sio = socketio.AsyncClient()
        self.is_connected = False
        self.authenticated = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Dados de autenticação
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        self.user_model = None
        
        # Timestamps para monitoramento
        self._last_data_received = time.time()
        self._connection_start_time = None
        
        # Filtros
        self.profit_filter = ProfitFilter(
            self.settings.MIN_PROFIT_PERCENTAGE,
            self.settings.COIN_TO_USD_FACTOR
        )
        self.liquidity_filter = LiquidityFilter(self.settings.MIN_LIQUIDITY_SCORE)
        
        # Supabase client
        self.supabase = SupabaseClient()
        
        # Callback para oportunidades
        self.opportunity_callback: Optional[Callable] = None
        
        # Configura eventos
        self._setup_socket_events()
    
    def _setup_socket_events(self):
        """Configura os handlers de eventos do Socket.IO."""
        
        @self.sio.event
        async def connect():
            """Evento de conexão."""
            logger.info("🔌 Conectado ao WebSocket do CSGOEmpire")
            self._connection_start_time = time.time()
        
        @self.sio.event
        async def disconnect():
            """Evento de desconexão."""
            logger.info("🔌 Desconectado do WebSocket do CSGOEmpire")
            self.is_connected = False
            self.authenticated = False
        
        @self.sio.event
        async def connect_error(data):
            """Erro de conexão."""
            logger.error(f"❌ Erro de conexão WebSocket: {data}")
            self.is_connected = False
            self.authenticated = False
        
        @self.sio.event(namespace='/trade')
        async def connect():
            """Conectado ao namespace /trade."""
            logger.info("🔌 Conectado ao namespace /trade")
            self._connection_start_time = time.time()
            self.is_connected = True
            logger.info("✅ Status atualizado: is_connected = True")
        
        @self.sio.event(namespace='/trade')
        async def disconnect():
            """Desconectado do namespace /trade."""
            logger.info("🔌 Desconectado do namespace /trade")
            self.is_connected = False
            self.authenticated = False
            logger.info("✅ Status atualizado: is_connected = False, authenticated = False")
        
        @self.sio.on('identify', namespace='/trade')
        async def on_identify_response(data):
            """Resposta do evento identify."""
            logger.info(f"🆔 Resposta do identify recebida: {data}")
            self._update_last_data_received()
        
        @self.sio.on('init', namespace='/trade')
        async def on_init(data):
            """Evento de inicialização (mesmo do bot principal)."""
            logger.info(f"📡 Evento init recebido: {data}")
            try:
                # Verifica se é uma lista (alguns eventos retornam listas)
                if isinstance(data, list):
                    logger.warning(f"⚠️ Evento init retornou lista: {data}")
                    return
                
                if isinstance(data, dict) and data.get('authenticated'):
                    # Já autenticado - emite eventos necessários
                    logger.info("✅ Usuário já autenticado, configurando filtros...")
                    
                    # Configura filtros seguindo exatamente a documentação
                    await self.sio.emit('filters', {
                        "enabled": True,
                        "price_min": self.settings.MIN_PRICE,
                        "price_max": self.settings.MAX_PRICE
                    }, namespace='/trade')
                    logger.info("📤 Filtros básicos enviados")
                    
                    # Configura eventos permitidos (TODOS os eventos de leilão)
                    await self.sio.emit('allowedEvents', {
                        'events': ['new_item', 'updated_item', 'auction_update', 'auction_end', 'deleted_item', 'timesync', 'trade_status']
                    }, namespace='/trade')
                    logger.info("📤 Eventos permitidos configurados")
                    
                    # Inscreve nos canais seguindo a documentação
                    await self.sio.emit('subscribe', {'room': 'auctions'}, namespace='/trade')
                    logger.info("📤 Inscrição em leilões enviada")
                    
                    # Sincronização de tempo
                    await self.sio.emit('timesync', namespace='/trade')
                    logger.info("📤 Timesync solicitado")
                    
                    # Aguarda um pouco e envia heartbeat
                    await asyncio.sleep(1)
                    await self.sio.emit('ping', namespace='/trade')
                    logger.info("📤 Ping enviado")
                    
                    self.authenticated = True
                    self.is_connected = True
                    self._last_data_received = time.time()
                    logger.info("✅ Autenticado em /trade e filtros configurados")
                    logger.info("🎯 Bot pronto para receber itens de leilão!")
                else:
                    # Não autenticado - executa autenticação manual IMEDIATAMENTE
                    logger.info("🆔 Usuário não autenticado no init - executando autenticação manual...")
                    
                    # Executa autenticação manual
                    if await self._authenticate_websocket():
                        logger.info("✅ Autenticação manual bem-sucedida!")
                    else:
                        logger.error("❌ Falha na autenticação manual")
                    
            except Exception as e:
                logger.error(f"❌ Erro no init: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        @self.sio.on('ping', namespace='/trade')
        async def on_ping(data):
            """Resposta do ping."""
            logger.info(f"🏓 Pong recebido: {data}")
            self._update_last_data_received()
        
        @self.sio.on('new_item', namespace='/trade')
        async def on_new_item(data):
            """Novo item disponível."""
            try:
                # Trata tanto lista quanto dicionário
                if isinstance(data, list):
                    logger.info(f"🆕 NOVO ITEM RECEBIDO (lista): {len(data)} itens")
                    logger.info(f"📊 Dados completos: {data}")
                    # Processa cada item da lista
                    for item in data:
                        if isinstance(item, dict):
                            logger.info(f"🎯 Processando item: {item.get('market_name', 'Unknown')} (ID: {item.get('id', 'Unknown')})")
                            await self._process_item(item, 'new_item')
                        else:
                            logger.warning(f"⚠️ Item não é dicionário: {type(item)} - {item}")
                elif isinstance(data, dict):
                    logger.info(f"🆕 NOVO ITEM RECEBIDO: {data.get('market_name', 'Unknown')}")
                    logger.info(f"📊 Dados completos: {data}")
                    logger.info(f"🎯 Processando item: {data.get('market_name', 'Unknown')} (ID: {data.get('id', 'Unknown')})")
                    await self._process_item(data, 'new_item')
                else:
                    logger.warning(f"⚠️ Dados inesperados para new_item: {type(data)} - {data}")
                
                self._update_last_data_received()
            except Exception as e:
                logger.error(f"❌ Erro ao processar new_item: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        @self.sio.on('updated_item', namespace='/trade')
        async def on_updated_item(data):
            """Item atualizado."""
            try:
                # Trata tanto lista quanto dicionário
                if isinstance(data, list):
                    logger.info(f"🔄 ITEM ATUALIZADO (lista): {len(data)} itens")
                    logger.info(f"📊 Dados completos: {data}")
                    # Processa cada item da lista
                    for item in data:
                        if isinstance(item, dict):
                            logger.info(f"🎯 Processando item atualizado: {item.get('market_name', 'Unknown')} (ID: {item.get('id', 'Unknown')})")
                            await self._process_item(item, 'updated_item')
                        else:
                            logger.warning(f"⚠️ Item não é dicionário: {type(item)} - {item}")
                elif isinstance(data, dict):
                    logger.info(f"🔄 ITEM ATUALIZADO: {data.get('market_name', 'Unknown')}")
                    logger.info(f"📊 Dados completos: {data}")
                    logger.info(f"🎯 Processando item atualizado: {data.get('market_name', 'Unknown')} (ID: {data.get('id', 'Unknown')})")
                    await self._process_item(data, 'updated_item')
                else:
                    logger.warning(f"⚠️ Dados inesperados para updated_item: {type(data)} - {data}")
                
                self._update_last_data_received()
            except Exception as e:
                logger.error(f"❌ Erro ao processar updated_item: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        @self.sio.on('deleted_item', namespace='/trade')
        async def on_deleted_item(data):
            """Item removido."""
            try:
                if isinstance(data, list):
                    logger.info(f"🗑️ ITEM REMOVIDO (lista): {len(data)} itens")
                    # Tenta obter nomes dos itens removidos
                    item_names = []
                    for item_id in data:
                        if isinstance(item_id, (int, str)):
                            # Busca informações do item no cache ou faz log do ID
                            item_names.append(f"ID:{item_id}")
                        else:
                            item_names.append(f"Tipo:{type(item_id)}")
                    
                    logger.info(f"📊 Itens removidos: {', '.join(item_names)}")
                    logger.info(f"📊 Dados completos: {data}")
                elif isinstance(data, dict):
                    item_name = data.get('market_name', data.get('name', 'Unknown'))
                    item_id = data.get('id', 'Unknown')
                    logger.info(f"🗑️ ITEM REMOVIDO: {item_name} (ID: {item_id})")
                    logger.info(f"📊 Dados completos: {data}")
                else:
                    logger.info(f"🗑️ ITEM REMOVIDO: {type(data)} - {data}")
                
                self._update_last_data_received()
            except Exception as e:
                logger.error(f"❌ Erro ao processar deleted_item: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        @self.sio.on('auction_update', namespace='/trade')
        async def on_auction_update(data):
            """Atualização de leilão."""
            try:
                if isinstance(data, list):
                    logger.info(f"🏷️ ATUALIZAÇÃO DE LEILÃO (lista): {len(data)} itens")
                    # Tenta obter nomes dos itens
                    item_names = []
                    for item in data:
                        if isinstance(item, dict):
                            item_name = item.get('market_name', item.get('name', 'Unknown'))
                            item_id = item.get('id', 'Unknown')
                            item_names.append(f"{item_name} (ID: {item_id})")
                        else:
                            item_names.append(f"Tipo:{type(item)}")
                    
                    logger.info(f"📊 Itens atualizados: {', '.join(item_names)}")
                    logger.info(f"📊 Dados completos: {data}")
                elif isinstance(data, dict):
                    item_name = data.get('market_name', data.get('name', 'Unknown'))
                    item_id = data.get('id', 'Unknown')
                    logger.info(f"🏷️ ATUALIZAÇÃO DE LEILÃO: {item_name} (ID: {item_id})")
                    logger.info(f"📊 Dados completos: {data}")
                else:
                    logger.info(f"🏷️ ATUALIZAÇÃO DE LEILÃO: {type(data)} - {data}")
                
                self._update_last_data_received()
            except Exception as e:
                logger.error(f"❌ Erro ao processar auction_update: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        @self.sio.on('auction_end', namespace='/trade')
        async def on_auction_end(data):
            """Fim de leilão."""
            try:
                if isinstance(data, list):
                    logger.info(f"🏁 LEILÃO FINALIZADO (lista): {len(data)} itens")
                    # Tenta obter nomes dos itens
                    item_names = []
                    for item in data:
                        if isinstance(item, dict):
                            item_name = item.get('market_name', item.get('name', 'Unknown'))
                            item_id = item.get('id', 'Unknown')
                            item_names.append(f"{item_name} (ID: {item_id})")
                        else:
                            item_names.append(f"Tipo:{type(item)}")
                    
                    logger.info(f"📊 Leilões finalizados: {', '.join(item_names)}")
                    logger.info(f"📊 Dados completos: {data}")
                elif isinstance(data, dict):
                    item_name = data.get('market_name', data.get('name', 'Unknown'))
                    item_id = data.get('id', 'Unknown')
                    logger.info(f"🏁 LEILÃO FINALIZADO: {item_name} (ID: {item_id})")
                    logger.info(f"📊 Dados completos: {data}")
                else:
                    logger.info(f"🏁 LEILÃO FINALIZADO: {type(data)} - {data}")
                
                self._update_last_data_received()
                # Não processa fim de leilão como oportunidade
            except Exception as e:
                logger.error(f"❌ Erro ao processar auction_end: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        @self.sio.on('trade_status', namespace='/trade')
        async def on_trade_status(data):
            """Status de trade."""
            try:
                if isinstance(data, list):
                    logger.info(f"📊 STATUS DE TRADE (lista): {len(data)} itens")
                    logger.info(f"📊 Dados completos: {data}")
                elif isinstance(data, dict):
                    logger.info(f"📊 STATUS DE TRADE: {data}")
                else:
                    logger.info(f"📊 STATUS DE TRADE: {type(data)} - {data}")
                
                self._update_last_data_received()
            except Exception as e:
                logger.error(f"❌ Erro ao processar trade_status: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        @self.sio.on('timesync', namespace='/trade')
        async def on_timesync(data):
            """Sincronização de tempo."""
            logger.debug(f"⏰ Timesync recebido: {data}")
            self._update_last_data_received()
        
        @self.sio.on('error', namespace='/trade')
        async def on_error(data):
            """Erro do servidor."""
            logger.error(f"❌ Erro do servidor WebSocket: {data}")
        
        @self.sio.on('connect_error', namespace='/trade')
        async def on_connect_error(data):
            """Erro de conexão."""
            logger.error(f"❌ Erro de conexão WebSocket: {data}")
        
        @self.sio.on('disconnect', namespace='/trade')
        async def on_disconnect(data):
            """Desconexão."""
            logger.warning(f"🔌 Desconectado do WebSocket: {data}")
            self.is_connected = False
            self.authenticated = False
        
        # Handler genérico para capturar todos os eventos (mesmo do bot principal)
        @self.sio.on('*', namespace='/trade')
        async def catch_all(event_name, data):
            """Captura todos os eventos para debug."""
            try:
                # Log especial para o evento init
                if event_name == 'init':
                    logger.info(f"🎯 EVENTO INIT CAPTURADO: {event_name}")
                    logger.info(f"📡 Dados do init: {data}")
                    # Chama o handler específico do init
                    await on_init(data)
                    return
                
                # Log especial para o evento connect
                if event_name == 'connect':
                    logger.info(f"🔌 EVENTO CONNECT CAPTURADO: {event_name}")
                    logger.info(f"📡 Dados do connect: {data}")
                    return
                
                # Log especial para o evento disconnect
                if event_name == 'disconnect':
                    logger.info(f"🔌 EVENTO DISCONNECT CAPTURADO: {event_name}")
                    logger.info(f"📡 Dados do disconnect: {data}")
                    return
                
                # Log especial para o evento connect_error
                if event_name == 'connect_error':
                    logger.error(f"❌ EVENTO CONNECT_ERROR CAPTURADO: {event_name}")
                    logger.error(f"📡 Dados do connect_error: {data}")
                    return
                
                # Ignora eventos que já temos handlers específicos
                if event_name in ['identify', 'new_item', 'updated_item', 'deleted_item', 'auction_update', 'auction_end', 'timesync', 'trade_status', 'error', 'ping']:
                    return
                
                # Verifica se é uma lista ou dicionário
                if isinstance(data, list):
                    logger.info(f"📨 Evento não tratado: {event_name} - Lista com {len(data)} itens")
                    self._update_last_data_received()
                elif isinstance(data, dict):
                    logger.info(f"📨 Evento não tratado: {event_name} - {type(data).__name__}")
                    self._update_last_data_received()
                else:
                    logger.info(f"📨 Evento não tratado: {event_name} - Tipo: {type(data).__name__}")
                    self._update_last_data_received()
            except Exception as e:
                logger.error(f"❌ Erro no handler genérico para evento {event_name}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
    
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
            
            # Filtro de preço básico (antes de enriquecer com database)
            if not self._check_basic_price_filter(item):
                logger.debug(f"Item {item.get('name')} rejeitado pelo filtro de preço básico: ${item.get('price', 0):.2f}")
                return
            
            # Busca informações adicionais da database
            await self._enrich_item_data(item)
            
            # Verifica se passa nos filtros
            if await self._check_filters(item):
                logger.info(f"🎯 OPORTUNIDADE ENCONTRADA: {item.get('name')}")
                
                # Chama callback de oportunidade
                if self.opportunity_callback:
                    await self.opportunity_callback(item, 'csgoempire')
                else:
                    logger.warning("⚠️ Callback de oportunidade não configurado")
            else:
                logger.debug(f"Item {item.get('name')} não passou nos filtros")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _check_basic_price_filter(self, item: Dict) -> bool:
        """
        Filtro de preço básico aplicado antes de enriquecer com database.
        Rejeita itens com preços muito baixos ou muito altos.
        """
        try:
            price_usd = item.get('price')
            if price_usd is None:
                logger.debug(f"Item {item.get('name')} sem preço, rejeitando")
                return False
            
            # Filtros de preço configurados
            min_price = self.settings.MIN_PRICE
            max_price = self.settings.MAX_PRICE
            
            # Log detalhado dos valores
            logger.info(f"🔍 Filtro de preço básico para: {item.get('name')}")
            logger.info(f"   - Preço do item: ${price_usd:.2f}")
            logger.info(f"   - MIN_PRICE configurado: ${min_price:.2f}")
            logger.info(f"   - MAX_PRICE configurado: ${max_price:.2f}")
            
            # Verifica preço mínimo
            if price_usd < min_price:
                logger.info(f"❌ Item {item.get('name')} REJEITADO: ${price_usd:.2f} < ${min_price:.2f} (MIN_PRICE)")
                return False
            
            # Verifica preço máximo
            if price_usd > max_price:
                logger.info(f"❌ Item {item.get('name')} REJEITADO: ${price_usd:.2f} > ${max_price:.2f} (MAX_PRICE)")
                return False
            
            logger.info(f"✅ Item {item.get('name')} ACEITO no filtro de preço básico: ${price_usd:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar filtro de preço básico: {e}")
            return False
    
    async def _enrich_item_data(self, item: Dict):
        """Enriquece o item com dados da database (preço Buff163 e liquidez)."""
        try:
            # Usa os campos parseados do item
            base_name = item.get('base_name')
            is_stattrak = item.get('is_stattrak', False)
            is_souvenir = item.get('is_souvenir', False)
            condition = item.get('condition', '')
            
            if not base_name:
                logger.warning("⚠️ Sem base_name para enriquecer item")
                return
            
            logger.info(f"🔍 Enriquecendo item: {base_name}")
            logger.info(f"   - StatTrak: {is_stattrak}")
            logger.info(f"   - Souvenir: {is_souvenir}")
            logger.info(f"   - Condição: {condition}")
            
            # Busca preço Buff163 usando os campos corretos
            price_buff163 = await self.supabase.get_buff163_price_advanced(
                base_name=base_name,
                is_stattrak=is_stattrak,
                is_souvenir=is_souvenir,
                condition=condition
            )
            
            if price_buff163:
                item['price_buff163'] = price_buff163
                logger.info(f"💰 Preço Buff163 encontrado: ${price_buff163:.2f}")
            else:
                logger.warning(f"⚠️ Preço Buff163 não encontrado para: {base_name}")
            
            # Busca score de liquidez usando os campos corretos
            liquidity_score = await self.supabase.get_liquidity_score_advanced(
                base_name=base_name,
                is_stattrak=is_stattrak,
                is_souvenir=is_souvenir,
                condition=condition
            )
            
            if liquidity_score is not None:
                item['liquidity_score'] = liquidity_score
                logger.info(f"💧 Score de liquidez encontrado: {liquidity_score:.1f}")
            else:
                logger.warning(f"⚠️ Score de liquidez não encontrado para: {base_name}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao enriquecer item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _extract_item_data(self, data: Dict) -> Optional[Dict]:
        """Extrai dados relevantes do item do CSGOEmpire."""
        try:
            # Campos obrigatórios do CSGOEmpire
            item_id = data.get('id')
            market_name = data.get('market_name')
            purchase_price = data.get('purchase_price')  # Preço em centavos
            suggested_price = data.get('suggested_price')  # Preço sugerido em USD
            
            if not all([item_id, market_name, purchase_price]):
                logger.debug(f"Dados incompletos do item: {data}")
                return None
            
            # Parse do nome do item (baseado no bot principal)
            base_name, is_stattrak, is_souvenir, condition = self._parse_market_hash_name(market_name)
            
            # Dados adicionais
            float_value = data.get('wear')
            auction_ends_at = data.get('auction_ends_at')
            auction_highest_bid = data.get('auction_highest_bid')
            auction_number_of_bids = data.get('auction_number_of_bids', 0)
            
            # Converte preço de centavos para USD (fator 0.614)
            # CSGOEmpire retorna preços em centavos, não em coin
            price_usd = (purchase_price / 100) * self.settings.COIN_TO_USD_FACTOR
            
            logger.info(f"💰 Item: {market_name}")
            logger.info(f"   - Base: {base_name}")
            logger.info(f"   - StatTrak: {is_stattrak}")
            logger.info(f"   - Souvenir: {is_souvenir}")
            logger.info(f"   - Condição: {condition}")
            logger.info(f"   - Preço CSGOEmpire: {purchase_price} centavos = ${price_usd:.2f}")
            logger.info(f"   - Preço sugerido CSGOEmpire: ${suggested_price}")
            logger.info(f"   - Leilão termina: {auction_ends_at}")
            logger.info(f"   - Lances: {auction_number_of_bids}")
            
            return {
                'id': item_id,
                'name': market_name,
                'market_hash_name': market_name,  # Nome completo para busca
                'base_name': base_name,  # Nome base sem flags
                'is_stattrak': is_stattrak,
                'is_souvenir': is_souvenir,
                'condition': condition,
                'price': price_usd,  # Preço convertido para USD
                'price_centavos': purchase_price,  # Preço original em centavos
                'suggested_price_csgoempire': suggested_price,  # Preço sugerido do CSGOEmpire
                'float_value': float_value,
                'auction_ends_at': auction_ends_at,
                'auction_highest_bid': auction_highest_bid,
                'auction_number_of_bids': auction_number_of_bids,
                'marketplace': 'csgoempire',
                'detected_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados do item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _parse_market_hash_name(self, name: str) -> tuple:
        """
        Parse do nome do item (baseado no bot principal).
        
        Args:
            name: Nome completo do item
            
        Returns:
            tuple: (base_name, is_stattrak, is_souvenir, condition)
        """
        try:
            if not name:
                return "", False, False, None
            
            s = name.strip()
            stattrak = ("StatTrak™" in s) or ("StatTrak" in s)
            souvenir = ("Souvenir" in s)
            condition_local = None
            
            # Lista de condições possíveis
            conditions = [
                "Factory New",
                "Minimal Wear", 
                "Field-Tested",
                "Well-Worn",
                "Battle-Scarred",
            ]
            
            # Remove a condição do final do nome
            for c in conditions:
                suffix = f"({c})"
                if s.endswith(suffix):
                    condition_local = c
                    s = s[: -len(suffix)].strip()
                    break
            
            # Remove flags do início do nome
            base = (
                s.replace("StatTrak™ ", "")
                 .replace("StatTrak ", "")
                 .replace("Souvenir ", "")
                 .strip()
            )
            
            return base, stattrak, souvenir, condition_local
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse do nome: {e}")
            return name, False, False, None
    
    async def _check_filters(self, item: Dict) -> bool:
        """Verifica se o item passa nos filtros configurados."""
        try:
            # Filtro de lucro
            if not await self.profit_filter.check(item):
                logger.debug(f"Item {item.get('name')} rejeitado pelo filtro de lucro")
                return False
            
            # Filtro de liquidez
            if not await self.liquidity_filter.check(item):
                logger.debug(f"Item {item.get('name')} rejeitado pelo filtro de liquidez")
                return False
            
            logger.debug(f"Item {item.get('name')} passou em todos os filtros")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar filtros: {e}")
            return False
    
    async def _check_connection_health(self) -> bool:
        """Verifica se a conexão WebSocket está realmente ativa."""
        try:
            # Verifica se o socket está conectado
            if not self.sio.connected:
                logger.debug("❌ Socket.IO não está conectado")
                return False
            
            # Verifica se está autenticado
            if not self.authenticated:
                logger.debug("❌ WebSocket não está autenticado")
                return False
            
            # Verifica se recebeu dados recentemente
            if hasattr(self, '_last_data_received'):
                time_since_data = time.time() - self._last_data_received
                if time_since_data > 300:  # 5 minutos sem dados
                    logger.warning(f"⚠️ Sem dados recebidos há {time_since_data:.0f}s")
                    return False
            
            logger.debug("✅ Conexão WebSocket está saudável")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar saúde da conexão: {e}")
            return False
    
    async def _send_heartbeat(self):
        """Envia heartbeat para manter conexão ativa."""
        try:
            if self.sio.connected and self.authenticated:
                # Envia evento de ping (se suportado pelo servidor)
                await self.sio.emit('ping', namespace='/trade')
                logger.debug("💓 Heartbeat enviado")
        except Exception as e:
            logger.debug(f"⚠️ Erro ao enviar heartbeat: {e}")
    
    def _update_last_data_received(self):
        """Atualiza timestamp do último dado recebido."""
        self._last_data_received = time.time()
    
    async def _connect_websocket(self) -> bool:
        """Conecta ao WebSocket do CSGOEmpire seguindo exatamente a documentação."""
        try:
            # Verifica se já está conectado
            if self.sio.connected:
                logger.info("✅ WebSocket já está conectado")
                return True
            
            if not all([self.user_id, self.socket_token, self.socket_signature]):
                logger.error("❌ Dados de autenticação incompletos")
                logger.error(f"  - user_id: {self.user_id}")
                logger.error(f"  - socket_token: {self.socket_token[:20]}..." if self.socket_token else "None")
                logger.error(f"  - socket_signature: {self.socket_signature[:20]}..." if self.socket_signature else "None")
                return False
            
            # Headers usados pelo bot principal
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Origin': 'https://trade.csgoempire.com',
                'Referer': 'https://trade.csgoempire.com/'
            }
            
            # Query string com uid e token (mesmo formato do bot principal)
            qs = f"uid={self.user_id}&token={self.socket_token}"
            
            logger.info(f"🔌 Conectando ao WebSocket: trade.csgoempire.com/?{qs}")
            
            # Conecta usando a mesma URL e namespace do bot principal
            await self.sio.connect(
                f"https://trade.csgoempire.com/?{qs}",
                socketio_path='s/',
                headers=headers,
                transports=['websocket'],
                namespaces=['/trade']
            )
            
            logger.info("🔌 WebSocket conectado ao namespace /trade")
            
            # Aguarda um pouco para a conexão estabilizar
            await asyncio.sleep(2)
            
            # Verifica se ainda está conectado
            if not self.sio.connected:
                logger.error("❌ WebSocket desconectado após conexão")
                return False
            
            logger.info("✅ WebSocket conectado com sucesso")
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _authenticate_websocket(self) -> bool:
        """Autentica no WebSocket seguindo exatamente a documentação do CSGOEmpire."""
        try:
            logger.info("🔐 Iniciando autenticação WebSocket...")
            
            # Verifica se temos todos os dados necessários
            if not all([self.user_id, self.user_model, self.socket_token, self.socket_signature]):
                logger.error("❌ Dados incompletos para autenticação:")
                logger.error(f"  - user_id: {self.user_id}")
                logger.error(f"  - user_model: {self.user_model}")
                logger.error(f"  - socket_token: {self.socket_token[:20] if self.socket_token else 'None'}...")
                logger.error(f"  - socket_signature: {self.socket_signature[:20] if self.socket_signature else 'None'}...")
                return False
            
            # Payload exatamente como na documentação
            identify_payload = {
                "uid": self.user_id,
                "model": self.user_model,
                "authorizationToken": self.socket_token,
                "signature": self.socket_signature,
                "uuid": str(uuid.uuid4())  # UUID opcional como na documentação
            }
            
            logger.info(f"📤 Emitindo identify com uid: {self.user_id}")
            logger.info(f"📤 Payload completo: {identify_payload}")
            
            try:
                await self.sio.emit('identify', identify_payload, namespace='/trade')
                logger.info("✅ Evento identify emitido com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao emitir identify: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
            
            logger.info("⏳ Identify enviado, aguardando autenticação...")
            
            # Aguarda autenticação conforme documentação
            for i in range(30):  # 30 segundos timeout para autenticação
                if self.authenticated:
                    logger.info("✅ Autenticação confirmada!")
                    return True
                if i % 5 == 0:  # Log a cada 5 segundos
                    logger.info(f"⏳ Aguardando confirmação de autenticação... ({i}s)")
                await asyncio.sleep(1)
            
            logger.error("❌ Timeout aguardando confirmação de autenticação")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro na autenticação: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def connect(self) -> bool:
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            # Verifica se já está conectado
            if self.is_connected and self.authenticated:
                logger.info("✅ Já conectado ao WebSocket")
                return True
            
            # Verifica se excedeu tentativas de reconexão
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                logger.error(f"❌ Máximo de tentativas de reconexão atingido ({self.max_reconnect_attempts})")
                return False
            
            logger.info("🔄 Tentando conectar ao WebSocket...")
            
            # Testa conexão com Supabase
            logger.info("🔍 Testando conexão com Supabase...")
            if not await self.supabase.test_connection():
                logger.error("❌ Falha na conexão com Supabase")
                return False
            logger.info("✅ Conexão com Supabase OK")
            
            # Obtém metadata (já verifica API key indiretamente)
            if not await self._get_socket_metadata():
                logger.error("❌ Falha ao obter metadata")
                self.reconnect_attempts += 1
                return False
            
            # Configura handlers ANTES de conectar (crítico!)
            logger.info("🔧 Configurando handlers de eventos...")
            self._setup_socket_events()
            
            # Conecta ao WebSocket
            if not await self._connect_websocket():
                logger.error("❌ Falha ao conectar WebSocket")
                self.reconnect_attempts += 1
                return False
            
            # Aguarda eventos e tenta autenticação
            logger.info("⏳ Aguardando eventos e tentando autenticação...")
            
            # Loop de aguardar eventos ou autenticação
            for i in range(30):  # 30 segundos timeout total
                if self.authenticated:
                    logger.info("✅ Autenticação confirmada!")
                    break
                
                if i % 5 == 0:  # Log a cada 5 segundos
                    logger.info(f"⏳ Aguardando autenticação... ({i}s)")
                    logger.info(f"📊 Status: sio.connected={self.sio.connected}, authenticated={self.authenticated}")
                
                # Se chegou a 10 segundos e ainda não autenticou, tenta autenticação manual
                if i == 10 and not self.authenticated:
                    logger.info("🔄 Tentando autenticação manual após 10s...")
                    if await self._authenticate_websocket():
                        logger.info("✅ Autenticação manual bem-sucedida!")
                        break
                    else:
                        logger.warning("⚠️ Autenticação manual falhou, continuando aguardando...")
                
                await asyncio.sleep(1)
            
            # Verifica se foi autenticado
            if not self.authenticated:
                logger.error("❌ Falha na autenticação após 30s")
                self.reconnect_attempts += 1
                return False
            
            # Reset de tentativas se conectou com sucesso
            self.reconnect_attempts = 0
            logger.info("✅ Conectado e autenticado com sucesso ao WebSocket")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            self.reconnect_attempts += 1
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
            if self.sio.connected:
                await self.sio.disconnect()
                logger.info("🔌 WebSocket desconectado")
            
            self.is_connected = False
            self.authenticated = False
            self.reconnect_attempts = 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao desconectar: {e}")
    
    async def run_forever(self):
        """Executa o scanner indefinidamente."""
        try:
            logger.info("🚀 Iniciando scanner de marketplace...")
            
            while True:
                try:
                    # Tenta conectar
                    if await self.connect():
                        logger.info("✅ Scanner conectado, aguardando oportunidades...")
                        
                        # Loop de monitoramento com verificação de saúde
                        while True:
                            # Verifica saúde da conexão
                            if not await self._check_connection_health():
                                logger.warning("⚠️ Conexão não está saudável, tentando reconectar...")
                                break
                            
                            # Envia heartbeat a cada 30 segundos
                            await self._send_heartbeat()
                            
                            # Aguarda próximo ciclo
                            await asyncio.sleep(30)
                            
                            # Log de status a cada 2 minutos
                            if hasattr(self, '_connection_start_time') and self._connection_start_time:
                                uptime = time.time() - self._connection_start_time
                                if int(uptime) % 120 == 0:  # A cada 2 minutos
                                    logger.info(f"📊 Status: Conectado há {int(uptime)}s, autenticado: {self.authenticated}")
                        
                        # Se chegou aqui, perdeu conexão
                        logger.warning("⚠️ Conexão perdida, aguardando antes de reconectar...")
                        await asyncio.sleep(10)
                        
                    else:
                        # Falha na conexão
                        if self.reconnect_attempts >= self.max_reconnect_attempts:
                            logger.error("❌ Máximo de tentativas atingido, aguardando 5 minutos...")
                            await asyncio.sleep(300)  # 5 minutos
                            self.reconnect_attempts = 0  # Reset
                        else:
                            logger.warning(f"⚠️ Tentativa {self.reconnect_attempts + 1}/{self.max_reconnect_attempts} falhou")
                            await asyncio.sleep(30)  # 30 segundos
                            
                except Exception as e:
                    logger.error(f"❌ Erro no loop principal: {e}")
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("🛑 Scanner cancelado")
        except Exception as e:
            logger.error(f"❌ Erro fatal no scanner: {e}")
        finally:
            await self.disconnect()
