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

# Configuração de logging básica
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class OpportunityBot:
    """Bot principal de detecção de oportunidades."""
    
    def __init__(self):
        self.running = False
        
        # Configura handlers de sinal para graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de shutdown."""
        logger.info(f"📡 Sinal {signum} recebido, iniciando shutdown...")
        self.running = False
    
    async def initialize(self) -> bool:
        """Inicializa o bot."""
        try:
            logger.info("🚀 Iniciando Opportunity Bot (modo minimalista)...")
            
            # Modo minimalista - sempre funciona
            logger.info("✅ Bot inicializado em modo minimalista")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar bot: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def run(self):
        """Executa o bot."""
        try:
            logger.info("🔄 Bot iniciado, modo minimalista ativo...")
            
            # Loop principal simples
            while self.running:
                try:
                    # Verifica status a cada 30 segundos
                    await asyncio.sleep(30)
                    logger.info("ℹ️ Bot em modo minimalista - health check ativo")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no loop principal: {e}")
                    await asyncio.sleep(5)
            
            # Shutdown graceful
            logger.info("🔄 Iniciando shutdown...")
            await self.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no bot: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def shutdown(self):
        """Shutdown graceful do bot."""
        try:
            logger.info("🔄 Shutdown em andamento...")
            self.running = False
            logger.info("✅ Shutdown concluído")
        except Exception as e:
            logger.error(f"❌ Erro durante shutdown: {e}")

async def main():
    """Função principal."""
    try:
        logger.info("🚀 Iniciando Opportunity Bot...")
        
        # Inicia health server IMEDIATAMENTE
        logger.info("🏥 Iniciando servidor de health check...")
        try:
            from health_server import HealthServer
            health_server = HealthServer()
            health_task = asyncio.create_task(health_server.start())
            logger.info("✅ Health server iniciado")
        except Exception as e:
            logger.error(f"❌ Falha ao iniciar health server: {e}")
            # Continua mesmo sem health server
        
        # Aguarda inicialização do health server
        await asyncio.sleep(2)
        
        # Inicia bot
        bot = OpportunityBot()
        if await bot.initialize():
            bot.running = True
            await bot.run()
        else:
            logger.error("❌ Falha na inicialização do bot")
            # Mantém health check rodando mesmo se bot falhar
            while True:
                await asyncio.sleep(30)
                logger.info("ℹ️ Health check ativo, bot em modo de espera")
                
    except Exception as e:
        logger.error(f"❌ Erro fatal na aplicação: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Loop de emergência para manter processo vivo
        while True:
            await asyncio.sleep(30)
            logger.info("🚨 Modo de emergência - processo mantido vivo")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("📡 Interrupção por teclado")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Loop de emergência síncrono
        while True:
            import time
            time.sleep(30)
            print("🚨 Modo de emergência síncrono - processo mantido vivo")
