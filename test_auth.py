#!/usr/bin/env python3
"""
Script para testar especificamente a autenticação WebSocket do CSGOEmpire.
"""

import asyncio
import logging
import socketio
import aiohttp
import time
import uuid
from pathlib import Path
import sys

# Adiciona o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class WebSocketAuthTester:
    """Testa especificamente a autenticação WebSocket."""
    
    def __init__(self):
        self.settings = Settings()
        self.sio = socketio.AsyncClient()
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        self.authenticated = False
        
        # Configura eventos
        self._setup_events()
    
    def _setup_events(self):
        """Configura os handlers de eventos."""
        
        @self.sio.event(namespace='/trade')
        async def connect():
            logger.info("🔌 Conectado ao namespace /trade")
        
        @self.sio.event(namespace='/trade')
        async def disconnect():
            logger.info("🔌 Desconectado do namespace /trade")
        
        @self.sio.on('init', namespace='/trade')
        async def on_init(data):
            logger.info(f"📡 Evento init recebido: {data}")
            
            if isinstance(data, dict):
                auth_status = data.get('authenticated', False)
                is_guest = data.get('isGuest', True)
                server_info = data.get('server', 'Unknown')
                
                logger.info(f"📡 Status de autenticação:")
                logger.info(f"   - Authenticated: {auth_status}")
                logger.info(f"   - Is Guest: {is_guest}")
                logger.info(f"   - Server: {server_info}")
                
                if auth_status:
                    logger.info("✅ Autenticação confirmada pelo servidor")
                    self.authenticated = True
                else:
                    logger.warning("⚠️ Servidor indica que não está autenticado")
                    if is_guest:
                        logger.warning("⚠️ Usuário marcado como guest")
        
        @self.sio.on('*', namespace='/trade')
        async def on_any_event(event, data):
            if event not in ['connect', 'disconnect', 'init']:
                logger.info(f"📡 EVENTO RECEBIDO: {event} - Dados: {data}")
    
    async def get_metadata(self):
        """Obtém metadata para autenticação."""
        try:
            if not self.settings.CSGOEMPIRE_API_KEY:
                logger.error("❌ API key do CSGOEmpire não configurada")
                return False
            
            url = "https://csgoempire.com/api/v2/metadata/socket"
            headers = {
                "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            
            logger.info(f"🔍 Obtendo metadata de: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    logger.info(f"📡 Resposta da API: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"📡 Dados recebidos: {data}")
                        
                        js_data = data.get('data') or data
                        
                        self.user_id = js_data.get('user', {}).get('id')
                        self.socket_token = js_data.get('socket_token')
                        self.socket_signature = js_data.get('socket_signature') or js_data.get('token_signature')
                        
                        logger.info(f"🔍 Dados extraídos:")
                        logger.info(f"   - User ID: {self.user_id}")
                        logger.info(f"   - Socket Token: {self.socket_token[:20] if self.socket_token else 'None'}...")
                        logger.info(f"   - Socket Signature: {self.socket_signature[:20] if self.socket_signature else 'None'}...")
                        
                        if all([self.user_id, self.socket_token, self.socket_signature]):
                            logger.info("✅ Metadata obtida com sucesso")
                            return True
                        else:
                            logger.error("❌ Dados de autenticação incompletos")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Erro ao obter metadata: {response.status}")
                        logger.error(f"❌ Resposta: {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadata: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def connect_websocket(self):
        """Conecta ao WebSocket."""
        try:
            if not all([self.user_id, self.socket_token, self.socket_signature]):
                logger.error("❌ Dados de autenticação incompletos")
                return False
            
            qs = f"uid={self.user_id}&token={self.socket_token}"
            logger.info(f"🔌 Conectando ao WebSocket: trade.csgoempire.com/?{qs}")
            
            await self.sio.connect(
                f"https://trade.csgoempire.com/?{qs}",
                socketio_path='s/',
                transports=['websocket'],
                namespaces=['/trade']
            )
            
            logger.info("🔌 WebSocket conectado")
            
            # Aguarda estabilizar
            await asyncio.sleep(3)
            
            if not self.sio.connected:
                logger.error("❌ WebSocket desconectado após conexão")
                return False
            
            if '/trade' not in self.sio.connected_namespaces:
                logger.error("❌ Namespace /trade não está conectado")
                return False
            
            logger.info("✅ WebSocket conectado com sucesso")
            return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def authenticate(self):
        """Tenta autenticar o usuário."""
        try:
            logger.info("🆔 Emitindo identify para autenticação...")
            
            identify_payload = {
                'uid': self.user_id,
                'authorizationToken': self.socket_token,
                'signature': self.socket_signature,
                'uuid': str(uuid.uuid4())
            }
            
            logger.info(f"🆔 Payload identify: {identify_payload}")
            
            await self.sio.emit('identify', identify_payload, namespace='/trade')
            
            logger.info("⏳ Aguardando autenticação...")
            await asyncio.sleep(5)
            
            if self.authenticated:
                logger.info("✅ Autenticação bem-sucedida!")
                return True
            else:
                logger.warning("⚠️ Autenticação falhou")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro durante autenticação: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def test_connection(self):
        """Testa a conexão completa."""
        try:
            logger.info("🧪 Iniciando teste de autenticação WebSocket...")
            
            # 1. Obtém metadata
            if not await self.get_metadata():
                return False
            
            # 2. Conecta ao WebSocket
            if not await self.connect_websocket():
                return False
            
            # 3. Tenta autenticar
            if not await self.authenticate():
                return False
            
            # 4. Aguarda um pouco para ver se recebe eventos
            logger.info("⏳ Aguardando eventos por 10 segundos...")
            await asyncio.sleep(10)
            
            # 5. Resultado final
            if self.authenticated:
                logger.info("🎉 TESTE PASSOU: Autenticação WebSocket funcionando!")
                return True
            else:
                logger.error("❌ TESTE FALHOU: Autenticação não funcionou")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro durante teste: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            await self.sio.disconnect()
    
    async def run(self):
        """Executa o teste."""
        try:
            success = await self.test_connection()
            return success
        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}")
            return False

async def main():
    """Função principal."""
    try:
        tester = WebSocketAuthTester()
        success = await tester.run()
        
        if success:
            logger.info("🎉 Teste de autenticação concluído com sucesso!")
            sys.exit(0)
        else:
            logger.error("❌ Teste de autenticação falhou!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Erro não tratado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Teste interrompido pelo usuário")
        sys.exit(1)
