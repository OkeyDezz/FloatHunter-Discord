"""
Scanner de marketplace para o Opportunity Bot.
Monitora CSGOEmpire via WebSocket e identifica oportunidades.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Optional, Callable, List
from datetime import datetime

import socketio
import aiohttp

from .discord_poster import DiscordPoster
from ..filters.profit_filter import ProfitFilter
from ..filters.liquidity_filter import LiquidityFilter
from ..utils.supabase_client import SupabaseClient
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class MarketplaceScanner:
    """
    Scanner de marketplace que monitora CSGOEmpire via WebSocket.
    Baseado na arquitetura eficiente do bot principal.
    """
    
    def __init__(self, settings: Settings, discord_poster: DiscordPoster, 
                 opportunity_callback: Optional[Callable] = None):
        """
        Inicializa o scanner.
        
        Args:
            settings: Configurações do bot
            discord_poster: Cliente Discord para envio de oportunidades
            opportunity_callback: Callback para oportunidades encontradas
        """
        self.settings = settings
        self.discord_poster = discord_poster
        self.opportunity_callback = opportunity_callback
        
        # Cliente Supabase
        self.supabase = SupabaseClient()
        
        # WebSocket
        self.sio = socketio.AsyncClient()
        self.authenticated = False
        self.is_connected = False
        
        # Credenciais
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        self.user_model = None
        
        # Estado
        self.running = False
        self._last_data_received = time.time()
        self._last_stable_connection = time.time()
        
        # Estatísticas
        self.stats = {
            'items_received': 0,
            'items_processed': 0,
            'opportunities_found': 0,
            'websocket_events': 0,
            'last_opportunity': None
        }
        
        # Filtros pré-inicializados para performance
        self.profit_filter = ProfitFilter(settings.MIN_PROFIT_PERCENTAGE)
        self.liquidity_filter = LiquidityFilter(settings.MIN_LIQUIDITY_SCORE)
        
        # Cache de itens processados para evitar duplicatas
        self.processed_items = set()
        self.cache_ttl = 300  # 5 minutos
        
        # Configura handlers
        self._setup_websocket_handlers()
        
        logger.info("🔧 Configurações carregadas:")
        logger.info(f"   - MIN_PRICE: ${settings.MIN_PRICE:.2f}")
        logger.info(f"   - MAX_PRICE: ${settings.MAX_PRICE:.2f}")
        logger.info(f"   - MIN_PROFIT_PERCENTAGE: {settings.MIN_PROFIT_PERCENTAGE:.1f}%")
        logger.info(f"   - MIN_LIQUIDITY_SCORE: {settings.MIN_LIQUIDITY_SCORE:.1f}")
        logger.info(f"   - COIN_TO_USD_FACTOR: {settings.COIN_TO_USD_FACTOR}")
    
    async def start(self):
        """Inicia o scanner."""
        try:
            if self.running:
                logger.warning("⚠️ Scanner já está rodando")
                return
            
            self.running = True
            logger.info("🚀 Iniciando scanner de marketplace...")
            
            # Testa conexão com Supabase
            await self._test_supabase_connection()
            
            # Conecta ao WebSocket
            await self._connect_websocket()
            
            logger.info("✅ Scanner iniciado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar scanner: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Para o scanner."""
        try:
            self.running = False
            logger.info("🛑 Parando scanner...")
            
            if self.sio and hasattr(self.sio, 'connected') and self.sio.connected:
                await self.sio.disconnect()
            
            logger.info("✅ Scanner parado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao parar scanner: {e}")
    
    async def _test_supabase_connection(self):
        """Testa conexão com Supabase."""
        try:
            logger.info("🔍 Testando conexão com Supabase...")
            await self.supabase.test_connection()
            logger.info("✅ Conexão com Supabase OK")
        except Exception as e:
            logger.error(f"❌ Falha na conexão com Supabase: {e}")
            raise
    
    async def _connect_websocket(self):
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            logger.info("🔄 Tentando conectar ao WebSocket...")
            
            # Obtém metadata
            metadata = await self._get_socket_metadata()
            if not metadata:
                raise Exception("Falha ao obter metadata")
            
            # Configura credenciais
            self.user_id = metadata.get('user', {}).get('id')
            self.socket_token = metadata.get('socket_token')
            self.socket_signature = metadata.get('socket_signature') or metadata.get('token_signature')
            self.user_model = metadata.get('user')
            
            if not all([self.user_id, self.socket_token, self.socket_signature, self.user_model]):
                raise Exception("Credenciais incompletas")
            
            logger.info("✅ Metadata obtida com sucesso")
            
            # Conecta ao WebSocket
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Origin': 'https://trade.csgoempire.com',
                'Referer': 'https://trade.csgoempire.com/'
            }
            
            qs = f"uid={self.user_id}&token={self.socket_token}"
            await self.sio.connect(
                f"https://trade.csgoempire.com/?{qs}",
                socketio_path='s/',
                headers=headers,
                transports=['websocket'],
                namespaces=['/trade']
            )
            
            logger.info("🔌 Conectado ao namespace /trade")
            self.is_connected = True
            
            # Aguarda autenticação
            await self._wait_for_authentication()
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            raise
    
    async def _get_socket_metadata(self) -> Optional[Dict]:
        """Obtém metadata para conexão WebSocket."""
        try:
            headers = {
                "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get("https://csgoempire.com/api/v2/metadata/socket", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('data') or data
                    else:
                        logger.error(f"❌ Erro ao obter metadata: {resp.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadata: {e}")
            return None
    
    async def _wait_for_authentication(self):
        """Aguarda autenticação do WebSocket."""
        try:
            logger.info("⏳ Aguardando autenticação...")
            
            # Timeout de 30 segundos
            for i in range(30):
                if self.authenticated:
                    break
                await asyncio.sleep(1)
                if i % 5 == 0:
                    logger.info(f"⏳ Aguardando autenticação... ({i}s)")
            
            if not self.authenticated:
                raise Exception("Timeout na autenticação")
            
            logger.info("✅ Autenticação confirmada!")
            
        except Exception as e:
            logger.error(f"❌ Falha na autenticação: {e}")
            raise
    
    def _setup_websocket_handlers(self):
        """Configura handlers do WebSocket."""
        
        @self.sio.event(namespace='/trade')
        async def connect():
            """Conectado ao WebSocket."""
            logger.info("🔌 WebSocket conectado ao namespace /trade")
            self.is_connected = True
            self._update_last_data_received()
        
        @self.sio.event(namespace='/trade')
        async def disconnect():
            """Desconectado do WebSocket."""
            logger.warning("🔌 WebSocket desconectado")
            self.is_connected = False
            self.authenticated = False
        
        @self.sio.on('init', namespace='/trade')
        async def on_init(data):
            """Evento de inicialização."""
            try:
                if isinstance(data, dict):
                    authenticated = data.get('authenticated', False)
                    if authenticated:
                        logger.info("✅ Usuário já autenticado, configurando filtros...")
                        
                        # Configura filtros
                        await self.sio.emit('filters', {
                            'price_min': int(self.settings.MIN_PRICE * 100 / self.settings.COIN_TO_USD_FACTOR),
                            'price_max': int(self.settings.MAX_PRICE * 100 / self.settings.COIN_TO_USD_FACTOR)
                        }, namespace='/trade')
                        logger.info("📤 Filtros básicos enviados")
                        
                        # Configura eventos permitidos
                        await self.sio.emit('allowedEvents', {
                            'events': ['new_item', 'updated_item', 'auction_update', 'auction_end', 'deleted_item', 'timesync', 'trade_status']
                        }, namespace='/trade')
                        logger.info("📤 Eventos permitidos configurados")
                        
                        # Inscreve em múltiplos canais
                        channels = ['auctions', 'trading', 'marketplace', 'items', 'live']
                        for channel in channels:
                            try:
                                await self.sio.emit('subscribe', {'room': channel}, namespace='/trade')
                                logger.info(f"📤 Inscrição no canal '{channel}' enviada")
                            except Exception as e:
                                logger.warning(f"⚠️ Falha ao inscrever no canal '{channel}': {e}")
                        
                        # Sincronização de tempo
                        await self.sio.emit('timesync', namespace='/trade')
                        logger.info("📤 Timesync solicitado")
                        
                        self.authenticated = True
                        self._update_last_data_received()
                        
                        logger.info("🔍 MONITORAMENTO ATIVO:")
                        logger.info("   - WebSocket: ✅ Conectado")
                        logger.info("   - Autenticação: ✅ Confirmada")
                        logger.info("   - Eventos: ✅ Permitidos")
                        logger.info("   - Canais: ✅ Inscritos")
                        logger.info("   - Filtros: ✅ Configurados")
                        logger.info("   - Status: 🎯 PRONTO PARA CAPTURAR ITENS!")
                        
                    else:
                        logger.warning(f"ℹ️ init sem authenticated=true - dados: {data}")
                        # Emite identify manualmente
                        await self._emit_identify()
                else:
                    logger.warning(f"⚠️ Dados inesperados para init: {type(data)} - {data}")
                    
            except Exception as e:
                logger.error(f"❌ Erro no handler init: {e}")
        
        @self.sio.on('new_item', namespace='/trade')
        async def on_new_item(data):
            """Novo item recebido."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                
                items_to_process = self._extract_items_from_event(data, 'new_item')
                if items_to_process:
                    logger.info(f"🆕 NOVOS ITENS RECEBIDOS: {len(items_to_process)} itens")
                    for item in items_to_process:
                        await self._process_item_optimized(item, 'new_item')
                else:
                    logger.debug(f"🆕 new_item recebido mas sem itens válidos: {type(data)}")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar new_item: {e}")
        
        @self.sio.on('updated_item', namespace='/trade')
        async def on_updated_item(data):
            """Item atualizado."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                
                items_to_process = self._extract_items_from_event(data, 'updated_item')
                if items_to_process:
                    logger.info(f"🔄 ITENS ATUALIZADOS: {len(items_to_process)} itens")
                    for item in items_to_process:
                        await self._process_item_optimized(item, 'updated_item')
                else:
                    logger.debug(f"🔄 updated_item recebido mas sem itens válidos: {type(data)}")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar updated_item: {e}")
        
        @self.sio.on('item_list', namespace='/trade')
        async def on_item_list(data):
            """Lista de itens."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                
                items_to_process = self._extract_items_from_event(data, 'item_list')
                if items_to_process:
                    logger.info(f"📋 LISTA DE ITENS: {len(items_to_process)} itens")
                    for item in items_to_process:
                        await self._process_item_optimized(item, 'item_list')
                else:
                    logger.debug(f"📋 item_list recebido mas sem itens válidos: {type(data)}")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar item_list: {e}")
        
        @self.sio.on('market_update', namespace='/trade')
        async def on_market_update(data):
            """Atualização de mercado."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                
                items_to_process = self._extract_items_from_event(data, 'market_update')
                if items_to_process:
                    logger.info(f"🏪 ATUALIZAÇÃO DE MERCADO: {len(items_to_process)} itens")
                    for item in items_to_process:
                        await self._process_item_optimized(item, 'market_update')
                else:
                    logger.debug(f"🏪 market_update recebido mas sem itens válidos: {type(data)}")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar market_update: {e}")
        
        @self.sio.on('deleted_item', namespace='/trade')
        async def on_deleted_item(data):
            """Item removido."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                
                # Log reduzido para deleted_item
                if isinstance(data, list) and len(data) > 5:
                    logger.info(f"🗑️ {len(data)} itens removidos do marketplace")
                else:
                    logger.debug(f"🗑️ {len(data)} itens removidos")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar deleted_item: {e}")
        
        @self.sio.on('auction_update', namespace='/trade')
        async def on_auction_update(data):
            """Atualização de leilão."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                logger.debug(f"🏷️ Atualização de leilão recebida")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar auction_update: {e}")
        
        @self.sio.on('auction_end', namespace='/trade')
        async def on_auction_end(data):
            """Fim de leilão."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                logger.debug(f"🏁 Leilão finalizado")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar auction_end: {e}")
        
        @self.sio.on('trade_status', namespace='/trade')
        async def on_trade_status(data):
            """Status de trade."""
            try:
                self.stats['websocket_events'] += 1
                self._update_last_data_received()
                logger.debug(f"📊 Status de trade recebido")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao processar trade_status: {e}")
        
        @self.sio.on('timesync', namespace='/trade')
        async def on_timesync(data):
            """Sincronização de tempo."""
            logger.debug(f"⏰ Timesync recebido")
            self._update_last_data_received()
        
        @self.sio.on('error', namespace='/trade')
        async def on_error(data):
            """Erro do servidor."""
            logger.error(f"❌ Erro do servidor WebSocket: {data}")
        
        @self.sio.on('connect_error', namespace='/trade')
        async def on_connect_error(data):
            """Erro de conexão."""
            logger.error(f"❌ Erro de conexão WebSocket: {data}")
        
        # Handler genérico para capturar eventos não tratados
        @self.sio.on('*', namespace='/trade')
        async def catch_all(event_name, data):
            """Captura todos os eventos para debug."""
            try:
                if isinstance(event_name, str):
                    event_name = event_name.lower()
                else:
                    event_name = str(event_name).lower()
                
                # Log apenas para eventos importantes ou desconhecidos
                if event_name in ['updated_seller_online_status']:
                    # Log reduzido para eventos de ruído
                    if isinstance(data, list) and len(data) > 100:
                        logger.debug(f"📨 Evento não tratado: {event_name} - Lista com {len(data)} itens")
                    else:
                        logger.debug(f"📨 Evento não tratado: {event_name} - {type(data)}")
                else:
                    # Log para eventos desconhecidos
                    logger.info(f"📨 Evento não tratado: {event_name} - {type(data)}")
                    if isinstance(data, list):
                        logger.info(f"   Primeiro item: {data[0] if data else 'N/A'} (ID: {data[0].get('id', 'Unknown') if data and isinstance(data[0], dict) else 'Unknown'})")
                    elif isinstance(data, dict):
                        logger.info(f"   Dados: {data}")
                
                self._update_last_data_received()
                
            except Exception as e:
                logger.error(f"❌ Erro no handler genérico: {e}")
    
    async def _emit_identify(self):
        """Emite evento identify manualmente."""
        try:
            logger.info("🔄 Tentando autenticação manual após 10s...")
            await asyncio.sleep(10)
            
            logger.info("🔐 Iniciando autenticação WebSocket...")
            identify_data = {
                'uid': self.user_id,
                'model': self.user_model,
                'authorizationToken': self.socket_token,
                'signature': self.socket_signature,
                'uuid': str(uuid.uuid4())
            }
            
            await self.sio.emit('identify', identify_data, namespace='/trade')
            logger.info("📤 Evento identify emitido com sucesso")
            
            logger.info("⏳ Identify enviado, aguardando autenticação...")
            
        except Exception as e:
            logger.error(f"❌ Erro ao emitir identify: {e}")
    
    def _extract_items_from_event(self, data, event_type: str) -> List[Dict]:
        """Extrai itens válidos de um evento WebSocket."""
        items = []
        
        try:
            if isinstance(data, list):
                # Lista direta de itens
                for item in data:
                    if isinstance(item, dict) and 'id' in item:
                        items.append(item)
                # Se não encontrou itens válidos, pode ser formato [event_type, data]
                if not items and len(data) >= 2:
                    payload = data[1]
                    if isinstance(payload, list):
                        for item in payload:
                            if isinstance(item, dict) and 'id' in item:
                                items.append(item)
                    elif isinstance(payload, dict) and 'id' in payload:
                        items.append(payload)
            elif isinstance(data, dict):
                # Item único ou payload com data
                if 'id' in data:
                    items.append(data)
                elif 'data' in data:
                    payload = data['data']
                    if isinstance(payload, list):
                        for item in payload:
                            if isinstance(item, dict) and 'id' in item:
                                items.append(item)
                    elif isinstance(payload, dict) and 'id' in payload:
                        items.append(payload)
            
            # Filtra itens já processados recentemente
            current_time = time.time()
            filtered_items = []
            for item in items:
                item_id = str(item.get('id'))
                if item_id not in self.processed_items:
                    filtered_items.append(item)
                    # Adiciona ao cache de processados
                    self.processed_items.add(item_id)
                    # Agenda remoção do cache
                    asyncio.create_task(self._remove_from_processed_cache(item_id))
            
            return filtered_items
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair itens do evento {event_type}: {e}")
            return []
    
    async def _remove_from_processed_cache(self, item_id: str):
        """Remove item do cache de processados após TTL."""
        try:
            await asyncio.sleep(self.cache_ttl)
            self.processed_items.discard(item_id)
        except Exception:
            pass
    
    async def _process_item_optimized(self, item: Dict, event_type: str):
        """Processa um item de forma otimizada."""
        try:
            self.stats['items_received'] += 1
            
            # Extrai dados básicos
            item_data = self._extract_item_data(item)
            if not item_data:
                return
            
            # Verifica filtro de preço básico ANTES de enriquecer com database
            if not self._check_basic_price_filter(item_data):
                logger.debug(f"Item {item_data.get('name')} rejeitado pelo filtro de preço básico: ${item_data.get('price', 0):.2f}")
                return
            
            # Enriquece com dados da database
            enriched_data = await self._enrich_item_data(item_data)
            if not enriched_data:
                return
            
            # Aplica filtros de oportunidade
            if await self._check_filters(enriched_data):
                # OPORTUNIDADE ENCONTRADA!
                await self._handle_opportunity(enriched_data, event_type)
            
            self.stats['items_processed'] += 1
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
    
    def _extract_item_data(self, item: Dict) -> Optional[Dict]:
        """Extrai dados básicos do item."""
        try:
            item_id = item.get('id')
            if not item_id:
                return None
            
            # Nome do item
            market_name = item.get('market_name', item.get('name', 'Unknown'))
            if not market_name or market_name == 'Unknown':
                return None
            
            # Preço em centavos
            purchase_price = item.get('purchase_price', 0)
            if not purchase_price or purchase_price <= 0:
                return None
            
            # Converte centavos para USD
            price_usd = (purchase_price / 100) * self.settings.COIN_TO_USD_FACTOR
            
            # Parse do nome para extrair componentes
            base_name, is_stattrak, is_souvenir, condition = self._parse_market_hash_name(market_name)
            
            # Dados básicos
            item_data = {
                'id': item_id,
                'name': market_name,
                'price': price_usd,
                'price_csgoempire_coin': purchase_price,
                'base_name': base_name,
                'is_stattrak': is_stattrak,
                'is_souvenir': is_souvenir,
                'condition': condition,
                'type': item.get('type', 'Unknown'),
                'float_value': item.get('float_value'),
                'wear': item.get('wear'),
                'icon_url': item.get('icon_url'),
                'auction_ends_at': item.get('auction_ends_at'),
                'auction_highest_bid': item.get('auction_highest_bid'),
                'auction_number_of_bids': item.get('auction_number_of_bids', 0),
                'suggested_price_csgoempire': item.get('suggested_price', 0)
            }
            
            logger.debug(f"💰 Item: {market_name}")
            logger.debug(f"   - Preço CSGOEmpire: {purchase_price} centavos = ${price_usd:.2f}")
            logger.debug(f"   - Base: {base_name}")
            logger.debug(f"   - StatTrak: {is_stattrak}")
            logger.debug(f"   - Souvenir: {is_souvenir}")
            logger.debug(f"   - Condição: {condition}")
            
            return item_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados do item: {e}")
            return None
    
    def _parse_market_hash_name(self, market_name: str) -> tuple:
        """Parse do nome do item para extrair componentes."""
        try:
            if not market_name:
                return "", False, False, ""
            
            s = market_name.strip()
            
            # Verifica StatTrak
            is_stattrak = ("StatTrak™" in s) or ("StatTrak" in s)
            if is_stattrak:
                s = s.replace("StatTrak™ ", "").replace("StatTrak ", "")
            
            # Verifica Souvenir
            is_souvenir = "Souvenir" in s
            if is_souvenir:
                s = s.replace("Souvenir ", "")
            
            # Extrai condição
            condition = ""
            for c in ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]:
                suffix = f"({c})"
                if s.endswith(suffix):
                    condition = c
                    s = s[:-len(suffix)].strip()
                    break
            
            # Nome base
            base_name = s.strip()
            
            return base_name, is_stattrak, is_souvenir, condition
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse do nome: {e}")
            return market_name, False, False, ""
    
    def _check_basic_price_filter(self, item: Dict) -> bool:
        """Filtro de preço básico aplicado antes de enriquecer com database."""
        try:
            price_usd = item.get('price')
            if price_usd is None:
                logger.debug(f"Item {item.get('name')} sem preço, rejeitando")
                return False
            
            # Filtros de preço configurados
            min_price = self.settings.MIN_PRICE
            max_price = self.settings.MAX_PRICE
            
            # Verifica preço mínimo
            if price_usd < min_price:
                logger.debug(f"Item {item.get('name')} rejeitado: ${price_usd:.2f} < ${min_price:.2f} (MIN_PRICE)")
                return False
            
            # Verifica preço máximo
            if price_usd > max_price:
                logger.debug(f"Item {item.get('name')} rejeitado: ${price_usd:.2f} > ${max_price:.2f} (MAX_PRICE)")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar filtro de preço básico: {e}")
            return False
    
    async def _enrich_item_data(self, item: Dict) -> Optional[Dict]:
        """Enriquece dados do item com informações da database."""
        try:
            base_name = item.get('base_name')
            is_stattrak = item.get('is_stattrak', False)
            is_souvenir = item.get('is_souvenir', False)
            condition = item.get('condition', '')
            
            if not base_name:
                logger.warning(f"Item {item.get('name')} sem base_name")
                return None
            
            # Busca preço Buff163
            price_buff163 = await self.supabase.get_buff163_price_advanced(
                base_name, is_stattrak, is_souvenir, condition
            )
            
            if price_buff163:
                item['price_buff163'] = price_buff163
                logger.info(f"💰 Preço Buff163 encontrado: ${price_buff163:.2f}")
            else:
                logger.debug(f"Preço Buff163 não encontrado para {item.get('name')}")
                return None
            
            # Busca score de liquidez
            liquidity_score = await self.supabase.get_liquidity_score_advanced(
                base_name, is_stattrak, is_souvenir, condition
            )
            
            if liquidity_score is not None:
                item['liquidity_score'] = liquidity_score
                logger.info(f"💧 Score de liquidez encontrado: {liquidity_score:.1f}")
            else:
                logger.debug(f"Score de liquidez não encontrado para {item.get('name')}")
                return None
            
            return item
            
        except Exception as e:
            logger.error(f"❌ Erro ao enriquecer dados do item: {e}")
            return None
    
    async def _check_filters(self, item: Dict) -> bool:
        """Verifica se o item passa em todos os filtros."""
        try:
            # Filtro de liquidez
            liquidity_result = await self.liquidity_filter.check(item)
            if not liquidity_result:
                logger.debug(f"Item {item.get('name')} rejeitado pelo filtro de liquidez")
                return False
            
            # Filtro de lucro
            profit_result = await self.profit_filter.check(item)
            if not profit_result:
                logger.debug(f"Item {item.get('name')} rejeitado pelo filtro de lucro")
                return False
            
            logger.info(f"✅ Item {item.get('name')} passou em todos os filtros!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar filtros: {e}")
            return False
    
    async def _handle_opportunity(self, item: Dict, event_type: str):
        """Processa oportunidade encontrada."""
        try:
            self.stats['opportunities_found'] += 1
            self.stats['last_opportunity'] = time.time()
            
            logger.info(f"🎉 === OPORTUNIDADE ENCONTRADA! ===")
            logger.info(f"🏆 Item: {item.get('name', 'Unknown')}")
            logger.info(f"💰 Preço CSGOEmpire: ${item.get('price', 0):.2f}")
            logger.info(f"💵 Preço Buff163: ${item.get('price_buff163', 0):.2f}")
            logger.info(f"💧 Liquidez: {item.get('liquidity_score', 0):.1f}")
            
            # Calcula lucro
            price_csgoempire = item.get('price', 0)
            price_buff163 = item.get('price_buff163', 0)
            if price_csgoempire > 0 and price_buff163 > 0:
                profit_usd = price_buff163 - price_csgoempire
                profit_percentage = (profit_usd / price_csgoempire) * 100
                item['profit_usd'] = profit_usd
                item['profit_percentage'] = profit_percentage
                
                logger.info(f"📈 Lucro: ${profit_usd:.2f} ({profit_percentage:.2f}%)")
            
            # Envia para Discord
            try:
                await self.discord_poster.post_opportunity(item)
                logger.info(f"✅ Oportunidade enviada para Discord com sucesso!")
            except Exception as e:
                logger.error(f"❌ Erro ao enviar para Discord: {e}")
            
            # Chama callback se configurado
            if self.opportunity_callback:
                try:
                    await self.opportunity_callback(item, 'csgoempire')
                except Exception as e:
                    logger.error(f"❌ Erro no callback de oportunidade: {e}")
            
            logger.info(f"🎉 === FIM OPORTUNIDADE ===")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar oportunidade: {e}")
    
    def _update_last_data_received(self):
        """Atualiza timestamp do último dado recebido."""
        self._last_data_received = time.time()
        if self.authenticated:
            self._last_stable_connection = time.time()
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do scanner."""
        return {
            'running': self.running,
            'authenticated': self.authenticated,
            'websocket_connected': self.is_connected,
            'items_received': self.stats['items_received'],
            'items_processed': self.stats['items_processed'],
            'opportunities_found': self.stats['opportunities_found'],
            'websocket_events': self.stats['websocket_events'],
            'last_opportunity': self.stats['last_opportunity'],
            'last_data_received': self._last_data_received,
            'last_stable_connection': self._last_stable_connection,
            'processed_items_cache_size': len(self.processed_items)
        }
