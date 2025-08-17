"""
Opportunity Bot - Bot de Detecção de Oportunidades 24/7
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict

from config.settings import Settings
from core.marketplace_scanner import MarketplaceScanner
from core.discord_poster import DiscordPoster
from health_server import HealthServer

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('opportunity_bot.log') if Settings().LOG_TO_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

class OpportunityBot:
    """Bot principal de detecção de oportunidades."""
    
    def __init__(self):
        self.settings = Settings()
        self.scanner = MarketplaceScanner()
        self.discord_poster = DiscordPoster()
        self.running = False
        
        # Configura callback para oportunidades
        self.scanner.set_opportunity_callback(self._on_opportunity_found)
        
        # Configura handlers de sinal para graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de shutdown."""
        logger.info(f"📡 Sinal {signum} recebido, iniciando shutdown...")
        self.running = False
    
    async def _on_opportunity_found(self, item: Dict, marketplace: str):
        """
        Callback chamado quando uma oportunidade é encontrada.
        
        Args:
            item: Dados do item
            marketplace: Nome do marketplace
        """
        try:
            logger.info(f"🎯 Oportunidade encontrada em {marketplace}: {item.get('name', 'Unknown')}")
            
            # Posta no Discord
            await self.discord_poster.post_opportunity(item, marketplace)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar oportunidade: {e}")
    
    async def initialize(self) -> bool:
        """Inicializa o bot."""
        try:
            logger.info("🚀 Iniciando Opportunity Bot...")
            
            # Valida configurações
            if not self.settings.validate():
                logger.error("❌ Configurações inválidas")
                return False
            
            # Inicializa Discord
            logger.info("🤖 Inicializando Discord...")
            if not await self.discord_poster.initialize():
                logger.error("❌ Falha ao inicializar Discord")
                return False
            
            logger.info("✅ Opportunity Bot inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar bot: {e}")
            return False
    
    async def run(self):
        """Executa o bot."""
        try:
            if not await self.initialize():
                return
            
            self.running = True
            logger.info("🔄 Bot iniciado, monitorando oportunidades...")
            
            # Inicia scanner em background
            scanner_task = asyncio.create_task(self.scanner.run_forever())
            
            # Inicia servidor de health check em background
            health_server = HealthServer()
            health_task = asyncio.create_task(health_server.start())
            
            # Loop principal
            while self.running:
                try:
                    # Verifica status a cada 30 segundos
                    await asyncio.sleep(30)
                    
                    # Log de status
                    if self.scanner.is_connected:
                        logger.debug("✅ WebSocket conectado, monitorando...")
                    else:
                        logger.warning("⚠️ WebSocket desconectado, tentando reconectar...")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no loop principal: {e}")
                    await asyncio.sleep(5)
            
            # Shutdown graceful
            logger.info("🔄 Iniciando shutdown...")
            
            # Cancela scanner
            scanner_task.cancel()
            try:
                await scanner_task
            except asyncio.CancelledError:
                pass
            
            # Cancela servidor de health check
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass
            
            # Desconecta componentes
            await self.scanner.disconnect()
            await self.discord_poster.close()
            
            logger.info("✅ Shutdown concluído")
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no bot: {e}")
        finally:
            # Garante que tudo seja fechado
            try:
                await self.scanner.disconnect()
                await self.discord_poster.close()
            except:
                pass
    
    async def shutdown(self):
        """Shutdown manual do bot."""
        logger.info("🔄 Shutdown manual solicitado...")
        self.running = False

async def main():
    """Função principal."""
    bot = OpportunityBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("📡 Interrupção do usuário detectada")
        await bot.shutdown()
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        await bot.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n📡 Bot interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)
