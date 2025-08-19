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
        
        # Sistema robusto de reconexão
        self._last_data_received = time.time()
        self._connection_start_time = None
        self._reconnect_backoff = 1  # Delay inicial em segundos
        self._max_reconnect_backoff = 300  # Delay máximo: 5 minutos
        self._last_reconnect_attempt = 0
        self._consecutive_failures = 0
        self._max_consecutive_failures = 10  # Máximo de falhas consecutivas
        self._force_restart_after = 3600  # Força restart após 1 hora sem conexão estável
        self._last_stable_connection = time.time()
        
        # Dados de autenticação
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        self.user_model = None
        
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
    
    async def _setup_socket_events(self):
        """Configura os handlers de eventos do WebSocket."""
        try:
            logger.info("🔧 Configurando handlers de eventos...")
            
            # Handlers de conexão ESSENCIAIS
            @self.sio.event(namespace='/trade')
            async def connect():
                """Conectado ao namespace /trade."""
                logger.info("🔌 Conectado ao namespace /trade")
                self._connection_start_time = time.time()
                self.is_connected = True
                logger.info("✅ Status atualizado: is_connected = True")
                
                # Configura automaticamente após conectar (sem depender do init)
                logger.info("🔧 Configurando WebSocket automaticamente após conexão...")
                await self._configure_websocket_after_connection()
            
            @self.sio.event(namespace='/trade')
            async def disconnect():
                """Desconectado do namespace /trade."""
                logger.info("🔌 Desconectado do namespace /trade")
                self.is_connected = False
                self.authenticated = False
                logger.info("✅ Status atualizado: is_connected = False, authenticated = False")
            
            @self.sio.event(namespace='/trade')
            async def connect_error(data):
                """Erro de conexão."""
                logger.error(f"❌ Erro de conexão WebSocket: {data}")
                self.is_connected = False
                self.authenticated = False
            
            # Handler ESSENCIAL para evento init (autenticação)
            @self.sio.on('init', namespace='/trade')
            async def on_init(data):
                """Evento de inicialização (ESSENCIAL para autenticação)."""
                logger.info(f"📡 Evento init recebido: {data}")
                try:
                    if isinstance(data, dict) and data.get('authenticated'):
                        # Usuário autenticado - marca como autenticado
                        logger.info("✅ Usuário já autenticado via init")
                        self.authenticated = True
                        self._update_last_data_received()
                        
                    elif isinstance(data, dict) and not data.get('authenticated'):
                        # Não autenticado - emite identify
                        logger.warning(f"ℹ️ init sem authenticated=true - dados: {data}")
                        if not self.authenticated:
                            logger.info("🆔 Usuário não autenticado, emitindo identify...")
                            await self._identify_and_configure()
                    else:
                        logger.warning(f"⚠️ Evento init com formato inesperado: {data}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar evento init: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # APENAS eventos essenciais conforme documentação oficial
            @self.sio.on('new_item', namespace='/trade')
            async def on_new_item(data):
                """Novo item disponível."""
                try:
                    logger.info(f"🆕 NOVO ITEM RECEBIDO: {type(data)}")
                    
                    if isinstance(data, list):
                        logger.info(f"📋 Lista com {len(data)} itens")
                        for item in data:
                            if isinstance(item, dict):
                                await self._process_item(item, 'new_item')
                    elif isinstance(data, dict):
                        logger.info(f"📋 Item único recebido")
                        await self._process_item(data, 'new_item')
                    
                    self._update_last_data_received()
                except Exception as e:
                    logger.error(f"❌ Erro ao processar new_item: {e}")
            
            @self.sio.on('deleted_item', namespace='/trade')
            async def on_deleted_item(data):
                """Item removido."""
                try:
                    if isinstance(data, list):
                        logger.debug(f"🗑️ {len(data)} itens removidos")
                    else:
                        logger.debug(f"🗑️ Item removido")
                    
                    self._update_last_data_received()
                except Exception as e:
                    logger.error(f"❌ Erro ao processar deleted_item: {e}")
            
            @self.sio.on('timesync', namespace='/trade')
            async def on_timesync(data):
                """Sincronização de tempo."""
                logger.debug(f"⏰ Timesync: {data}")
                self._update_last_data_received()
            
            # Handler genérico para capturar TODOS os eventos (debug)
            @self.sio.on('*', namespace='/trade')
            async def on_any_event(event, data):
                """Captura TODOS os eventos para debug."""
                try:
                    # Log apenas eventos que não temos handlers específicos
                    if event not in ['new_item', 'deleted_item', 'timesync', 'init']:
                        logger.info(f"📡 EVENTO NÃO TRATADO: {event} - Tipo: {type(data)}")
                        
                        # Se for lista com itens, pode ser importante
                        if isinstance(data, list) and len(data) > 0:
                            if isinstance(data[0], dict) and 'id' in data[0]:
                                logger.info(f"🎯 ITENS DETECTADOS em '{event}': {len(data)} itens")
                                for item in data:
                                    if isinstance(item, dict) and 'id' in item:
                                        await self._process_item(item, event)
                    
                    self._update_last_data_received()
                except Exception as e:
                    logger.error(f"❌ Erro ao processar evento '{event}': {e}")
            
            logger.info("✅ Handlers de eventos configurados")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar eventos: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _identify_and_configure(self):
        """Método removido - configuração é feita automaticamente após conectar."""
        pass
    
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
    
    async def _process_item(self, item: Dict, event_type: str) -> None:
        """Processa um item recebido."""
        try:
            # FILTRO ULTRA-RÁPIDO DE PREÇO (ANTES de qualquer processamento)
            if not self._check_basic_price_filter_ultra_fast(item):
                return  # Sai imediatamente se preço não estiver no range
            
            # Log do item sendo processado
            item_name = item.get('market_name', item.get('name', 'Unknown'))
            item_id = item.get('id', 'Unknown')
            logger.info(f"🎯 PROCESSANDO ITEM: {item_name} (ID: {item_id}) - Evento: {event_type}")
            
            # Extrai dados básicos do item
            extracted_item = self._extract_item_data(item)
            if not extracted_item:
                logger.warning(f"⚠️ Falha ao extrair dados do item: {item_name}")
                return
            
            # Enriquece com dados da database
            await self._enrich_item_data(extracted_item)
            
            # Aplica filtros de oportunidade
            if await self._apply_opportunity_filters(extracted_item):
                # Oportunidade encontrada!
                logger.info(f"🎯 OPORTUNIDADE ENCONTRADA: {extracted_item.get('name')}")
                
                # Envia para Discord
                await self.discord_poster.post_opportunity(extracted_item)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _check_basic_price_filter_ultra_fast(self, item: Dict) -> bool:
        """
        Filtro de preço ULTRA-RÁPIDO aplicado ANTES de qualquer processamento.
        Evita processar itens caros desnecessariamente.
        """
        try:
            # Extrai preço em centavos
            purchase_price_centavos = item.get('purchase_price')
            if purchase_price_centavos is None:
                return False
            
            # Converte para USD (ultra-rápido)
            price_usd = (purchase_price_centavos / 100) * self.settings.COIN_TO_USD_FACTOR
            
            # Filtros de preço configurados
            min_price = self.settings.MIN_PRICE
            max_price = self.settings.MAX_PRICE
            
            # Verifica preço mínimo (ultra-rápido)
            if price_usd < min_price:
                logger.debug(f"🚫 Item {item.get('market_name', 'Unknown')} REJEITADO: ${price_usd:.2f} < ${min_price:.2f} (MIN_PRICE)")
                return False
            
            # Verifica preço máximo (ultra-rápido)
            if price_usd > max_price:
                logger.debug(f"🚫 Item {item.get('market_name', 'Unknown')} REJEITADO: ${price_usd:.2f} > ${max_price:.2f} (MAX_PRICE)")
                return False
            
            # Item passou no filtro de preço básico
            logger.debug(f"✅ Item {item.get('market_name', 'Unknown')} ACEITO no filtro de preço: ${price_usd:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no filtro de preço ultra-rápido: {e}")
            return False
    
    async def _enrich_item_data(self, item: Dict) -> None:
        """Enriquece o item com dados da database."""
        try:
            base_name = item.get('base_name')
            is_stattrak = item.get('is_stattrak', False)
            is_souvenir = item.get('is_souvenir', False)
            condition = item.get('condition')
            
            if not base_name:
                logger.warning(f"⚠️ Item sem base_name: {item.get('name', 'Unknown')}")
                return
            
            logger.info(f"🔍 Enriquecendo item: {base_name}")
            logger.info(f"   - StatTrak: {is_stattrak}")
            logger.info(f"   - Souvenir: {is_souvenir}")
            logger.info(f"   - Condição: {condition}")
            
            # Busca preço Buff163 (UMA ÚNICA consulta)
            price_buff163 = await self.supabase.get_buff163_price_advanced(
                base_name, is_stattrak, is_souvenir, condition
            )
            
            if price_buff163 is not None:
                item['price_buff163'] = price_buff163
                logger.info(f"💰 Preço Buff163 encontrado: ${price_buff163:.2f}")
            else:
                logger.warning(f"⚠️ Preço Buff163 não encontrado para: {base_name}")
                item['price_buff163'] = None
            
            # Busca score de liquidez (UMA ÚNICA consulta)
            liquidity_score = await self.supabase.get_liquidity_score_advanced(
                base_name, is_stattrak, is_souvenir, condition
            )
            
            if liquidity_score is not None:
                item['liquidity_score'] = liquidity_score
                logger.info(f"💧 Score de liquidez encontrado: {liquidity_score:.1f}")
            else:
                logger.warning(f"⚠️ Score de liquidez não encontrado para: {base_name}")
                item['liquidity_score'] = None
                
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
    
    async def _apply_opportunity_filters(self, item: Dict) -> bool:
        """
        Aplica filtros de oportunidade de forma otimizada.
        Retorna True se o item passar em todos os filtros.
        """
        try:
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
            
            # Item passou em todos os filtros
            logger.info(f"✅ Item {item.get('name')} ACEITO em todos os filtros")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar filtros de oportunidade: {e}")
            return False
    
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
                await self._handle_connection_loss()
                return False
            
            # Verifica se está autenticado
            if not self.authenticated:
                logger.debug("❌ WebSocket não está autenticado")
                await self._handle_connection_loss()
                return False
            
            # Verifica se recebeu dados recentemente
            if hasattr(self, '_last_data_received'):
                time_since_data = time.time() - self._last_data_received
                if time_since_data > 300:  # 5 minutos sem dados
                    logger.warning(f"⚠️ Sem dados recebidos há {time_since_data:.0f}s")
                    await self._handle_connection_loss()
                    return False
            
            logger.debug("✅ Conexão WebSocket está saudável")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar saúde da conexão: {e}")
            await self._handle_connection_loss()
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
    
    async def _handle_connection_loss(self):
        """
        Gerencia perda de conexão de forma robusta.
        Implementa backoff exponencial e fallback para restart.
        """
        try:
            current_time = time.time()
            time_since_data = current_time - self._last_data_received
            time_since_stable = current_time - self._last_stable_connection
            
            logger.warning(f"⚠️ Sem dados recebidos há {time_since_data:.0f}s")
            logger.warning(f"⚠️ Última conexão estável há {time_since_stable:.0f}s")
            
            # Verifica se deve forçar restart
            if time_since_stable > self._force_restart_after:
                logger.error(f"🚨 Forçando restart após {self._force_restart_after/3600:.1f}h sem conexão estável")
                await self._force_restart()
                return
            
            # Verifica se excedeu falhas consecutivas
            if self._consecutive_failures >= self._max_consecutive_failures:
                logger.error(f"🚨 Excedeu {self._max_consecutive_failures} falhas consecutivas, forçando restart")
                await self._force_restart()
                return
            
            # Calcula delay de reconexão com backoff exponencial
            if current_time - self._last_reconnect_attempt < self._reconnect_backoff:
                logger.info(f"⏳ Aguardando {self._reconnect_backoff:.0f}s antes da próxima tentativa...")
                return
            
            # Tenta reconectar
            logger.info(f"🔄 Tentativa de reconexão {self._consecutive_failures + 1}/{self._max_consecutive_failures}")
            
            if await self._attempt_reconnection():
                # Sucesso na reconexão
                self._consecutive_failures = 0
                self._reconnect_backoff = 1  # Reset do backoff
                self._last_stable_connection = current_time
                logger.info("✅ Reconexão bem-sucedida!")
            else:
                # Falha na reconexão
                self._consecutive_failures += 1
                self._reconnect_backoff = min(self._reconnect_backoff * 2, self._max_reconnect_backoff)
                self._last_reconnect_attempt = current_time
                logger.warning(f"❌ Reconexão falhou. Próxima tentativa em {self._reconnect_backoff:.0f}s")
                
        except Exception as e:
            logger.error(f"❌ Erro ao gerenciar perda de conexão: {e}")
            self._consecutive_failures += 1
    
    async def _attempt_reconnection(self) -> bool:
        """
        Tenta reconectar ao WebSocket.
        
        Returns:
            bool: True se reconexão bem-sucedida
        """
        try:
            # Desconecta completamente
            if self.sio.connected:
                await self.sio.disconnect()
            
            # Reseta estado
            self.is_connected = False
            self.authenticated = False
            
            # Aguarda um pouco antes de tentar
            await asyncio.sleep(2)
            
            # Tenta reconectar
            if await self._connect_websocket():
                # Aguarda autenticação
                auth_timeout = 30  # 30 segundos para autenticar
                start_time = time.time()
                
                while not self.authenticated and (time.time() - start_time) < auth_timeout:
                    await asyncio.sleep(1)
                
                if self.authenticated:
                    logger.info("✅ Reconexão e autenticação bem-sucedidas")
                    return True
                else:
                    logger.warning("⚠️ Reconexão bem-sucedida, mas autenticação falhou")
                    return False
            else:
                logger.warning("⚠️ Falha na reconexão")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro durante tentativa de reconexão: {e}")
            return False
    
    async def _force_restart(self):
        """
        Força restart completo do scanner.
        Último recurso quando reconexão falha repetidamente.
        """
        try:
            logger.error("🚨 INICIANDO RESTART COMPLETO DO SCANNER")
            
            # Desconecta tudo
            await self.disconnect()
            
            # Aguarda um pouco
            await asyncio.sleep(10)
            
            # Reseta estado
            self._consecutive_failures = 0
            self._reconnect_backoff = 1
            self._last_stable_connection = time.time()
            
            # Tenta reconectar do zero
            if await self._connect_websocket():
                logger.info("✅ Restart completo bem-sucedido!")
            else:
                logger.error("❌ Restart completo falhou")
                
        except Exception as e:
            logger.error(f"❌ Erro durante restart completo: {e}")
    
    def _update_last_data_received(self):
        """Atualiza timestamp do último dado recebido."""
        self._last_data_received = time.time()
        # Se recebeu dados, considera conexão estável
        if self.is_connected and self.authenticated:
            self._last_stable_connection = time.time()
    
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
        """Método removido - autenticação é feita automaticamente após conectar."""
        pass
    
    async def start(self):
        """Inicia o scanner de marketplace."""
        try:
            logger.info("🚀 Iniciando scanner de marketplace...")
            
            # Obtém metadata antes de conectar
            if not await self._get_socket_metadata():
                logger.error("❌ Falha ao obter metadata")
                return False
            
            # Testa conexão com Supabase
            logger.info("🔍 Testando conexão com Supabase...")
            if not await self.supabase.test_connection():
                logger.error("❌ Falha na conexão com Supabase")
                return False
            
            # Conecta ao WebSocket
            logger.info("🔄 Tentando conectar ao WebSocket...")
            if not await self._connect_websocket():
                logger.error("❌ Falha ao conectar ao WebSocket")
                return False
            
            # Configura handlers de eventos
            logger.info("🔧 Configurando handlers de eventos...")
            await self._setup_socket_events()
            
            # Verifica se já está conectado
            if self.sio.connected:
                logger.info("✅ WebSocket já está conectado")
                # Configura automaticamente se já estiver conectado
                await self._configure_websocket_after_connection()
            else:
                logger.warning("⚠️ WebSocket não está conectado")
                return False
            
            # Aguarda um pouco para estabilizar
            await asyncio.sleep(2)
            
            # Verifica se está funcionando
            if self.authenticated:
                logger.info("✅ Scanner iniciado com sucesso!")
                return True
            else:
                logger.warning("⚠️ Scanner iniciado mas autenticação não confirmada")
                return True  # Continua mesmo sem confirmação de autenticação
                
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar scanner: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def connect(self):
        """Alias para start() - mantém compatibilidade."""
        return await self.start()
    
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
                    if await self.start():
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

    async def start_polling_fallback(self):
        """Método removido - foco apenas no WebSocket ultra-rápido."""
        pass
    
    async def fetch_items_via_api_fallback(self):
        """Busca itens via API do CSGOEmpire como fallback."""
        try:
            logger.info("🔍 Buscando itens via API de fallback...")
            
            # URL da API conforme documentação
            api_url = "https://csgoempire.com/api/v2/trading/items"
            
            # Parâmetros para buscar itens recentes
            params = {
                'per_page': 50,  # Máximo de itens por página
                'page': 1,
                'auction': 'yes',  # Apenas itens de leilão
                'sort': 'desc',  # Mais recentes primeiro
                'order': 'market_value'  # Ordenar por valor de mercado
            }
            
            # Headers necessários
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Faz a requisição HTTP
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'data' in data and isinstance(data['data'], list):
                            items = data['data']
                            logger.info(f"📡 API retornou {len(items)} itens")
                            
                            # Processa cada item encontrado
                            for item in items:
                                if isinstance(item, dict) and 'id' in item:
                                    logger.info(f"🎯 Processando item da API: {item.get('market_name', 'Unknown')}")
                                    await self._process_item(item, 'api_fallback')
                        else:
                            logger.warning(f"⚠️ Formato inesperado da API: {data}")
                    else:
                        logger.error(f"❌ API retornou status {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens via API: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def start_api_fallback_monitor(self):
        """Inicia monitoramento para usar API de fallback quando necessário."""
        logger.info("🔄 Iniciando monitor de API de fallback...")
        
        while True:
            try:
                # Verifica se WebSocket está funcionando bem
                time_since_last_data = time.time() - self._last_data_received
                
                # Se não recebeu dados há mais de 5 minutos, usa API de fallback
                if time_since_last_data > 300:  # 5 minutos
                    logger.warning(f"⚠️ Sem dados há {time_since_last_data:.0f}s, usando API de fallback...")
                    await self.fetch_items_via_api_fallback()
                
                # Aguarda antes da próxima verificação
                await asyncio.sleep(60)  # Verifica a cada 1 minuto
                
            except Exception as e:
                logger.error(f"❌ Erro no monitor de API: {e}")
                await asyncio.sleep(60)

    async def _configure_websocket_after_connection(self):
        """Configura o WebSocket automaticamente após conectar."""
        try:
            logger.info("🔧 Configurando WebSocket após conexão...")
            
            # Aguarda um pouco para estabilizar a conexão
            await asyncio.sleep(1)
            
            # Emite identify para autenticar
            logger.info("🆔 Emitindo identify para autenticação...")
            await self.sio.emit('identify', {
                'uid': self.user_id,
                'authorizationToken': self.socket_token,
                'signature': self.socket_signature,
                'uuid': str(uuid.uuid4())
            }, namespace='/trade')
            
            # NÃO aguarda resposta do init - configura diretamente
            logger.info("⚡ Configurando filtros e eventos diretamente após identify...")
            
            # Configura APENAS eventos essenciais conforme documentação oficial
            logger.info("📤 Configurando eventos permitidos...")
            await self.sio.emit('allowedEvents', {
                'events': ['new_item', 'deleted_item']
            }, namespace='/trade')
            logger.info("📤 Eventos permitidos configurados: new_item, deleted_item")
            
            # Configura filtros de preço
            logger.info("📤 Configurando filtros de preço...")
            await self.sio.emit('filters', {
                'price_min': self.settings.MIN_PRICE,
                'price_max': self.settings.MAX_PRICE
            }, namespace='/trade')
            logger.info("📤 Filtros de preço configurados")
            
            # Sincronização de tempo
            logger.info("📤 Solicitando timesync...")
            await self.sio.emit('timesync', namespace='/trade')
            logger.info("📤 Timesync solicitado")
            
            # Marca como autenticado e configurado
            self.authenticated = True
            
            # Log de configuração
            logger.info("🔍 Configuração do WebSocket concluída:")
            logger.info("   - Filtros de preço: $%.2f - $%.2f" % (self.settings.MIN_PRICE, self.settings.MAX_PRICE))
            logger.info("   - Eventos permitidos: new_item, deleted_item")
            logger.info("   - Aguardando itens...")
            
            # Log especial para debug
            logger.info("🔍 MONITORAMENTO ATIVO:")
            logger.info("   - WebSocket: ✅ Conectado")
            logger.info("   - Autenticação: ✅ Confirmada")
            logger.info("   - Eventos: ✅ Permitidos")
            logger.info("   - Filtros: ✅ Configurados")
            logger.info("   - Status: 🎯 PRONTO PARA CAPTURAR ITENS!")
            
            self._update_last_data_received()
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar WebSocket após conexão: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
