#!/usr/bin/env python3
"""
Script de teste básico para o Opportunity Bot.
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Testa se todos os módulos podem ser importados."""
    try:
        print("🧪 Testando imports...")
        
        # Testa configurações
        from config.settings import Settings
        print("✅ Configurações importadas")
        
        # Testa filtros
        from filters.profit_filter import ProfitFilter
        from filters.liquidity_filter import LiquidityFilter
        print("✅ Filtros importados")
        
        # Testa core
        from core.marketplace_scanner import MarketplaceScanner
        from core.discord_poster import DiscordPoster
        print("✅ Core importado")
        
        print("\n🎉 Todos os imports funcionaram!")
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def test_config():
    """Testa a configuração básica."""
    try:
        print("\n🔧 Testando configuração...")
        
        from config.settings import Settings
        settings = Settings()
        
        print(f"   Min Profit: {settings.MIN_PROFIT_PERCENTAGE}%")
        print(f"   Min Liquidity: {settings.MIN_LIQUIDITY_SCORE}")
        print(f"   Price Range: ${settings.MIN_PRICE} - ${settings.MAX_PRICE}")
        print(f"   Scan Interval: {settings.SCAN_INTERVAL_SECONDS}s")
        
        print("✅ Configuração carregada")
        return True
        
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        return False

def test_filters():
    """Testa os filtros básicos."""
    try:
        print("\n🎯 Testando filtros...")
        
        from filters.profit_filter import ProfitFilter
        from filters.liquidity_filter import LiquidityFilter
        
        profit_filter = ProfitFilter(5.0)
        liquidity_filter = LiquidityFilter(0.7)
        
        # Item de teste
        test_item = {
            'name': 'AK-47 | Redline',
            'price': 25.50,
            'market_hash_name': 'AK-47 | Redline (Field-Tested)'
        }
        
        profit_result = profit_filter.check(test_item)
        liquidity_result = liquidity_filter.check(test_item)
        
        print(f"   Item: {test_item['name']}")
        print(f"   Preço: ${test_item['price']}")
        print(f"   Passou filtro de lucro: {'✅' if profit_result else '❌'}")
        print(f"   Passou filtro de liquidez: {'✅' if liquidity_result else '❌'}")
        
        print("✅ Filtros funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos filtros: {e}")
        return False

def main():
    """Função principal de teste."""
    print("🚀 Iniciando testes do Opportunity Bot...\n")
    
    tests = [
        test_imports,
        test_config,
        test_filters
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Resultados: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Todos os testes passaram! O bot está pronto para uso.")
        return 0
    else:
        print("❌ Alguns testes falharam. Verifique os erros acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
