#!/usr/bin/env python3
"""
Bot Principal - Bot limpo e novo que usa o cliente CSGOEmpire.
"""

import asyncio
import logging
import sys
import time
from typing import Dict, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class OpportunityBot:
    """Bot principal de oportunidades."""
    
    def __init__(self):
        self.running = False
        self.csgoempire_client = None
        self.discord_poster = None
        
    async def initialize(self) -> bool:
        """Inicializa o bot."""
        try:
            logger.info("🚀 Iniciando Opportunity Bot...")
            
            # Carrega configurações
            try:
                from config.settings import Settings
                settings = Settings()
                logger.info("✅ Configurações carregadas")
                
                if not settings.CSGOEMPIRE_API_KEY:
                    logger.error("❌ CSGOEMPIRE_API_KEY não configurada")
                    return False
                    
                logger.info(f"✅ API Key configurada: {settings.CSGOEMPIRE_API_KEY[:10]}...")
                
            except Exception as e:
                logger.error(f"❌ Erro ao carregar configurações: {e}")
                return False
            
            # Inicializa Discord (opcional)
            try:
                if settings.DISCORD_TOKEN and settings.CSGOEMPIRE_CHANNEL_ID:
                    from core.discord_poster import DiscordPoster
                    self.discord_poster = DiscordPoster(settings)
                    await self.discord_poster.initialize()
                    logger.info("✅ Discord conectado")
                else:
                    logger.warning("⚠️ Discord não configurado")
            except Exception as e:
                logger.warning(f"⚠️ Discord falhou: {e} - continuando sem Discord")
            
            # Inicializa cliente CSGOEmpire
            try:
                from csgoempire_client import CSGOEmpireClient
                self.csgoempire_client = CSGOEmpireClient(settings.CSGOEMPIRE_API_KEY)
                logger.info("✅ Cliente CSGOEmpire criado")
            except Exception as e:
                logger.error(f"❌ Erro ao criar cliente CSGOEmpire: {e}")
                return False
            
            logger.info("✅ Bot inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar bot: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def on_item_received(self, item: Dict, event_type: str):
        """Callback chamado quando um item é recebido."""
        try:
            item_id = item.get('id')
            item_name = item.get('market_name', 'Unknown')
            item_price = item.get('purchase_price', 0)
            
            logger.info(f"📦 Item recebido: {item_name} (ID: {item_id}) - Preço: {item_price}")
            
            # Converte preço de centavos para USD
            from config.settings import Settings
            settings = Settings()
            price_usd = item_price * settings.COIN_TO_USD_FACTOR
            
            logger.info(f"💰 Preço convertido: {item_price} centavos = ${price_usd:.2f}")
            
            # Verifica filtros básicos
            if price_usd < settings.MIN_PRICE or price_usd > settings.MAX_PRICE:
                logger.debug(f"❌ Item {item_name} fora do range de preço: ${price_usd:.2f}")
                return
            
            # Enriquece item com dados do banco
            enriched_item = await self.enrich_item(item, price_usd)
            if not enriched_item:
                logger.debug(f"❌ Item {item_name} não pôde ser enriquecido")
                return
            
            # Verifica se é oportunidade
            if await self.is_opportunity(enriched_item):
                logger.info(f"🎯 OPORTUNIDADE ENCONTRADA: {item_name}")
                
                # Envia para Discord
                if self.discord_poster:
                    try:
                        await self.discord_poster.post_opportunity(enriched_item)
                        logger.info("✅ Oportunidade enviada para Discord")
                    except Exception as e:
                        logger.error(f"❌ Erro ao enviar para Discord: {e}")
                else:
                    logger.info("ℹ️ Discord não disponível - oportunidade apenas logada")
            else:
                logger.debug(f"ℹ️ Item {item_name} não é oportunidade")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar item: {e}")
    
    async def enrich_item(self, item: Dict, price_usd: float) -> Optional[Dict]:
        """Enriquece item com dados do banco."""
        try:
            # Dados básicos
            enriched_item = {
                'id': item.get('id'),
                'name': item.get('market_name', 'Unknown'),
                'price': price_usd,
                'price_csgoempire_coin': item.get('purchase_price', 0),
                'suggested_price': item.get('suggested_price', 0) * 0.614,  # Fator de conversão
                'market_value': item.get('market_value', 0) * 0.614,
                'wear': item.get('wear'),
                'wear_name': item.get('wear_name'),
                'rarity': item.get('item_search', {}).get('rarity'),
                'type': item.get('item_search', {}).get('type'),
                'sub_type': item.get('item_search', {}).get('sub_type'),
                'stickers': item.get('stickers', []),
                'auction_ends_at': item.get('auction_ends_at'),
                'auction_highest_bid': item.get('auction_highest_bid'),
                'auction_number_of_bids': item.get('auction_number_of_bids'),
                'published_at': item.get('published_at')
            }
            
            # Busca dados do banco
            try:
                from utils.supabase_client import SupabaseClient
                supabase = SupabaseClient()
                
                # Extrai informações do nome
                item_info = self.parse_item_name(item.get('market_name', ''))
                
                if item_info:
                    # Busca preço Buff163
                    price_buff163 = await supabase.get_buff163_price_advanced(
                        base_name=item_info['base_name'],
                        is_stattrak=item_info['is_stattrak'],
                        is_souvenir=item_info['is_souvenir'],
                        condition=item_info['condition']
                    )
                    
                    if price_buff163:
                        enriched_item['price_buff163'] = price_buff163
                        logger.debug(f"✅ Preço Buff163: ${price_buff163:.2f}")
                    
                    # Busca liquidez
                    liquidity_score = await supabase.get_liquidity_score_advanced(
                        base_name=item_info['base_name'],
                        is_stattrak=item_info['is_stattrak'],
                        is_souvenir=item_info['is_souvenir'],
                        condition=item_info['condition']
                    )
                    
                    if liquidity_score is not None:
                        enriched_item['liquidity_score'] = liquidity_score
                        logger.debug(f"✅ Liquidez: {liquidity_score:.1f}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Erro ao enriquecer com banco: {e}")
            
            return enriched_item
            
        except Exception as e:
            logger.error(f"❌ Erro ao enriquecer item: {e}")
            return None
    
    def parse_item_name(self, market_name: str) -> Optional[Dict]:
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
    
    async def is_opportunity(self, item: Dict) -> bool:
        """Verifica se um item é uma oportunidade."""
        try:
            from config.settings import Settings
            settings = Settings()
            
            # Verifica se tem preço Buff163
            if 'price_buff163' not in item:
                logger.debug(f"❌ Item {item['name']} sem preço Buff163")
                return False
            
            # Verifica se tem liquidez
            if 'liquidity_score' not in item:
                logger.debug(f"❌ Item {item['name']} sem liquidez")
                return False
            
            # Verifica liquidez mínima
            if item['liquidity_score'] < settings.MIN_LIQUIDITY_SCORE:
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
            if profit_percentage < settings.MIN_PROFIT_PERCENTAGE:
                logger.debug(f"❌ Item {item['name']} lucro baixo: {profit_percentage:.2f}%")
                return False
            
            logger.info(f"✅ OPORTUNIDADE: {item['name']} - Lucro: {profit_percentage:.2f}% - Liquidez: {item['liquidity_score']:.1f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar oportunidade: {e}")
            return False
    
    async def run(self):
        """Executa o bot."""
        try:
            logger.info("🔄 Bot iniciado, monitorando oportunidades...")
            
            # Inicia cliente CSGOEmpire
            if self.csgoempire_client:
                try:
                    await self.csgoempire_client.start(self.on_item_received)
                    logger.info("✅ Cliente CSGOEmpire iniciado")
                except Exception as e:
                    logger.error(f"❌ Falha ao iniciar cliente CSGOEmpire: {e}")
                    return
            
            # Loop principal
            cycle = 0
            while self.running:
                cycle += 1
                await asyncio.sleep(30)
                
                # Log de status
                if self.csgoempire_client:
                    status = self.csgoempire_client.get_status()
                    if status['connected'] and status['authenticated']:
                        logger.info(f"💓 Bot ativo - WebSocket conectado - Ciclo #{cycle}")
                    elif status['connected']:
                        logger.warning(f"⚠️ Bot ativo - WebSocket não autenticado - Ciclo #{cycle}")
                    else:
                        logger.error(f"❌ Bot ativo - WebSocket desconectado - Ciclo #{cycle}")
                        break
                else:
                    logger.info(f"ℹ️ Bot ativo - Sem cliente CSGOEmpire - Ciclo #{cycle}")
                
                # Log adicional a cada 10 ciclos
                if cycle % 10 == 0:
                    logger.info(f"🔥 {cycle * 30} segundos de funcionamento!")
                    
        except Exception as e:
            logger.error(f"❌ Erro no loop principal: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def stop(self):
        """Para o bot."""
        try:
            logger.info("🛑 Parando bot...")
            
            self.running = False
            
            # Para cliente CSGOEmpire
            if self.csgoempire_client:
                await self.csgoempire_client.stop()
            
            logger.info("✅ Bot parado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao parar bot: {e}")

async def main():
    """Função principal."""
    try:
        logger.info("🚀 Iniciando Opportunity Bot...")
        
        # Cria bot
        bot = OpportunityBot()
        
        # Inicializa
        if not await bot.initialize():
            logger.error("❌ Falha na inicialização")
            return
        
        # Executa
        bot.running = True
        await bot.run()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    finally:
        # Shutdown
        if 'bot' in locals():
            await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("📡 Interrupção por teclado")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
