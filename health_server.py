"""
Servidor de health check para o Railway.
"""

import asyncio
import logging
from aiohttp import web
from datetime import datetime

logger = logging.getLogger(__name__)

class HealthServer:
    """Servidor simples para health checks do Railway."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Configura as rotas do servidor."""
        
        async def health_check(request):
            """Endpoint de health check."""
            return web.json_response({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'service': 'opportunity-bot',
                'version': '1.0.0'
            })
        
        async def status(request):
            """Endpoint de status detalhado."""
            return web.json_response({
                'status': 'running',
                'timestamp': datetime.now().isoformat(),
                'service': 'opportunity-bot',
                'endpoints': {
                    'health': '/health',
                    'status': '/status'
                }
            })
        
        # Adiciona rotas
        self.app.router.add_get('/health', health_check)
        self.app.router.add_get('/status', status)
        self.app.router.add_get('/', health_check)
    
    async def start(self):
        """Inicia o servidor."""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            logger.info(f"🚀 Servidor de health check iniciado na porta {self.port}")
            logger.info(f"📊 Health check disponível em: http://0.0.0.0:{self.port}/health")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar servidor de health check: {e}")
    
    async def stop(self):
        """Para o servidor."""
        try:
            await self.app.cleanup()
            logger.info("🛑 Servidor de health check parado")
        except Exception as e:
            logger.error(f"❌ Erro ao parar servidor: {e}")

async def main():
    """Função principal para executar o servidor de health check."""
    server = HealthServer()
    await server.start()
    
    # Mantém o servidor rodando
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
