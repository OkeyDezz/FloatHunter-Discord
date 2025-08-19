"""
Opportunity Bot - Bot de Detecção de Oportunidades 24/7
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Dict

from config.settings import Settings
from core.marketplace_scanner import MarketplaceScanner
from core.discord_poster import DiscordPoster
from utils.supabase_client import SupabaseClient
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
        self.discord_poster = None
        self.scanner = None
        self.running = False
        
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
            if self.discord_poster:
                await self.discord_poster.post_opportunity(item)
            
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
            
            # Testa conexão com Supabase
            logger.info("🔍 Testando conexão com Supabase...")
            supabase = SupabaseClient()
            await supabase.test_connection()
            logger.info("✅ Conexão com Supabase OK")
            
            # Inicializa Discord
            logger.info("🤖 Inicializando Discord...")
            self.discord_poster = DiscordPoster(self.settings)
            await self.discord_poster.initialize()
            logger.info("✅ Discord conectado")
            
            # Inicializa scanner
            logger.info("🔄 Inicializando scanner...")
            self.scanner = MarketplaceScanner(
                settings=self.settings,
                discord_poster=self.discord_poster,
                opportunity_callback=self._on_opportunity_found
            )
            
            logger.info("✅ Opportunity Bot inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar bot: {e}")
            return False
    
    async def run(self):
        """Executa o bot."""
        try:
            # Salva PID do processo para restart automático
            import os
            pid = os.getpid()
            with open('bot.pid', 'w') as f:
                f.write(str(pid))
            logger.info(f"🆔 PID do processo salvo: {pid}")
            
            # Inicia servidor de health check IMEDIATAMENTE
            logger.info("🚀 Iniciando servidor de health check...")
            health_server = HealthServer()
            health_task = asyncio.create_task(health_server.start())
            
            # Aguarda um pouco para o health server inicializar
            await asyncio.sleep(2)
            
            if not await self.initialize():
                logger.error("❌ Falha na inicialização, encerrando...")
                return
            
            self.running = True
            logger.info("🔄 Bot iniciado, monitorando oportunidades...")
            
            # Inicia scanner
            await self.scanner.start()
            
            # Loop principal
            while self.running:
                try:
                    # Verifica status a cada 30 segundos
                    await asyncio.sleep(30)
                    
                    # Log de status
                    if self.scanner and self.scanner.is_connected:
                        logger.debug("✅ WebSocket conectado, monitorando...")
                    else:
                        logger.warning("⚠️ WebSocket desconectado, tentando reconectar...")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no loop principal: {e}")
                    await asyncio.sleep(5)
            
            # Shutdown graceful
            logger.info("🔄 Iniciando shutdown...")
            await self.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no bot: {e}")
        finally:
            # Garante que tudo seja fechado
            try:
                await self.cleanup()
            except:
                pass
    
    async def shutdown(self):
        """Shutdown manual do bot."""
        logger.info("🔄 Shutdown manual solicitado...")
        self.running = False
        await self.cleanup()
    
    async def cleanup(self):
        """Limpa recursos."""
        try:
            # Remove arquivo PID
            try:
                os.remove('bot.pid')
                logger.info("🗑️ Arquivo PID removido")
            except:
                pass
            
            # Desconecta componentes
            if self.scanner:
                await self.scanner.stop()
            
            if self.discord_poster:
                await self.discord_poster.close()
            
            logger.info("✅ Cleanup concluído")
            
        except Exception as e:
            logger.error(f"❌ Erro no cleanup: {e}")

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
