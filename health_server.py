"""
Servidor de health check para o Railway.
"""

import asyncio
import logging
import os
from aiohttp import web
from datetime import datetime

# Configura logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthServer:
    """Servidor simples para health checks do Railway."""
    
    def __init__(self, port: int = None):
        # Usa porta do Railway ou padrão
        self.port = port or int(os.getenv('PORT', 8000))
        self.app = web.Application()
        self.setup_routes()
        self.start_time = datetime.now()
    
    def setup_routes(self):
        """Configura as rotas do servidor."""
        
        async def health_check(request):
            """Endpoint de health check principal."""
            try:
                uptime = (datetime.now() - self.start_time).total_seconds()
                return web.json_response({
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'uptime_seconds': int(uptime),
                    'service': 'opportunity-bot',
                    'version': '1.0.0',
                    'port': self.port
                }, status=200)
            except Exception as e:
                logger.error(f"Erro no health check: {e}")
                return web.json_response({
                    'status': 'error',
                    'error': str(e)
                }, status=500)
        
        async def status(request):
            """Endpoint de status detalhado."""
            try:
                uptime = (datetime.now() - self.start_time).total_seconds()
                return web.json_response({
                    'status': 'running',
                    'timestamp': datetime.now().isoformat(),
                    'uptime_seconds': int(uptime),
                    'service': 'opportunity-bot',
                    'endpoints': {
                        'health': '/health',
                        'status': '/status',
                        'root': '/'
                    },
                    'port': self.port
                }, status=200)
            except Exception as e:
                logger.error(f"Erro no status: {e}")
                return web.json_response({
                    'status': 'error',
                    'error': str(e)
                }, status=500)
        
        async def root(request):
            """Endpoint raiz."""
            return web.json_response({
                'service': 'opportunity-bot',
                'status': 'running',
                'health_check': '/health',
                'timestamp': datetime.now().isoformat()
            }, status=200)
        
        # Adiciona rotas
        self.app.router.add_get('/health', health_check)
        self.app.router.add_get('/status', status)
        self.app.router.add_get('/', root)
        
        # Middleware para logging
        @web.middleware
        async def log_requests(request, handler):
            start_time = datetime.now()
            response = await handler(request)
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"{request.method} {request.path} - {response.status} - {duration:.3f}s")
            return response
        
        self.app.middlewares.append(log_requests)
    
    async def start(self):
        """Inicia o servidor."""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            logger.info(f"🚀 Servidor de health check iniciado na porta {self.port}")
            logger.info(f"📊 Health check disponível em: http://0.0.0.0:{self.port}/health")
            logger.info(f"🌐 Status disponível em: http://0.0.0.0:{self.port}/status")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar servidor de health check: {e}")
            return False
    
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
    if await server.start():
        logger.info("✅ Servidor iniciado com sucesso")
        
        # Mantém o servidor rodando
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Recebido sinal de parada")
            await server.stop()
    else:
        logger.error("❌ Falha ao iniciar servidor")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
