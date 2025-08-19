#!/usr/bin/env python3
"""
Test Simple - Script ultra-simples para forçar Railway a usar o script correto.
"""

import asyncio
import logging
import sys
import time

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_websocket_simple():
    """Teste simples de WebSocket."""
    try:
        logger.info("🧪 TESTE SIMPLES: Iniciando...")
        
        # Testa import das configurações
        try:
            from config.settings import Settings
            settings = Settings()
            logger.info("✅ Configurações carregadas")
            
            if settings.CSGOEMPIRE_API_KEY:
                logger.info(f"✅ API Key: {settings.CSGOEMPIRE_API_KEY[:10]}...")
            else:
                logger.warning("⚠️ API Key não configurada")
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar configurações: {e}")
            return False
        
        # Testa import do aiohttp
        try:
            import aiohttp
            logger.info("✅ aiohttp importado")
        except Exception as e:
            logger.error(f"❌ Erro ao importar aiohttp: {e}")
            return False
        
        # Testa import do socketio
        try:
            import socketio
            logger.info("✅ socketio importado")
        except Exception as e:
            logger.error(f"❌ Erro ao importar socketio: {e}")
            return False
        
        # Testa endpoint metadata
        try:
            logger.info("🔍 Testando endpoint metadata...")
            
            headers = {
                'Authorization': f'Bearer {settings.CSGOEMPIRE_API_KEY}',
                'User-Agent': 'CSGOEmpire Test Bot'
            }
            
            async with aiohttp.ClientSession() as session:
                url = "https://csgoempire.com/api/v2/metadata/socket"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        logger.info("✅ Metadata obtida!")
                        logger.info(f"   - Usuário: {user_data.get('user', {}).get('name', 'Unknown')}")
                        logger.info(f"   - UID: {user_data.get('user', {}).get('id', 'Unknown')}")
                    else:
                        logger.error(f"❌ Metadata falhou: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro no endpoint metadata: {e}")
            return False
        
        # Testa WebSocket básico
        try:
            logger.info("🔗 Testando WebSocket básico...")
            
            sio = socketio.AsyncClient(transports=['websocket'])
            
            @sio.event
            async def connect():
                logger.info("✅ WebSocket conectado!")
                
            @sio.event
            async def disconnect():
                logger.info("❌ WebSocket desconectado!")
                
            @sio.event
            async def init(data):
                logger.info(f"🚀 INIT: {data}")
                
            @sio.event
            async def new_item(data):
                logger.info(f"🆕 ITEM: {len(data) if isinstance(data, list) else 1}")
                
            # Conecta
            socket_endpoint = "wss://trade.csgoempire.com/trade"
            query_params = {
                'uid': user_data['user']['id'],
                'token': user_data['socket_token']
            }
            
            logger.info(f"🔗 Conectando a: {socket_endpoint}")
            await sio.connect(
                socket_endpoint,
                query=query_params,
                wait_timeout=30
            )
            
            logger.info("✅ WebSocket conectado com sucesso!")
            
            # Aguarda eventos
            logger.info("⏳ Aguardando eventos por 30 segundos...")
            await asyncio.sleep(30)
            
            # Desconecta
            await sio.disconnect()
            logger.info("✅ Teste WebSocket concluído!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no WebSocket: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro geral no teste: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Função principal."""
    try:
        logger.info("🚀 TESTE SIMPLES INICIADO!")
        logger.info("=" * 50)
        
        success = await test_websocket_simple()
        
        logger.info("=" * 50)
        if success:
            logger.info("🎉 TESTE PASSOU! WebSocket funcionando!")
        else:
            logger.error("❌ TESTE FALHOU! WebSocket com problemas!")
            
        # Loop infinito para manter processo vivo
        logger.info("🔄 Mantendo processo vivo para Railway...")
        cycle = 0
        while True:
            cycle += 1
            await asyncio.sleep(30)
            logger.info(f"💓 Processo vivo - Ciclo #{cycle}")
            
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        
        # Loop de emergência
        cycle = 0
        while True:
            cycle += 1
            time.sleep(30)
            print(f"🚨 Emergência - Ciclo #{cycle}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        
        # Último recurso
        cycle = 0
        while True:
            cycle += 1
            time.sleep(30)
            print(f"💀 Último recurso - Ciclo #{cycle}")
