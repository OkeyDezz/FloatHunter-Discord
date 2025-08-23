#!/usr/bin/env python3
"""
Script robusto para testar a autenticação WebSocket do CSGOEmpire.
Resolve os problemas de "Identify failed. Please refresh."
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class RobustWebSocketTester:
    def __init__(self):
        self.settings = Settings()
        self.sio = socketio.AsyncClient()
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        self.authenticated = False
        self._setup_events()
    
    def _setup_events(self):
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
        
        @self.sio.on('err', namespace='/trade')
        async def on_error(data):
            logger.error(f"❌ ERRO RECEBIDO: {data}")
            if isinstance(data, dict):
                error_msg = data.get('error', 'Unknown error')
                if 'Identify failed' in error_msg:
                    logger.error("🚨 PROBLEMA CRÍTICO: Identify failed - token pode estar expirado ou payload incorreto")
        
        @self.sio.on('*', namespace='/trade')
        async def on_any_event(event, data):
            if event not in ['connect', 'disconnect', 'init', 'err']:
                logger.info(f"📡 EVENTO RECEBIDO: {event} - Dados: {data}")
    
    async def get_fresh_metadata(self):
        """Obtém metadata FRESCA imediatamente antes de usar."""
        try:
            logger.info("🔍 Obtendo metadata FRESCA...")
            url = "https://csgoempire.com/api/v2/metadata/socket"
            headers = {
                "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"❌ API retornou {response.status}")
                        return False
                    
                    data = await response.json()
                    js_data = data.get('data') or data
                    
                    self.user_id = js_data.get('user', {}).get('id')
                    self.socket_token = js_data.get('socket_token')
                    self.socket_signature = js_data.get('socket_signature') or js_data.get('token_signature')
                    
                    if not all([self.user_id, self.socket_token, self.socket_signature]):
                        logger.error("❌ Metadata incompleta")
                        return False
                    
                    logger.info(f"✅ Metadata FRESCA obtida: User ID {self.user_id}")
                    logger.info(f"   Token: {self.socket_token[:30]}...")
                    logger.info(f"   Signature: {self.socket_signature[:30]}...")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadata: {e}")
            return False
    
    async def connect_websocket(self):
        """Conecta ao WebSocket com metadata FRESCA."""
        try:
            # Obtém metadata FRESCA imediatamente antes de conectar
            if not await self.get_fresh_metadata():
                return False
            
            logger.info("🔌 Conectando ao WebSocket...")
            
            # Conecta com metadata FRESCA
            qs = f"uid={self.user_id}&token={self.socket_token}"
            await self.sio.connect(
                f"https://trade.csgoempire.com/?{qs}",
                socketio_path='s/',
                transports=['websocket'],
                namespaces=['/trade'],
                wait_timeout=10
            )
            
            logger.info("✅ WebSocket conectado")
            await asyncio.sleep(2)
            
            # Verifica namespace
            if '/trade' in self.sio.connection_namespaces:
                logger.info("✅ Namespace /trade conectado")
                return True
            else:
                logger.error("❌ Namespace /trade não conectado")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            return False
    
    async def authenticate_immediately(self):
        """Autentica IMEDIATAMENTE após conectar, sem delay."""
        try:
            logger.info("🆔 Autenticando IMEDIATAMENTE...")
            
            # Tenta autenticar várias vezes com metadata FRESCA
            for attempt in range(3):
                logger.info(f"🔄 Tentativa de autenticação {attempt + 1}/3")
                
                # Obtém metadata FRESCA para cada tentativa
                if not await self.get_fresh_metadata():
                    logger.error("❌ Falha ao obter metadata fresca")
                    return False
                
                identify_payload = {
                    'uid': self.user_id,
                    'authorizationToken': self.socket_token,
                    'signature': self.socket_signature,
                    'uuid': str(uuid.uuid4())
                }
                
                logger.info(f"🆔 Payload identify: {identify_payload}")
                
                await self.sio.emit('identify', identify_payload, namespace='/trade')
                
                logger.info("⏳ Aguardando autenticação...")
                await asyncio.sleep(3)  # Reduzido para 3 segundos
                
                if self.authenticated:
                    logger.info("✅ Autenticação bem-sucedida!")
                    return True
                else:
                    logger.warning(f"⚠️ Tentativa {attempt + 1} falhou")
                    if attempt < 2:  # Não aguarda na última tentativa
                        await asyncio.sleep(1)
            
            logger.error("❌ Todas as tentativas de autenticação falharam")
            return False
                
        except Exception as e:
            logger.error(f"❌ Erro durante autenticação: {e}")
            return False
    
    async def test_connection(self):
        """Testa a conexão completa com abordagem robusta."""
        try:
            logger.info("🧪 TESTE ROBUSTO de autenticação WebSocket")
            
            # 1. Conecta ao WebSocket
            if not await self.connect_websocket():
                return False
            
            # 2. Autentica IMEDIATAMENTE
            if not await self.authenticate_immediately():
                logger.error("❌ Autenticação falhou")
                return False
            
            # 3. Aguarda eventos
            logger.info("⏳ Aguardando eventos por 15 segundos...")
            await asyncio.sleep(15)
            
            # 4. Resultado final
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
            if success:
                logger.info("🎉 Teste concluído com sucesso!")
            else:
                logger.error("❌ Teste falhou!")
            return success
        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}")
            return False

async def main():
    """Função principal."""
    tester = RobustWebSocketTester()
    try:
        return await tester.run()
    except KeyboardInterrupt:
        logger.info("🛑 Teste interrompido pelo usuário")
        return False
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
