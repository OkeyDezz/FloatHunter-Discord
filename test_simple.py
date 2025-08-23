#!/usr/bin/env python3
"""
Script simples para testar a autenticação WebSocket do CSGOEmpire.
Foca apenas no problema de autenticação.
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

async def test_auth():
    """Testa apenas a autenticação."""
    try:
        logger.info("🧪 Teste simples de autenticação WebSocket")
        
        # Carrega configurações
        settings = Settings()
        if not settings.CSGOEMPIRE_API_KEY:
            logger.error("❌ CSGOEMPIRE_API_KEY não configurada")
            return False
        
        # 1. Obtém metadata
        logger.info("🔍 Obtendo metadata...")
        url = "https://csgoempire.com/api/v2/metadata/socket"
        headers = {
            "Authorization": f"Bearer {settings.CSGOEMPIRE_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"❌ API retornou {response.status}")
                    return False
                
                data = await response.json()
                js_data = data.get('data') or data
                
                user_id = js_data.get('user', {}).get('id')
                socket_token = js_data.get('socket_token')
                socket_signature = js_data.get('socket_signature') or js_data.get('token_signature')
                
                logger.info(f"✅ Metadata obtida: User ID {user_id}")
                logger.info(f"   Token: {socket_token[:20]}...")
                logger.info(f"   Signature: {socket_signature[:20]}...")
        
        # 2. Testa WebSocket
        logger.info("🔌 Testando WebSocket...")
        sio = socketio.AsyncClient()
        
        # Handler simples
        @sio.on('init', namespace='/trade')
        async def on_init(data):
            logger.info(f"📡 Init recebido: {data}")
            if isinstance(data, dict):
                auth = data.get('authenticated', False)
                guest = data.get('isGuest', True)
                logger.info(f"   Authenticated: {auth}, IsGuest: {guest}")
        
        # Conecta
        qs = f"uid={user_id}&token={socket_token}"
        await sio.connect(
            f"https://trade.csgoempire.com/?{qs}",
            socketio_path='s/',
            transports=['websocket'],
            namespaces=['/trade']
        )
        
        logger.info("✅ WebSocket conectado")
        await asyncio.sleep(3)
        
        # Verifica namespace
        if '/trade' in sio.connection_namespaces:
            logger.info("✅ Namespace /trade conectado")
        else:
            logger.error("❌ Namespace /trade não conectado")
            return False
        
        # 3. Tenta autenticar
        logger.info("🆔 Tentando autenticar...")
        identify_payload = {
            'uid': user_id,
            'authorizationToken': socket_token,
            'signature': socket_signature,
            'uuid': str(uuid.uuid4())
        }
        
        await sio.emit('identify', identify_payload, namespace='/trade')
        logger.info("✅ Identify enviado")
        
        # Aguarda resposta
        await asyncio.sleep(5)
        
        # 4. Resultado
        logger.info("🎯 Teste concluído!")
        logger.info("💡 Verifique os logs acima para diagnosticar o problema")
        
        await sio.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Função principal."""
    try:
        success = await test_auth()
        if success:
            logger.info("🎉 Teste concluído com sucesso!")
        else:
            logger.error("❌ Teste falhou!")
        return success
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Teste interrompido")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
