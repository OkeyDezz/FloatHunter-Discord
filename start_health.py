#!/usr/bin/env python3
"""
Script de startup que inicia apenas o health server primeiro.
Útil para Railway que precisa de um endpoint de health check funcionando imediatamente.
"""

import asyncio
import logging
import os
import sys
from health_server import HealthServer

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Inicia apenas o health server."""
    try:
        logger.info("🚀 Iniciando servidor de health check...")
        
        # Inicia health server
        server = HealthServer()
        if await server.start():
            logger.info("✅ Health server iniciado com sucesso!")
            logger.info("📊 Endpoint disponível em: /health")
            
            # Mantém rodando
            while True:
                await asyncio.sleep(1)
        else:
            logger.error("❌ Falha ao iniciar health server")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Interrupção do usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
