#!/usr/bin/env python3
"""
Script que inicia o bot completo após verificar se o health server está funcionando.
"""

import asyncio
import logging
import os
import sys
import time
from health_server import HealthServer
from main import OpportunityBot

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def wait_for_health_server(port: int = 8000, max_wait: int = 60):
    """Aguarda o health server estar funcionando."""
    import aiohttp
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{port}/health", timeout=5) as response:
                    if response.status == 200:
                        logger.info("✅ Health server está funcionando!")
                        return True
        except Exception as e:
            logger.debug(f"Aguardando health server... ({e})")
        
        await asyncio.sleep(2)
    
    logger.error(f"❌ Health server não respondeu em {max_wait} segundos")
    return False

async def main():
    """Inicia o bot completo."""
    try:
        port = int(os.getenv('PORT', 8000))
        
        # Inicia health server em background
        logger.info("🚀 Iniciando health server...")
        health_server = HealthServer(port)
        health_task = asyncio.create_task(health_server.start())
        
        # Aguarda health server inicializar
        await asyncio.sleep(3)
        
        # Verifica se está funcionando
        if not await wait_for_health_server(port):
            logger.error("❌ Health server não está funcionando")
            sys.exit(1)
        
        # Inicia bot completo
        logger.info("🤖 Iniciando bot completo...")
        bot = OpportunityBot()
        
        # Executa bot em background
        bot_task = asyncio.create_task(bot.run())
        
        # Mantém ambos rodando
        try:
            await asyncio.gather(health_task, bot_task)
        except asyncio.CancelledError:
            logger.info("🛑 Tarefas canceladas")
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrupção do usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
