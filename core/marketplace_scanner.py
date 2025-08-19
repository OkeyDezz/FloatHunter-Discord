"""
Scanner simples e direto para o CSGOEmpire usando WebSocket.
Baseado na documentação oficial: https://docs.csgoempire.com/
"""
import asyncio
import logging
import socketio
import aiohttp
import time
import uuid
from typing import Dict, Optional
from datetime import datetime

from config.settings import Settings
from utils.supabase_client import SupabaseClient
from core.discord_poster import DiscordPoster

logger = logging.getLogger(__name__)

class MarketplaceScanner:
    """
    Scanner simples para o CSGOEmpire usando WebSocket.
    Foca apenas em eventos 'new_item' conforme solicitado.
    """
    
    def __init__(self):
        self.settings = Settings()
        self.supabase = SupabaseClient()
        self.discord_poster = DiscordPoster()
        
        # Socket.IO client
        self.sio = socketio.AsyncClient()
        
        # Estado da conexão
        self.is_connected = False
        self.authenticated = False
        self.reconnect_attempts = 0
        
        # Dados de autenticação
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        self.user_model = None
        
        # Log das configurações
        logger.info("🔧 Configurações carregadas:")
        logger.info(f"   - Preço: ${self.settings.MIN_PRICE:.2f} - ${self.settings.MAX_PRICE:.2f}")
        logger.info(f"   - Lucro mínimo: {self.settings.MIN_PROFIT_PERCENTAGE:.1f}%")
        logger.info(f"   - Liquidez mínima: {self.settings.MIN_LIQUIDITY_SCORE:.1f}")
        logger.info(f"   - Fator conversão: {self.settings.COIN_TO_USD_FACTOR}")
        
        # Configura eventos
        self._setup_socket_events()
    
    def _setup_socket_events(self):
        """Configura os handlers de eventos do WebSocket."""
        try:
            logger.info("🔧 Configurando handlers de eventos...")
            
            # Handler de conexão
            @self.sio.event(namespace='/trade')
            async def connect():
                """Conectado ao namespace /trade."""
                logger.info("🔌 Conectado ao namespace /trade")
                self.is_connected = True
                self.authenticated = False
                
                # Configura automaticamente após conectar
                await self._configure_websocket()
            
            # Handler de desconexão
            @self.sio.event(namespace='/trade')
            async def disconnect():
                """Desconectado do namespace /trade."""
                logger.info("🔌 Desconectado do namespace /trade")
                self.is_connected = False
                self.authenticated = False
            
            # Handler de erro
            @self.sio.event(namespace='/trade')
            async def connect_error(data):
                """Erro de conexão."""
                logger.error(f"❌ Erro de conexão WebSocket: {data}")
                self.is_connected = False
                self.authenticated = False
            
            # Handler ESSENCIAL: apenas new_item
            @self.sio.on('new_item', namespace='/trade')
            async def on_new_item(data):
                """Novo item disponível - APENAS este evento."""
                try:
                    logger.info(f"🆕 NOVO ITEM RECEBIDO: {type(data)}")
                    
                    if isinstance(data, list):
                        logger.info(f"📋 Lista com {len(data)} itens")
                        for i, item in enumerate(data):
                            if isinstance(item, dict):
                                item_name = item.get('market_name', item.get('name', f'Item {i+1}'))
                                item_id = item.get('id', 'Unknown')
                                logger.info(f"   🆕 {i+1}. {item_name} (ID: {item_id})")
                                await self._process_item(item, 'new_item')
                    elif isinstance(data, dict):
                        logger.info(f"📋 Item único recebido")
                        item_name = data.get('market_name', data.get('name', 'Unknown'))
                        item_id = data.get('id', 'Unknown')
                        logger.info(f"   🆕 {item_name} (ID: {item_id})")
                        await self._process_item(data, 'new_item')
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar new_item: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Handler para erros do servidor
            @self.sio.on('err', namespace='/trade')
            async def on_error(data):
                """Erro do servidor WebSocket."""
                logger.warning(f"⚠️ Erro do servidor WebSocket: {data}")
            
            logger.info("✅ Handlers de eventos configurados")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar eventos: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _get_socket_metadata(self) -> bool:
        """Obtém metadata para autenticação do WebSocket."""
        try:
            if not self.settings.CSGOEMPIRE_API_KEY:
                logger.error("❌ API key do CSGOEmpire não configurada")
                return False
            
            # Endpoint conforme documentação oficial
            url = "https://csgoempire.com/api/v2/metadata/socket"
            headers = {
                "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            
            async with aiohttp.ClientSession() as session:
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
                            logger.error("❌ Dados de autenticação incompletos")
                            return False
                    else:
                        logger.error(f"❌ Erro ao obter metadata: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadata: {e}")
            return False
    
    async def _connect_websocket(self) -> bool:
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            if self.sio.connected:
                logger.info("✅ WebSocket já está conectado")
                return True
            
            if not all([self.user_id, self.socket_token, self.socket_signature]):
                logger.error("❌ Dados de autenticação incompletos")
                return False
            
            # Query string conforme documentação oficial
            qs = f"uid={self.user_id}&token={self.socket_token}"
            
            logger.info(f"🔌 Conectando ao WebSocket: trade.csgoempire.com/?{qs}")
            
            # Conecta usando a documentação oficial
            await self.sio.connect(
                f"https://trade.csgoempire.com/?{qs}",
                socketio_path='s/',
                transports=['websocket'],
                namespaces=['/trade']
            )
            
            logger.info("🔌 WebSocket conectado ao namespace /trade")
            
            # Aguarda estabilizar
            await asyncio.sleep(2)
            
            if not self.sio.connected:
                logger.error("❌ WebSocket desconectado após conexão")
                return False
            
            logger.info("✅ WebSocket conectado com sucesso")
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            return False
    
    async def _configure_websocket(self):
        """Configura o WebSocket após conexão."""
        try:
            logger.info("🔧 Configurando WebSocket após conexão...")
            
            # Aguarda estabilizar
            await asyncio.sleep(1)
            
            # Emite identify conforme documentação oficial
            logger.info("🆔 Emitindo identify para autenticação...")
            await self.sio.emit('identify', {
                'uid': self.user_id,
                'authorizationToken': self.socket_token,
                'signature': self.socket_signature,
                'uuid': str(uuid.uuid4())
            }, namespace='/trade')
            
            # Aguarda autenticação
            logger.info("⏳ Aguardando autenticação...")
            await asyncio.sleep(3)
            
            # Configura APENAS evento new_item
            logger.info("📤 Configurando APENAS evento new_item...")
            await self.sio.emit('allowedEvents', {
                'events': ['new_item']
            }, namespace='/trade')
            logger.info("📤 Evento permitido: new_item")
            
            # Configura filtros básicos
            logger.info("📤 Configurando filtros básicos...")
            await self.sio.emit('filters', {
                'price_min': self.settings.MIN_PRICE,
                'price_max': self.settings.MAX_PRICE
            }, namespace='/trade')
            logger.info("📤 Filtros configurados: preço apenas")
            
            # Marca como autenticado
            self.authenticated = True
            
            # Log de configuração
            logger.info("🔍 Configuração do WebSocket concluída:")
            logger.info("   - Filtros de preço: $%.2f - $%.2f" % (self.settings.MIN_PRICE, self.settings.MAX_PRICE))
            logger.info("   - Evento único: new_item")
            logger.info("   - Aguardando novos itens...")
            
            logger.info("🔍 MONITORAMENTO ATIVO:")
            logger.info("   - WebSocket: ✅ Conectado")
            logger.info("   - Autenticação: ✅ Confirmada")
            logger.info("   - Evento: ✅ new_item")
            logger.info("   - Filtros: ✅ Configurados")
            logger.info("   - Status: 🎯 PRONTO PARA CAPTURAR NOVOS ITENS!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar WebSocket: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _process_item(self, item: Dict, event_type: str) -> None:
        """Processa um item recebido."""
        try:
            # Filtro básico de preço (ultra-rápido)
            if not self._check_basic_price_filter(item):
                return
            
            # Extrai dados básicos
            extracted_item = self._extract_item_data(item)
            if not extracted_item:
                return
            
            # Enriquece com dados da database
            await self._enrich_item_data(extracted_item)
            
            # Aplica filtros de oportunidade
            if await self._apply_opportunity_filters(extracted_item):
                logger.info(f"🎯 OPORTUNIDADE ENCONTRADA: {extracted_item.get('name')}")
                await self.discord_poster.post_opportunity(extracted_item)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _check_basic_price_filter(self, item: Dict) -> bool:
        """Filtro básico de preço (ultra-rápido)."""
        try:
            purchase_price_centavos = item.get('purchase_price')
            if purchase_price_centavos is None:
                return False
            
            # Converte centavos para USD
            price_usd = (purchase_price_centavos / 100) * self.settings.COIN_TO_USD_FACTOR
            
            if price_usd < self.settings.MIN_PRICE:
                logger.debug(f"🚫 Item {item.get('market_name', 'Unknown')} REJEITADO: ${price_usd:.2f} < ${self.settings.MIN_PRICE:.2f}")
                return False
            
            if price_usd > self.settings.MAX_PRICE:
                logger.debug(f"🚫 Item {item.get('market_name', 'Unknown')} REJEITADO: ${price_usd:.2f} > ${self.settings.MAX_PRICE:.2f}")
                return False
            
            logger.debug(f"✅ Item {item.get('market_name', 'Unknown')} ACEITO no filtro de preço: ${price_usd:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no filtro de preço: {e}")
            return False
    
    def _extract_item_data(self, data: Dict) -> Optional[Dict]:
        """Extrai dados relevantes do item."""
        try:
            item_id = data.get('id')
            market_name = data.get('market_name')
            purchase_price = data.get('purchase_price')
            
            if not all([item_id, market_name, purchase_price]):
                return None
            
            # Parse do nome do item
            base_name, is_stattrak, is_souvenir, condition = self._parse_market_hash_name(market_name)
            
            # Converte preço de centavos para USD
            price_usd = (purchase_price / 100) * self.settings.COIN_TO_USD_FACTOR
            
            logger.info(f"💰 Item: {market_name}")
            logger.info(f"   - Base: {base_name}")
            logger.info(f"   - StatTrak: {is_stattrak}")
            logger.info(f"   - Souvenir: {is_souvenir}")
            logger.info(f"   - Condição: {condition}")
            logger.info(f"   - Preço CSGOEmpire: {purchase_price} centavos = ${price_usd:.2f}")
            
            return {
                'id': item_id,
                'name': market_name,
                'base_name': base_name,
                'is_stattrak': is_stattrak,
                'is_souvenir': is_souvenir,
                'condition': condition,
                'price': price_usd,
                'price_centavos': purchase_price,
                'marketplace': 'csgoempire',
                'detected_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados do item: {e}")
            return None
    
    def _parse_market_hash_name(self, name: str) -> tuple:
        """Parse do nome do item."""
        try:
            if not name:
                return "", False, False, None
            
            s = name.strip()
            stattrak = ("StatTrak™" in s) or ("StatTrak" in s)
            souvenir = ("Souvenir" in s)
            condition = None
            
            # Lista de condições
            conditions = [
                "Factory New", "Minimal Wear", "Field-Tested", 
                "Well-Worn", "Battle-Scarred"
            ]
            
            # Remove a condição do final
            for c in conditions:
                suffix = f"({c})"
                if s.endswith(suffix):
                    condition = c
                    s = s[:-len(suffix)].strip()
                    break
            
            # Remove flags do início
            base = (
                s.replace("StatTrak™ ", "")
                 .replace("StatTrak ", "")
                 .replace("Souvenir ", "")
                 .strip()
            )
            
            return base, stattrak, souvenir, condition
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse do nome: {e}")
            return name, False, False, None
    
    async def _enrich_item_data(self, item: Dict) -> None:
        """Enriquece o item com dados da database."""
        try:
            base_name = item.get('base_name')
            is_stattrak = item.get('is_stattrak', False)
            is_souvenir = item.get('is_souvenir', False)
            condition = item.get('condition')
            
            if not base_name:
                return
            
            logger.info(f"🔍 Enriquecendo item: {base_name}")
            
            # Busca preço Buff163
            price_buff163 = await self.supabase.get_buff163_price_advanced(
                base_name, is_stattrak, is_souvenir, condition
            )
            
            if price_buff163 is not None:
                item['price_buff163'] = price_buff163
                logger.info(f"💰 Preço Buff163 encontrado: ${price_buff163:.2f}")
            else:
                item['price_buff163'] = None
                logger.warning(f"⚠️ Preço Buff163 não encontrado para: {base_name}")
            
            # Busca score de liquidez
            liquidity_score = await self.supabase.get_liquidity_score_advanced(
                base_name, is_stattrak, is_souvenir, condition
            )
            
            if liquidity_score is not None:
                item['liquidity_score'] = liquidity_score
                logger.info(f"💧 Score de liquidez encontrado: {liquidity_score:.1f}")
            else:
                item['liquidity_score'] = None
                logger.warning(f"⚠️ Score de liquidez não encontrado para: {base_name}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao enriquecer item: {e}")
    
    async def _apply_opportunity_filters(self, item: Dict) -> bool:
        """Aplica filtros de oportunidade."""
        try:
            from filters.profit_filter import ProfitFilter
            from filters.liquidity_filter import LiquidityFilter
            
            # Filtro de lucro
            profit_filter = ProfitFilter(self.settings.MIN_PROFIT_PERCENTAGE)
            if not await profit_filter.check(item):
                logger.debug(f"❌ Item {item.get('name')} REJEITADO pelo filtro de lucro")
                return False
            
            # Filtro de liquidez
            liquidity_filter = LiquidityFilter(self.settings.MIN_LIQUIDITY_SCORE)
            if not await liquidity_filter.check(item):
                logger.debug(f"❌ Item {item.get('name')} REJEITADO pelo filtro de liquidez")
                return False
            
            logger.info(f"✅ Item {item.get('name')} ACEITO em todos os filtros")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar filtros: {e}")
            return False
    
    async def start(self):
        """Inicia o scanner."""
        try:
            logger.info("🚀 Iniciando scanner de marketplace...")
            
            # Obtém metadata
            if not await self._get_socket_metadata():
                logger.error("❌ Falha ao obter metadata")
                return False
            
            # Testa conexão com Supabase
            if not await self.supabase.test_connection():
                logger.error("❌ Falha na conexão com Supabase")
                return False
            
            # Conecta ao WebSocket
            if not await self._connect_websocket():
                logger.error("❌ Falha ao conectar ao WebSocket")
                return False
            
            logger.info("✅ Scanner iniciado com sucesso!")
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar scanner: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta do WebSocket."""
        try:
            if self.sio.connected:
                await self.sio.disconnect()
                logger.info("🔌 WebSocket desconectado")
            
            self.is_connected = False
            self.authenticated = False
            
        except Exception as e:
            logger.error(f"❌ Erro ao desconectar: {e}")
    
    async def run_forever(self):
        """Executa o scanner indefinidamente."""
        try:
            logger.info("🚀 Iniciando scanner de marketplace...")
            
            while True:
                try:
                    # Tenta conectar
                    if await self.start():
                        logger.info("✅ Scanner conectado, aguardando oportunidades...")
                        
                        # Loop de monitoramento
                        while True:
                            if not self.sio.connected or not self.authenticated:
                                logger.warning("⚠️ Conexão perdida, tentando reconectar...")
                                break
                            
                            await asyncio.sleep(30)
                        
                        # Aguarda antes de reconectar
                        await asyncio.sleep(10)
                        
                    else:
                        # Falha na conexão
                        if self.reconnect_attempts >= self.settings.WEBSOCKET_MAX_RECONNECT_ATTEMPTS:
                            logger.error("❌ Máximo de tentativas atingido, aguardando 5 minutos...")
                            await asyncio.sleep(300)
                            self.reconnect_attempts = 0
                        else:
                            logger.warning(f"⚠️ Tentativa {self.reconnect_attempts + 1}/{self.settings.WEBSOCKET_MAX_RECONNECT_ATTEMPTS} falhou")
                            await asyncio.sleep(30)
                            self.reconnect_attempts += 1
                            
                except Exception as e:
                    logger.error(f"❌ Erro no loop principal: {e}")
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("🛑 Scanner cancelado")
        except Exception as e:
            logger.error(f"❌ Erro fatal no scanner: {e}")
        finally:
            await self.disconnect()
