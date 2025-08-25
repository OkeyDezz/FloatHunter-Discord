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
from typing import Dict, Optional, List
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
        
        # Controle de duplicatas - evita processar o mesmo item múltiplas vezes
        self.processed_items = set()
        self.max_processed_items = 1000  # Mantém apenas os últimos 1000 itens processados
        
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
                        item_id = item.get('id', 'Unknown')
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
                
                # Se for erro de autenticação, marca como não autenticado
                if isinstance(data, dict):
                    error_msg = data.get('error', '').lower()
                    if 'identify failed' in error_msg or 'authentication' in error_msg:
                        logger.error("❌ Falha na autenticação - marcando como não autenticado")
                        self.authenticated = False
                        # Tenta reconectar
                        asyncio.create_task(self._reconnect_websocket())
            
            # Handler para eventos de autenticação
            @self.sio.on('init', namespace='/trade')
            async def on_init(data):
                """Evento de inicialização/autenticação."""
                try:
                    logger.info(f"📡 Evento init recebido: {data}")
                    
                    if isinstance(data, dict):
                        auth_status = data.get('authenticated', False)
                        if auth_status:
                            logger.info("✅ Autenticação confirmada pelo servidor")
                            self.authenticated = True
                        else:
                            logger.warning("⚠️ Servidor indica que não está autenticado")
                            self.authenticated = False
                    else:
                        logger.info(f"📡 Evento init recebido (tipo: {type(data)})")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar evento init: {e}")
            
            # Handler para eventos de autenticação
            @self.sio.on('auth', namespace='/trade')
            async def on_auth(data):
                """Evento de resposta de autenticação."""
                try:
                    logger.info(f"📡 Evento auth recebido: {data}")
                    
                    if isinstance(data, dict):
                        auth_status = data.get('authenticated', False)
                        if auth_status:
                            logger.info("✅ Autenticação confirmada pelo comando auth")
                            self.authenticated = True
                        else:
                            logger.warning("⚠️ Comando auth falhou")
                            self.authenticated = False
                    else:
                        logger.info(f"📡 Evento auth recebido (tipo: {type(data)})")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar evento auth: {e}")
            
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
            if self.sio.connected and self.authenticated:
                logger.info("✅ WebSocket já está conectado e autenticado")
                return True
            
            # Se já está conectado mas não autenticado, não reconecta
            if self.sio.connected and not self.authenticated:
                logger.info("🔌 WebSocket já conectado, aguardando autenticação...")
                return True
            
            if not all([self.user_id, self.socket_token, self.socket_signature]):
                logger.error("❌ Dados de autenticação incompletos")
                return False
            
            # URL e parâmetros conforme documentação oficial
            # CSGOEmpire usa EIO=3 e o endpoint correto é wss://trade.csgoempire.com/s/
            base_url = "wss://trade.csgoempire.com"
            
            logger.info(f"🔌 Conectando ao WebSocket CSGOEmpire...")
            logger.info(f"   - URL base: {base_url}")
            logger.info(f"   - User ID: {self.user_id}")
            logger.info(f"   - Token: {self.socket_token[:20]}...")
            
            # Conecta usando a documentação oficial do CSGOEmpire
            await self.sio.connect(
                base_url,
                socketio_path='/s/',
                transports=['websocket'],
                headers={
                    'User-Agent': f'{self.user_id} API Bot'
                },
                auth={
                    'uid': self.user_id,
                    'token': self.socket_token
                },
                namespaces=['/trade']
            )
            
            logger.info("🔌 WebSocket conectado ao namespace /trade")
            
            # Aguarda estabilizar
            await asyncio.sleep(2)
            
            if not self.sio.connected:
                logger.error("❌ WebSocket desconectado após conexão")
                return False
            
            # NÃO marca como conectado ainda - aguarda autenticação
            logger.info("🔌 WebSocket conectado, aguardando autenticação...")
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
            
            # Emite identify conforme documentação oficial do CSGOEmpire
            logger.info("🆔 Emitindo identify para autenticação...")
            logger.info(f"   - User ID: {self.user_id}")
            logger.info(f"   - Token: {self.socket_token[:20]}...")
            logger.info(f"   - Signature: {self.socket_signature[:20]}...")
            
            # Formato conforme documentação oficial do CSGOEmpire
            identify_data = {
                'uid': self.user_id,
                'model': self.user_model,
                'authorizationToken': self.socket_token,
                'signature': self.socket_signature
            }
            
            logger.info("🆔 Enviando comando identify...")
            await self.sio.emit('identify', identify_data, namespace='/trade')
            
            # Aguarda autenticação
            logger.info("⏳ Aguardando autenticação...")
            await asyncio.sleep(3)
            
            # Configura filtros conforme documentação oficial do CSGOEmpire
            logger.info("📤 Configurando filtros de preço...")
            
            # Converte preços USD para centavos (formato esperado pela API)
            price_min_centavos = int(self.settings.MIN_PRICE / self.settings.COIN_TO_USD_FACTOR * 100)
            price_max_centavos = int(self.settings.MAX_PRICE / self.settings.COIN_TO_USD_FACTOR * 100)
            
            filters_data = {
                'price_max': price_max_centavos  # CSGOEmpire usa centavos
            }
            
            logger.info(f"📤 Filtro de preço: máximo {price_max_centavos} centavos (${self.settings.MAX_PRICE:.2f})")
            await self.sio.emit('filters', filters_data, namespace='/trade')
            logger.info("📤 Filtros configurados com sucesso")
            
            # NÃO marca como autenticado aqui - aguarda confirmação do servidor
            logger.info("⏳ Aguardando confirmação de autenticação do servidor...")
            logger.info("⏳ Aguardando evento 'init' com authenticated=true...")
            
            # Log de configuração
            logger.info("🔍 Configuração do WebSocket concluída:")
            logger.info("   - Filtros de preço: $%.2f - $%.2f" % (self.settings.MIN_PRICE, self.settings.MAX_PRICE))
            logger.info("   - Evento único: new_item")
            logger.info("   - Aguardando confirmação de autenticação...")
            
            logger.info("🔍 MONITORAMENTO ATIVO:")
            logger.info("   - WebSocket: ✅ Conectado")
            logger.info("   - Autenticação: ⏳ Aguardando confirmação")
            logger.info("   - Evento: ✅ new_item")
            logger.info("   - Filtros: ✅ Configurados")
            logger.info("   - Status: 🔄 AGUARDANDO AUTENTICAÇÃO DO SERVIDOR")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar WebSocket: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _reconnect_websocket(self):
        """Reconecta ao WebSocket após falha de autenticação."""
        try:
            logger.info("🔄 Reconectando WebSocket após falha de autenticação...")
            
            # Desconecta atual
            if self.sio.connected:
                await self.sio.disconnect()
                logger.info("🔌 WebSocket desconectado para reconexão")
            
            # Aguarda um pouco
            await asyncio.sleep(5)
            
            # Reconecta
            if await self._connect_websocket():
                logger.info("✅ Reconexão bem-sucedida")
                # Reconfigura
                await self._configure_websocket()
            else:
                logger.error("❌ Falha na reconexão")
                
        except Exception as e:
            logger.error(f"❌ Erro durante reconexão: {e}")
    
    async def _wait_for_authentication(self, timeout_seconds: int = 30) -> bool:
        """Aguarda autenticação ser confirmada pelo servidor."""
        try:
            logger.info(f"⏳ Aguardando autenticação (timeout: {timeout_seconds}s)...")
            
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                if self.authenticated:
                    logger.info("✅ Autenticação confirmada pelo servidor!")
                    return True
                
                await asyncio.sleep(1)
            
            logger.warning(f"⚠️ Timeout de autenticação ({timeout_seconds}s) - não autenticado")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao aguardar autenticação: {e}")
            return False
    
    def _is_item_already_processed(self, item_id: str) -> bool:
        """Verifica se o item já foi processado para evitar duplicatas."""
        return item_id in self.processed_items
    
    def _mark_item_as_processed(self, item_id: str) -> None:
        """Marca um item como processado e limpa itens antigos se necessário."""
        self.processed_items.add(item_id)
        
        # Limpa itens antigos se exceder o limite
        if len(self.processed_items) > self.max_processed_items:
            # Remove os itens mais antigos (mantém apenas os últimos 1000)
            items_to_remove = len(self.processed_items) - self.max_processed_items
            items_list = list(self.processed_items)
            for i in range(items_to_remove):
                self.processed_items.remove(items_list[i])
            logger.debug(f"🧹 Limpeza de cache: {items_to_remove} itens antigos removidos")
    
    async def _process_item(self, item: Dict, event_type: str) -> None:
        """Processa um item recebido."""
        try:
            # Verifica se o item já foi processado
            item_id = str(item.get('id', ''))
            if not item_id:
                logger.warning("⚠️ Item sem ID, ignorando")
                return
            
            if self._is_item_already_processed(item_id):
                logger.info(f"🔄 Item já processado anteriormente: {item_id} - ignorando duplicata")
                return
            
            # Filtro básico de preço (ultra-rápido)
            if not self._check_basic_price_filter(item):
                self._mark_item_as_processed(item_id)  # Marca como processado mesmo que rejeitado
                return
            
            # Extrai dados básicos
            extracted_item = self._extract_item_data(item)
            if not extracted_item:
                self._mark_item_as_processed(item_id)
                return
            
            # Enriquece com dados da database
            await self._enrich_item_data(extracted_item)
            
            # Aplica filtros de oportunidade
            if await self._apply_opportunity_filters(extracted_item):
                logger.info(f"🎯 OPORTUNIDADE ENCONTRADA: {extracted_item.get('name')}")
                await self.discord_poster.post_opportunity(extracted_item)
            
            # Marca como processado após todo o processamento
            self._mark_item_as_processed(item_id)
            logger.info(f"✅ Item processado com sucesso: {item_id} (Total processados: {len(self.processed_items)})")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Marca como processado mesmo em caso de erro para evitar loops infinitos
            if item_id:
                self._mark_item_as_processed(item_id)
    
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
    
    async def _get_items_via_api(self) -> List[Dict]:
        """Busca itens via API REST como alternativa ao WebSocket."""
        try:
            logger.info("🔍 Buscando itens via API REST...")
            
            # Endpoint para buscar itens disponíveis
            url = "https://csgoempire.com/api/v2/trading/items"
            headers = {
                "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            
            params = {
                "limit": 100,  # Busca até 100 itens
                "offset": 0
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('data', [])
                        logger.info(f"✅ API retornou {len(items)} itens")
                        return items
                    else:
                        logger.error(f"❌ Erro na API: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens via API: {e}")
            return []
    
    async def _scan_items_via_api(self):
        """Scanner alternativo usando API REST."""
        try:
            logger.info("🔍 Iniciando scanner via API REST...")
            
            while True:
                try:
                    # Busca itens via API
                    items = await self._get_items_via_api()
                    
                    if items:
                        logger.info(f"📋 Processando {len(items)} itens...")
                        
                        for item in items:
                            try:
                                # Processa cada item
                                await self._process_item(item, 'api_scan')
                            except Exception as e:
                                logger.error(f"❌ Erro ao processar item: {e}")
                                continue
                    else:
                        logger.info("📋 Nenhum item encontrado via API")
                    
                    # Aguarda antes da próxima busca
                    logger.info("⏳ Aguardando 30 segundos para próxima busca...")
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Erro no loop de scanner API: {e}")
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("🛑 Scanner API cancelado")
        except Exception as e:
            logger.error(f"❌ Erro fatal no scanner API: {e}")
    
    async def start(self):
        """Inicia o scanner."""
        try:
            logger.info("🚀 Iniciando scanner de marketplace...")
            
            # Obtém metadata para WebSocket
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
            
            # Configura o WebSocket após conexão
            await self._configure_websocket()
            
            # Aguarda autenticação ser confirmada pelo servidor
            if not await self._wait_for_authentication(timeout_seconds=30):
                logger.warning("⚠️ Autenticação não confirmada pelo servidor")
                return False
            
            logger.info("✅ Scanner iniciado e autenticado com sucesso!")
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
                        logger.info("✅ Scanner conectado e autenticado, aguardando oportunidades...")
                        
                        # Loop de monitoramento do WebSocket
                        while True:
                            if not self.sio.connected:
                                logger.warning("⚠️ WebSocket desconectado, tentando reconectar...")
                                break
                            
                            if not self.authenticated:
                                logger.warning("⚠️ WebSocket conectado mas não autenticado, tentando reautenticar...")
                                # Tenta reautenticar sem desconectar
                                await self._configure_websocket()
                                if await self._wait_for_authentication(timeout_seconds=15):
                                    logger.info("✅ Reautenticação bem-sucedida!")
                                    continue
                                else:
                                    logger.warning("⚠️ Reautenticação falhou, reconectando...")
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
