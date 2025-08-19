#!/usr/bin/env python3
"""
Start Robust Bot - Script robusto que SEMPRE funciona E monitora CSGOEmpire.
Combina a robustez do ultra-simple com a funcionalidade completa.
"""

import asyncio
import logging
import sys
import time
import os
from typing import Dict

# Configuração de logging básica
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class RobustBot:
    """Bot robusto que nunca para e monitora CSGOEmpire."""
    
    def __init__(self):
        self.running = True
        self.health_server = None
        self.scanner = None
        self.discord_poster = None
        
    async def start_health_server(self):
        """Inicia o health server."""
        try:
            logger.info("🏥 Iniciando health server...")
            from health_server import HealthServer
            self.health_server = HealthServer()
            await self.health_server.start()
            logger.info("✅ Health server iniciado")
            return True
        except Exception as e:
            logger.error(f"❌ Falha no health server: {e}")
            return False
    
    async def initialize_components(self):
        """Inicializa componentes do bot de forma robusta."""
        try:
            logger.info("🔧 Inicializando componentes do bot...")
            
            # Tenta inicializar Supabase
            try:
                from utils.supabase_client import SupabaseClient
                supabase = SupabaseClient()
                await supabase.test_connection()
                logger.info("✅ Supabase conectado")
            except Exception as e:
                logger.warning(f"⚠️ Supabase falhou: {e} - continuando sem database")
            
            # Tenta inicializar Discord
            try:
                from config.settings import Settings
                settings = Settings()
                if settings.DISCORD_TOKEN and settings.CSGOEMPIRE_CHANNEL_ID:
                    from core.discord_poster import DiscordPoster
                    self.discord_poster = DiscordPoster(settings)
                    await self.discord_poster.initialize()
                    logger.info("✅ Discord conectado")
                else:
                    logger.warning("⚠️ Discord não configurado")
            except Exception as e:
                logger.warning(f"⚠️ Discord falhou: {e} - continuando sem Discord")
            
            # Tenta inicializar Scanner
            try:
                from config.settings import Settings
                from core.marketplace_scanner import MarketplaceScanner
                settings = Settings()
                
                if settings.CSGOEMPIRE_API_KEY:
                    self.scanner = MarketplaceScanner(
                        settings=settings,
                        discord_poster=self.discord_poster,
                        opportunity_callback=self._on_opportunity_found
                    )
                    logger.info("✅ Scanner inicializado")
                else:
                    logger.warning("⚠️ CSGOEmpire API key não configurada")
            except Exception as e:
                logger.warning(f"⚠️ Scanner falhou: {e} - continuando sem scanner")
            
            logger.info("✅ Componentes inicializados (com fallbacks)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização: {e}")
            return False
    
    async def _on_opportunity_found(self, item: Dict, marketplace: str):
        """Callback para oportunidades encontradas."""
        try:
            logger.info(f"🎯 OPORTUNIDADE: {item.get('name', 'Unknown')} em {marketplace}")
            
            if self.discord_poster:
                try:
                    await self.discord_poster.post_opportunity(item)
                    logger.info("✅ Oportunidade enviada para Discord")
                except Exception as e:
                    logger.error(f"❌ Erro ao enviar para Discord: {e}")
            else:
                logger.info("ℹ️ Discord não disponível - oportunidade apenas logada")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar oportunidade: {e}")
    
    async def start_scanner(self):
        """Inicia o scanner se disponível."""
        if self.scanner:
            try:
                logger.info("🔄 Iniciando scanner...")
                await self.scanner.start()
                logger.info("✅ Scanner iniciado e monitorando")
                return True
            except Exception as e:
                logger.error(f"❌ Falha ao iniciar scanner: {e}")
                return False
        else:
            logger.warning("⚠️ Scanner não disponível")
            return False
    
    async def run(self):
        """Loop principal do bot."""
        try:
            logger.info("🚀 Bot robusto iniciado - funcionando com fallbacks...")
            
            # Inicializa componentes
            await self.initialize_components()
            
            # Tenta iniciar scanner
            scanner_started = await self.start_scanner()
            
            # Loop principal robusto
            cycle = 0
            while self.running:
                cycle += 1
                await asyncio.sleep(30)
                
                # Log de status
                if scanner_started and self.scanner and self.scanner.is_connected:
                    logger.info(f"💓 Bot ativo - Scanner conectado - Ciclo #{cycle}")
                elif scanner_started and self.scanner:
                    logger.warning(f"⚠️ Bot ativo - Scanner desconectado - Ciclo #{cycle}")
                else:
                    logger.info(f"ℹ️ Bot ativo - Apenas health check - Ciclo #{cycle}")
                
                # Log adicional a cada 10 ciclos
                if cycle % 10 == 0:
                    logger.info(f"🔥 {cycle * 30} segundos de funcionamento - Bot robusto!")
                    
        except Exception as e:
            logger.error(f"❌ Erro no loop principal: {e}")
            
            # Loop de emergência
            logger.info("🚨 Entrando em modo de emergência...")
            cycle = 0
            while True:
                cycle += 1
                await asyncio.sleep(30)
                logger.info(f"🚨 Emergência assíncrona - ciclo #{cycle}")

async def main():
    """Função principal."""
    try:
        logger.info("🚀 Iniciando Bot Robusto...")
        
        # Cria bot
        bot = RobustBot()
        
        # Inicia health server
        health_ok = await bot.start_health_server()
        if not health_ok:
            logger.warning("⚠️ Health server falhou - continuando mesmo assim")
        
        # Aguarda health server
        await asyncio.sleep(2)
        
        # Executa bot robusto
        await bot.run()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        
        # Loop de emergência síncrono
        logger.info("🚨 Modo emergência síncrono...")
        cycle = 0
        while True:
            cycle += 1
            time.sleep(30)
            print(f"🚨 Emergência síncrona - ciclo #{cycle}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        
        # Último recurso
        cycle = 0
        while True:
            cycle += 1
            time.sleep(30)
            print(f"💀 Último recurso - ciclo #{cycle}")
