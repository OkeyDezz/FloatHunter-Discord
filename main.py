"""
Main entry point para o Opportunity Bot.
Bot simples e direto para capturar oportunidades no CSGOEmpire.
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

async def main():
    """Função principal do bot."""
    try:
        logger.info("🚀 Iniciando Opportunity Bot...")
        
        # Importa o scanner
        from core.marketplace_scanner import MarketplaceScanner
        
        # Cria instância do scanner
        scanner = MarketplaceScanner()
        
        # Configura signal handlers para shutdown graceful
        def signal_handler(signum, frame):
            logger.info(f"📡 Sinal {signum} recebido, iniciando shutdown...")
            asyncio.create_task(shutdown(scanner))
        
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

async def shutdown(scanner):
    """Shutdown graceful do bot."""
    try:
        logger.info("🛑 Iniciando shutdown graceful...")
        
        # Desconecta do WebSocket
        await scanner.disconnect()
        
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
