#!/usr/bin/env python3
"""
Script para testar autenticação HTTP do CSGOEmpire.
Verifica se o problema é específico do WebSocket ou da autenticação em geral.
"""

import asyncio
import logging
import aiohttp
import time
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

class HTTPAuthTester:
    def __init__(self):
        self.settings = Settings()
        self.session = None
        self.user_id = None
        self.socket_token = None
        self.socket_signature = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def test_api_endpoints(self):
        """Testa diferentes endpoints da API do CSGOEmpire."""
        logger.info("🧪 Testando diferentes endpoints da API...")
        
        # Headers base
        headers = {
            "Authorization": f"Bearer {self.settings.CSGOEMPIRE_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://csgoempire.com/",
            "Origin": "https://csgoempire.com"
        }
        
        # Endpoints para testar
        endpoints = [
            ("/api/v2/metadata/socket", "Metadata do socket"),
            ("/api/v2/user", "Dados do usuário"),
            ("/api/v2/user/profile", "Perfil do usuário"),
            ("/api/v2/user/balance", "Saldo do usuário"),
            ("/api/v2/trade/items", "Itens de trade"),
            ("/api/v2/trade/history", "Histórico de trade")
        ]
        
        for endpoint, description in endpoints:
            try:
                url = f"https://csgoempire.com{endpoint}"
                logger.info(f"🧪 Testando: {description}")
                logger.info(f"   URL: {url}")
                
                async with self.session.get(url, headers=headers) as response:
                    logger.info(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"   ✅ Sucesso: {len(str(data))} caracteres")
                        
                        # Salva dados importantes
                        if endpoint == "/api/v2/metadata/socket":
                            if 'user' in data and 'socket_token' in data and 'socket_signature' in data:
                                self.user_id = data['user']['id']
                                self.socket_token = data['socket_token']
                                self.socket_signature = data['socket_signature']
                                logger.info(f"   📍 Dados extraídos: User ID {self.user_id}")
                                
                    elif response.status == 401:
                        logger.warning(f"   ⚠️ Não autorizado (401)")
                    elif response.status == 403:
                        logger.warning(f"   ⚠️ Proibido (403)")
                    elif response.status == 404:
                        logger.warning(f"   ⚠️ Não encontrado (404)")
                    else:
                        logger.warning(f"   ⚠️ Status inesperado: {response.status}")
                        
            except Exception as e:
                logger.error(f"   ❌ Erro: {e}")
                
    async def test_socket_connection_params(self):
        """Testa parâmetros de conexão do socket."""
        if not self.user_id or not self.socket_token:
            logger.error("❌ Dados de socket não disponíveis")
            return False
            
        logger.info("🔌 Testando parâmetros de conexão do socket...")
        
        # Testa diferentes URLs de conexão
        connection_urls = [
            f"https://trade.csgoempire.com/?uid={self.user_id}&token={self.socket_token}",
            f"https://trade.csgoempire.com/socket.io/?uid={self.user_id}&token={self.socket_token}",
            f"wss://trade.csgoempire.com/socket.io/?uid={self.user_id}&token={self.socket_token}",
            f"https://trade.csgoempire.com/?uid={self.user_id}&token={self.socket_token}&EIO=4&transport=websocket"
        ]
        
        for i, url in enumerate(connection_urls, 1):
            logger.info(f"🔌 Teste {i}: {url}")
            
            try:
                # Testa se a URL responde
                if url.startswith('https://'):
                    async with self.session.get(url) as response:
                        logger.info(f"   Status: {response.status}")
                        if response.status == 200:
                            logger.info(f"   ✅ URL responde")
                        else:
                            logger.info(f"   ⚠️ Status: {response.status}")
                else:
                    logger.info(f"   ⚠️ URL WebSocket (não testável via HTTP)")
                    
            except Exception as e:
                logger.error(f"   ❌ Erro: {e}")
                
    async def test_identify_payload_variations(self):
        """Testa variações do payload de identify."""
        if not self.user_id or not self.socket_token or not self.socket_signature:
            logger.error("❌ Dados de socket não disponíveis")
            return False
            
        logger.info("🆔 Testando variações do payload de identify...")
        
        # Diferentes variações do payload
        payloads = [
            {
                "name": "Padrão",
                "data": {
                    'uid': self.user_id,
                    'authorizationToken': self.socket_token,
                    'signature': self.socket_signature,
                    'uuid': 'test-uuid-123'
                }
            },
            {
                "name": "Sem UUID",
                "data": {
                    'uid': self.user_id,
                    'authorizationToken': self.socket_token,
                    'signature': self.socket_signature
                }
            },
            {
                "name": "Com timestamp",
                "data": {
                    'uid': self.user_id,
                    'authorizationToken': self.socket_token,
                    'signature': self.socket_signature,
                    'uuid': 'test-uuid-456',
                    'timestamp': int(time.time())
                }
            },
            {
                "name": "Campos em ordem diferente",
                "data": {
                    'uuid': 'test-uuid-789',
                    'signature': self.socket_signature,
                    'authorizationToken': self.socket_token,
                    'uid': self.user_id
                }
            }
        ]
        
        for payload_info in payloads:
            name = payload_info["name"]
            data = payload_info["data"]
            
            logger.info(f"🆔 Testando: {name}")
            logger.info(f"   Payload: {json.dumps(data, indent=2)}")
            
            # Aqui você pode testar enviando para um endpoint de teste
            # Por enquanto, apenas valida o formato
            try:
                # Valida se todos os campos obrigatórios estão presentes
                required_fields = ['uid', 'authorizationToken', 'signature']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    logger.warning(f"   ⚠️ Campos ausentes: {missing_fields}")
                else:
                    logger.info(f"   ✅ Todos os campos obrigatórios presentes")
                    
                # Valida tipos de dados
                if not isinstance(data['uid'], int):
                    logger.warning(f"   ⚠️ UID deve ser inteiro, recebido: {type(data['uid'])}")
                if not isinstance(data['authorizationToken'], str):
                    logger.warning(f"   ⚠️ Token deve ser string, recebido: {type(data['authorizationToken'])}")
                if not isinstance(data['signature'], str):
                    logger.warning(f"   ⚠️ Signature deve ser string, recebido: {type(data['signature'])}")
                    
            except Exception as e:
                logger.error(f"   ❌ Erro na validação: {e}")
                
    async def analyze_jwt_token(self):
        """Analisa o token JWT do socket."""
        if not self.socket_token:
            logger.error("❌ Token de socket não disponível")
            return False
            
        logger.info("🔍 Analisando token JWT...")
        
        try:
            import jwt
            payload = jwt.decode(self.socket_token, options={"verify_signature": False})
            
            logger.info(f"🔍 Payload JWT:")
            logger.info(f"   - Issuer (iss): {payload.get('iss', 'N/A')}")
            logger.info(f"   - Subject (sub): {payload.get('sub', 'N/A')}")
            logger.info(f"   - Audience (aud): {payload.get('aud', 'N/A')}")
            logger.info(f"   - Issued at (iat): {payload.get('iat', 'N/A')}")
            logger.info(f"   - Expires at (exp): {payload.get('exp', 'N/A')}")
            logger.info(f"   - JWT ID (jti): {payload.get('jti', 'N/A')}")
            
            # Verifica expiração
            if 'exp' in payload:
                current_time = int(time.time())
                exp_time = payload['exp']
                time_until_expiry = exp_time - current_time
                
                logger.info(f"🔍 Tempo:")
                logger.info(f"   - Tempo atual: {current_time} ({time.ctime(current_time)})")
                logger.info(f"   - Expira em: {exp_time} ({time.ctime(exp_time)})")
                logger.info(f"   - Tempo até expiração: {time_until_expiry} segundos")
                
                if time_until_expiry <= 0:
                    logger.error("❌ Token JWT EXPIRADO!")
                elif time_until_expiry < 60:
                    logger.warning("⚠️ Token JWT expira em menos de 1 minuto!")
                elif time_until_expiry < 300:
                    logger.warning("⚠️ Token JWT expira em menos de 5 minutos!")
                else:
                    logger.info("✅ Token JWT válido por mais de 5 minutos")
                    
        except ImportError:
            logger.error("❌ Biblioteca JWT não disponível. Instale com: pip install PyJWT")
        except Exception as e:
            logger.error(f"❌ Erro ao analisar JWT: {e}")
            
    async def run_tests(self):
        """Executa todos os testes."""
        try:
            logger.info("🧪 INICIANDO TESTES DE AUTENTICAÇÃO HTTP")
            
            # 1. Testa endpoints da API
            await self.test_api_endpoints()
            
            # 2. Analisa token JWT
            await self.analyze_jwt_token()
            
            # 3. Testa parâmetros de conexão
            await self.test_socket_connection_params()
            
            # 4. Testa variações do payload
            await self.test_identify_payload_variations()
            
            logger.info("✅ TESTES CONCLUÍDOS")
            
        except Exception as e:
            logger.error(f"❌ Erro durante testes: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
async def main():
    async with HTTPAuthTester() as tester:
        await tester.run_tests()
        
if __name__ == "__main__":
    asyncio.run(main())
