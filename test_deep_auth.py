#!/usr/bin/env python3
"""
Script para investigação profunda da autenticação WebSocket do CSGOEmpire.
Testa diferentes abordagens e analisa o protocolo.
"""

import asyncio
import logging
import socketio
import aiohttp
import time
import uuid
import json
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

class DeepAuthInvestigator:
    def __init__(self):
        self.settings = Settings()
        self.sio = socketio.AsyncClient(
            logger=True,
            engineio_logger=True,
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1
        )
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
            if isinstance(data, dict) and data.get('error') == 'Identify failed. Please refresh.':
                logger.error("🚨 PROBLEMA CRÍTICO: Identify failed - analisando payload...")
                await self._analyze_failed_identify()
                
        @self.sio.on('*', namespace='/trade')
        async def on_any_event(event, data):
            if event not in ['connect', 'disconnect', 'init', 'err']:
                logger.info(f"📡 EVENTO RECEBIDO: {event} - Dados: {data}")
                
    async def _analyze_failed_identify(self):
        """Analisa por que o identify falhou."""
        logger.info("🔍 Analisando falha de autenticação...")
        
        # Verifica se o token expirou
        if self.socket_token:
            try:
                import jwt
                payload = jwt.decode(self.socket_token, options={"verify_signature": False})
                exp = payload.get('exp')
                iat = payload.get('iat')
                if exp and iat:
                    current_time = int(time.time())
                    logger.info(f"🔍 Token JWT:")
                    logger.info(f"   - Issued at: {iat} ({time.ctime(iat)})")
                    logger.info(f"   - Expires at: {exp} ({time.ctime(exp)})")
                    logger.info(f"   - Current time: {current_time} ({time.ctime(current_time)})")
                    logger.info(f"   - Time until expiry: {exp - current_time} segundos")
                    if current_time >= exp:
                        logger.error("❌ Token JWT EXPIRADO!")
                    else:
                        logger.info("✅ Token JWT ainda válido")
            except Exception as e:
                logger.error(f"❌ Erro ao decodificar JWT: {e}")
                
    async def get_metadata(self):
        """Obtém metadata do socket do CSGOEmpire."""
        try:
            logger.info("🔍 Obtendo metadata do socket...")
            url = "https://csgoempire.com/api/v2/metadata/socket"
            headers = {
                "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": "https://csgoempire.com/",
                "Origin": "https://csgoempire.com"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    logger.info(f"📡 Resposta da API: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"📡 Dados recebidos: {data}")
                        
                        if 'user' in data and 'socket_token' in data and 'socket_signature' in data:
                            self.user_id = data['user']['id']
                            self.socket_token = data['socket_token']
                            self.socket_signature = data['socket_signature']
                            
                            logger.info(f"🔍 Dados extraídos:")
                            logger.info(f"   - User ID: {self.user_id}")
                            logger.info(f"   - Socket Token: {self.socket_token[:50]}...")
                            logger.info(f"   - Socket Signature: {self.socket_signature[:50]}...")
                            
                            return True
                        else:
                            logger.error("❌ Dados incompletos na resposta")
                            return False
                    else:
                        logger.error(f"❌ Erro na API: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao obter metadata: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    async def connect_websocket(self):
        """Conecta ao WebSocket do CSGOEmpire."""
        try:
            logger.info("🔌 Conectando ao WebSocket...")
            
            # URL de conexão
            url = f"https://trade.csgoempire.com/?uid={self.user_id}&token={self.socket_token}"
            logger.info(f"🔌 URL de conexão: {url}")
            
            # Conecta com configurações específicas
            await self.sio.connect(
                url,
                namespaces=['/trade'],
                transports=['websocket'],
                wait_timeout=10,
                socketio_path='socket.io'
            )
            
            # Aguarda conexão
            await asyncio.sleep(3)
            
            if not self.sio.connected:
                logger.error("❌ WebSocket não conectado")
                return False
                
            if '/trade' not in self.sio.connection_namespaces:
                logger.error("❌ Namespace /trade não conectado")
                return False
                
            logger.info("✅ WebSocket conectado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar WebSocket: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    async def test_different_payloads(self):
        """Testa diferentes formatos de payload para identify."""
        logger.info("🧪 Testando diferentes formatos de payload...")
        
        # Teste 1: Payload padrão
        payload1 = {
            'uid': self.user_id,
            'authorizationToken': self.socket_token,
            'signature': self.socket_signature,
            'uuid': str(uuid.uuid4())
        }
        
        # Teste 2: Payload sem uuid
        payload2 = {
            'uid': self.user_id,
            'authorizationToken': self.socket_token,
            'signature': self.socket_signature
        }
        
        # Teste 3: Payload com campos adicionais
        payload3 = {
            'uid': self.user_id,
            'authorizationToken': self.socket_token,
            'signature': self.socket_signature,
            'uuid': str(uuid.uuid4()),
            'timestamp': int(time.time())
        }
        
        # Teste 4: Payload com campos em ordem diferente
        payload4 = {
            'uuid': str(uuid.uuid4()),
            'signature': self.socket_signature,
            'authorizationToken': self.socket_token,
            'uid': self.user_id
        }
        
        payloads = [
            ("Padrão", payload1),
            ("Sem UUID", payload2),
            ("Com timestamp", payload3),
            ("Ordem diferente", payload4)
        ]
        
        for name, payload in payloads:
            logger.info(f"🧪 Testando payload: {name}")
            logger.info(f"   Payload: {payload}")
            
            try:
                await self.sio.emit('identify', payload, namespace='/trade')
                logger.info(f"   ✅ Payload enviado")
                
                # Aguarda resposta
                await asyncio.sleep(3)
                
                if self.authenticated:
                    logger.info(f"   🎉 AUTENTICAÇÃO BEM-SUCEDIDA com payload: {name}")
                    return True
                else:
                    logger.info(f"   ❌ Falhou")
                    
            except Exception as e:
                logger.error(f"   ❌ Erro ao enviar: {e}")
                
        return False
        
    async def test_connection_timing(self):
        """Testa diferentes timings de conexão."""
        logger.info("⏱️ Testando diferentes timings...")
        
        # Aguarda mais tempo após conexão
        logger.info("⏱️ Aguardando 5 segundos após conexão...")
        await asyncio.sleep(5)
        
        if not self.authenticated:
            logger.info("⏱️ Tentando autenticação após delay...")
            return await self.test_different_payloads()
            
        return False
        
    async def run_investigation(self):
        """Executa a investigação completa."""
        try:
            logger.info("🔍 INICIANDO INVESTIGAÇÃO PROFUNDA DE AUTENTICAÇÃO")
            
            # 1. Obtém metadata
            if not await self.get_metadata():
                logger.error("❌ Falha ao obter metadata")
                return False
                
            # 2. Conecta ao WebSocket
            if not await self.connect_websocket():
                logger.error("❌ Falha ao conectar WebSocket")
                return False
                
            # 3. Aguarda evento init
            logger.info("⏳ Aguardando evento init...")
            await asyncio.sleep(5)
            
            # 4. Testa diferentes payloads
            if not await self.test_different_payloads():
                logger.warning("⚠️ Todos os payloads falharam, testando timing...")
                
                # 5. Testa timing
                if not await self.test_connection_timing():
                    logger.error("❌ Todas as tentativas falharam")
                    return False
                    
            # 6. Aguarda mais eventos
            logger.info("⏳ Aguardando mais eventos para análise...")
            await asyncio.sleep(10)
            
            if self.authenticated:
                logger.info("🎉 INVESTIGAÇÃO CONCLUÍDA: Autenticação bem-sucedida!")
                return True
            else:
                logger.error("❌ INVESTIGAÇÃO CONCLUÍDA: Autenticação falhou")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro durante investigação: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            await self.sio.disconnect()
            
async def main():
    investigator = DeepAuthInvestigator()
    success = await investigator.run_investigation()
    
    if success:
        logger.info("✅ Investigação bem-sucedida!")
    else:
        logger.error("❌ Investigação falhou!")
        
if __name__ == "__main__":
    asyncio.run(main())
