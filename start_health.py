#!/usr/bin/env python3
"""
Start Health - Script ultra-simples para iniciar apenas o health check.
SEMPRE funciona, mesmo com erros de configuração.
"""

import asyncio
import logging
import sys
import time

# Configuração de logging básica
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def start_health_server():
    """Inicia apenas o servidor de health check."""
    try:
        logger.info("🏥 Iniciando servidor de health check...")
        
        # Tenta importar o health server
        try:
            from health_server import HealthServer
            health_server = HealthServer()
            logger.info("✅ Health server importado com sucesso")
        except Exception as e:
            logger.error(f"❌ Falha ao importar health server: {e}")
            return False
        
        # Inicia o health server
        try:
            await health_server.start()
            logger.info("✅ Health server iniciado com sucesso")
            return True
        except Exception as e:
            logger.error(f"❌ Falha ao iniciar health server: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro fatal ao iniciar health server: {e}")
        return False

async def main():
    """Função principal."""
    try:
        logger.info("🚀 Iniciando modo health check apenas...")
        
        # Inicia health server
        if await start_health_server():
            logger.info("✅ Health server funcionando - aguardando...")
            
            # Loop infinito para manter o processo vivo
            while True:
                await asyncio.sleep(30)
                logger.info("💓 Health check ativo - processo vivo")
                
        else:
            logger.error("❌ Health server falhou - modo de emergência")
            
            # Modo de emergência - mantém processo vivo
            while True:
                await asyncio.sleep(30)
                logger.warning("🚨 Modo de emergência - processo mantido vivo")
                
    except Exception as e:
        logger.error(f"❌ Erro fatal na aplicação: {e}")
        
        # Loop de emergência síncrono
        while True:
            time.sleep(30)
            print("🚨 Modo de emergência síncrono - processo mantido vivo")
                
    except Exception as e:
        logger.error(f"❌ Erro fatal na aplicação: {e}")
        
        # Loop de emergência síncrono
        while True:
            time.sleep(30)
            print("🚨 Modo de emergência síncrono - processo mantido vivo")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("📡 Interrupção por teclado")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        
        # Loop de emergência síncrono
        while True:
            time.sleep(30)
            print("🚨 Modo de emergência síncrono - processo mantido vivo")
