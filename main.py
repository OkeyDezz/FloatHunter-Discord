"""
Main entry point para o Opportunity Bot.
Bot simples e direto para capturar oportunidades no CSGOEmpire.
Inclui health server integrado para Railway.
"""
import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('opportunity_bot.log')
    ]
)

logger = logging.getLogger(__name__)

async def start_health_server():
    """Inicia o servidor de health check em background."""
    try:
        from health_server import HealthServer
        
        server = HealthServer()
        if await server.start():
            logger.info("✅ Health server iniciado com sucesso!")
            return server
        else:
            logger.error("❌ Falha ao iniciar health server")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar health server: {e}")
        return None

async def main():
    """Função principal do bot."""
    try:
        logger.info("🚀 Iniciando Opportunity Bot...")
        
        # Inicia health server em background
        health_server = await start_health_server()
        if health_server:
            logger.info("🌐 Health server rodando em background")
        
        # Importa o scanner
        from core.marketplace_scanner import MarketplaceScanner
        
        # Cria instância do scanner
        scanner = MarketplaceScanner()
        
        # Configura signal handlers para shutdown graceful
        def signal_handler(signum, frame):
            logger.info(f"📡 Sinal {signum} recebido, iniciando shutdown...")
            asyncio.create_task(shutdown(scanner, health_server))
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Inicia o scanner
        logger.info("🔍 Iniciando scanner de marketplace...")
        await scanner.run_forever()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal no main: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

async def shutdown(scanner, health_server=None):
    """Shutdown graceful do bot."""
    try:
        logger.info("🛑 Iniciando shutdown graceful...")
        
        # Desconecta do WebSocket
        await scanner.disconnect()
        
        # Para o health server se estiver rodando
        if health_server:
            await health_server.stop()
            logger.info("🛑 Health server parado")
        
        logger.info("✅ Shutdown concluído com sucesso")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Erro durante shutdown: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Executa o bot
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro não tratado: {e}")
        sys.exit(1)
