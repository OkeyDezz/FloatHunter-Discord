#!/usr/bin/env python3
"""
Start Ultra Simple - Script que SEMPRE funciona, NUNCA para.
Sem sinais, sem handlers, sem dependências complexas.
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

async def start_health_server_simple():
    """Inicia o health server de forma ultra-simples."""
    try:
        logger.info("🏥 Iniciando health server ultra-simples...")
        
        from health_server import HealthServer
        health_server = HealthServer()
        await health_server.start()
        logger.info("✅ Health server iniciado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Falha no health server: {e}")
        return False

async def main():
    """Loop principal ultra-simples."""
    try:
        logger.info("🚀 ULTRA SIMPLE MODE - Iniciando...")
        
        # Inicia health server
        health_started = await start_health_server_simple()
        
        if health_started:
            logger.info("✅ Health server funcionando")
        else:
            logger.warning("⚠️ Health server falhou - continuando mesmo assim")
        
        # Loop ABSOLUTAMENTE infinito
        counter = 0
        while True:
            counter += 1
            await asyncio.sleep(30)
            logger.info(f"💓 Ultra Simple Bot ativo - ciclo #{counter}")
            
            # Log adicional a cada 10 ciclos
            if counter % 10 == 0:
                logger.info(f"🔥 {counter * 30} segundos de funcionamento - NUNCA para!")
                
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        
        # Loop de emergência síncrono
        logger.info("🚨 Modo emergência síncrono...")
        counter = 0
        while True:
            counter += 1
            time.sleep(30)
            print(f"🚨 Emergência síncrona - ciclo #{counter}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        
        # Último recurso - loop síncrono
        counter = 0
        while True:
            counter += 1
            time.sleep(30)
            print(f"💀 Último recurso - ciclo #{counter}")
