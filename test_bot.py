#!/usr/bin/env python3
"""
Script de teste para o Opportunity Bot.
Testa conexão com Supabase e configurações básicas.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Adiciona o diretório atual ao path
sys.path.insert(0, str(Path(__file__).parent))

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_supabase_connection():
    """Testa conexão com Supabase."""
    try:
        logger.info("🧪 Testando conexão com Supabase...")
        
        from utils.supabase_client import SupabaseClient
        supabase = SupabaseClient()
        
        if await supabase.test_connection():
            logger.info("✅ Conexão com Supabase OK")
            return True
        else:
            logger.error("❌ Falha na conexão com Supabase")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar Supabase: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_settings():
    """Testa configurações do bot."""
    try:
        logger.info("🧪 Testando configurações...")
        
        from config.settings import Settings
        settings = Settings()
        
        logger.info(f"✅ Configurações carregadas:")
        logger.info(f"   - CSGOEMPIRE_API_KEY: {'✅' if settings.CSGOEMPIRE_API_KEY else '❌'}")
        logger.info(f"   - DISCORD_TOKEN: {'✅' if settings.DISCORD_BOT_TOKEN else '❌'}")
        logger.info(f"   - CSGOEMPIRE_CHANNEL_ID: {'✅' if settings.DISCORD_CHANNEL_ID else '❌'}")
        logger.info(f"   - SUPABASE_URL: {'✅' if settings.SUPABASE_URL else '❌'}")
        logger.info(f"   - SUPABASE_ANON_KEY: {'✅' if settings.SUPABASE_KEY else '❌'}")
        logger.info(f"   - MIN_PRICE: ${settings.MIN_PRICE:.2f}")
        logger.info(f"   - MAX_PRICE: ${settings.MAX_PRICE:.2f}")
        logger.info(f"   - MIN_PROFIT_PERCENTAGE: {settings.MIN_PROFIT_PERCENTAGE:.1f}%")
        logger.info(f"   - MIN_LIQUIDITY_SCORE: {settings.MIN_LIQUIDITY_SCORE:.1f}")
        logger.info(f"   - COIN_TO_USD_FACTOR: {settings.COIN_TO_USD_FACTOR}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar configurações: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_discord_poster():
    """Testa o sistema de postagem no Discord."""
    try:
        logger.info("🧪 Testando Discord Poster...")
        
        from core.discord_poster import DiscordPoster
        poster = DiscordPoster()
        
        # Testa se as configurações estão presentes
        if not poster.webhook_url and not poster.bot_token:
            logger.warning("⚠️ Discord webhook URL ou bot token não configurado")
            return False
        
        if not poster.channel_id:
            logger.warning("⚠️ Discord channel ID não configurado")
            return False
        
        logger.info("✅ Discord Poster configurado corretamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar Discord Poster: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_filters():
    """Testa os filtros do bot."""
    try:
        logger.info("🧪 Testando filtros...")
        
        from filters.profit_filter import ProfitFilter
        from filters.liquidity_filter import LiquidityFilter
        
        # Testa filtro de lucro
        profit_filter = ProfitFilter()
        logger.info(f"✅ Filtro de lucro criado com lucro mínimo: {profit_filter.get_min_profit_percentage()}%")
        
        # Testa filtro de liquidez
        liquidity_filter = LiquidityFilter()
        logger.info(f"✅ Filtro de liquidez criado com score mínimo: {liquidity_filter.get_min_liquidity_score()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar filtros: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_metadata_api():
    """Testa a API de metadata do CSGOEmpire."""
    try:
        logger.info("🧪 Testando API de metadata do CSGOEmpire...")
        
        from config.settings import Settings
        settings = Settings()
        
        if not settings.CSGOEMPIRE_API_KEY:
            logger.warning("⚠️ CSGOEMPIRE_API_KEY não configurada")
            return False
        
        import aiohttp
        
        url = "https://csgoempire.com/api/v2/metadata/socket"
        headers = {
            "Authorization": f"Bearer {settings.CSGOEMPIRE_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        logger.info(f"🔍 Testando URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                logger.info(f"📡 Resposta: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    logger.info("✅ API de metadata funcionando")
                    logger.info(f"📊 Dados recebidos: {data}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Erro na API: {response.status}")
                    logger.error(f"❌ Resposta: {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Erro ao testar API de metadata: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Função principal de teste."""
    try:
        logger.info("🚀 Iniciando testes do Opportunity Bot...")
        
        tests = [
            ("Configurações", test_settings),
            ("Supabase", test_supabase_connection),
            ("Discord Poster", test_discord_poster),
            ("Filtros", test_filters),
            ("API Metadata", test_metadata_api),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"🧪 Testando: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = await test_func()
                results[test_name] = result
                
                if result:
                    logger.info(f"✅ {test_name}: OK")
                else:
                    logger.error(f"❌ {test_name}: FALHOU")
                    
            except Exception as e:
                logger.error(f"❌ {test_name}: ERRO - {e}")
                results[test_name] = False
        
        # Resumo dos testes
        logger.info(f"\n{'='*50}")
        logger.info("📊 RESUMO DOS TESTES")
        logger.info(f"{'='*50}")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
        
        logger.info(f"\n🎯 Resultado: {passed}/{total} testes passaram")
        
        if passed == total:
            logger.info("🎉 Todos os testes passaram! O bot está configurado corretamente.")
        else:
            logger.warning("⚠️ Alguns testes falharam. Verifique as configurações.")
        
        return passed == total
        
    except Exception as e:
        logger.error(f"❌ Erro fatal nos testes: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Testes interrompidos pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro não tratado: {e}")
        sys.exit(1)
