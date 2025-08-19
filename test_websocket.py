#!/usr/bin/env python3
"""
Test WebSocket - Script para testar conexão WebSocket do CSGOEmpire.
"""

import asyncio
import logging
import json
import time
import os
from typing import Dict
import aiohttp
import socketio

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_websocket():
    """Testa conexão WebSocket do CSGOEmpire."""
    try:
        logger.info("🧪 TESTE: Iniciando teste de WebSocket...")
        
        # Carrega configurações
        from config.settings import Settings
        settings = Settings()
        
        if not settings.CSGOEMPIRE_API_KEY:
            logger.error("❌ CSGOEMPIRE_API_KEY não configurada")
            return False
        
        logger.info(f"✅ API Key configurada: {settings.CSGOEMPIRE_API_KEY[:10]}...")
        
        # Testa metadata endpoint
        logger.info("🔍 Testando endpoint metadata/socket...")
        
        headers = {
            'Authorization': f'Bearer {settings.CSGOEMPIRE_API_KEY}',
            'User-Agent': 'CSGOEmpire Test Bot'
        }
        
        async with aiohttp.ClientSession() as session:
            url = "https://csgoempire.com/api/v2/metadata/socket"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    logger.info("✅ Metadata obtida com sucesso!")
                    logger.info(f"   - Usuário: {user_data.get('user', {}).get('name', 'Unknown')}")
                    logger.info(f"   - UID: {user_data.get('user', {}).get('id', 'Unknown')}")
                    logger.info(f"   - Socket Token: {'✅' if user_data.get('socket_token') else '❌'}")
                    logger.info(f"   - Socket Signature: {'✅' if user_data.get('socket_signature') else '❌'}")
                else:
                    logger.error(f"❌ Falha ao obter metadata: {response.status}")
                    return False
        
        # Testa WebSocket
        logger.info("🔗 Testando conexão WebSocket...")
        
        # Cria Socket.IO client
        sio = socketio.AsyncClient(
            transports=['websocket'],
            logger=True,
            engineio_logger=True
        )
        
        # Configura eventos básicos
        @sio.event
        async def connect():
            logger.info("✅ WebSocket conectado!")
            
        @sio.event
        async def disconnect():
            logger.warning("❌ WebSocket desconectado!")
            
        @sio.event
        async def connect_error(data):
            logger.error(f"❌ Erro de conexão: {data}")
            
        @sio.event
        async def init(data):
            logger.info(f"🚀 Evento INIT: {json.dumps(data, indent=2)}")
            
        @sio.event
        async def new_item(data):
            logger.info(f"🆕 NOVO ITEM: {len(data) if isinstance(data, list) else 1} item(s)")
            
        @sio.event
        async def updated_item(data):
            logger.info(f"🔄 ITEM ATUALIZADO: {len(data) if isinstance(data, list) else 1} item(s)")
            
        @sio.event
        async def deleted_item(data):
            logger.info(f"🗑️ ITEM DELETADO: {len(data) if isinstance(data, list) else 1} item(s)")
        
        # Conecta ao WebSocket
        try:
            socket_endpoint = "wss://trade.csgoempire.com/trade"
            
            query_params = {
                'uid': user_data['user']['id'],
                'token': user_data['socket_token']
            }
            
            extra_headers = {
                'User-agent': f"{user_data['user']['id']} Test Bot"
            }
            
            logger.info(f"🔗 Conectando a: {socket_endpoint}")
            logger.info(f"   - UID: {query_params['uid']}")
            logger.info(f"   - Token: {query_params['token'][:10]}...")
            
            await sio.connect(
                socket_endpoint,
                query=query_params,
                headers=extra_headers,
                wait_timeout=30
            )
            
            logger.info("✅ WebSocket conectado com sucesso!")
            
            # Aguarda alguns eventos
            logger.info("⏳ Aguardando eventos por 60 segundos...")
            await asyncio.sleep(60)
            
            # Desconecta
            await sio.disconnect()
            logger.info("✅ Teste concluído com sucesso!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha na conexão WebSocket: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Função principal."""
    try:
        logger.info("🚀 Iniciando teste de WebSocket CSGOEmpire...")
        
        success = await test_websocket()
        
        if success:
            logger.info("🎉 TESTE PASSOU! WebSocket funcionando!")
        else:
            logger.error("❌ TESTE FALHOU! WebSocket com problemas!")
            
    except Exception as e:
        logger.error(f"❌ Erro fatal no teste: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
