"""
Sistema de postagem no Discord para o Opportunity Bot.
Versão simplificada usando apenas webhooks - sem dependência do discord.py.
"""

import aiohttp
import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime
from config.settings import Settings

logger = logging.getLogger(__name__)

class DiscordPoster:
    """Gerencia postagens no Discord usando webhooks."""
    
    def __init__(self):
        self.settings = Settings()
        self.webhook_url = self.settings.DISCORD_WEBHOOK_URL
        self.bot_token = self.settings.DISCORD_BOT_TOKEN
        self.channel_id = self.settings.DISCORD_CHANNEL_ID
        
        if not self.webhook_url and not self.bot_token:
            logger.warning("⚠️ Discord webhook URL ou bot token não configurado")
        
        if not self.channel_id:
            logger.warning("⚠️ Discord channel ID não configurado")
    
    async def post_opportunity(self, item: Dict) -> bool:
        """
        Posta uma oportunidade no Discord usando webhook ou bot token.
        
        Args:
            item: Dicionário com dados do item
            
        Returns:
            bool: True se enviou com sucesso, False caso contrário
        """
        try:
            if not self.webhook_url and not self.bot_token:
                logger.error("❌ Discord webhook URL ou bot token não configurado")
                return False
            
            if not self.channel_id:
                logger.error("❌ Discord channel ID não configurado")
                return False
            
            # Prepara os dados do embed
            embed = self._create_embed(item)
            
            # Prepara o payload do webhook
            payload = {
                "embeds": [embed],
                "username": "Opportunity Bot",
                "avatar_url": "https://i.imgur.com/4M34hi2.png"
            }
            
            # Envia via webhook ou bot token
            if self.webhook_url:
                # Usa webhook
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, json=payload) as response:
                        if response.status == 204:
                            logger.info(f"✅ Oportunidade enviada para Discord via webhook: {item.get('name', 'Unknown')}")
                            return True
                        else:
                            logger.error(f"❌ Erro ao enviar via webhook: {response.status}")
                            error_text = await response.text()
                            logger.error(f"❌ Resposta: {error_text}")
                            return False
            else:
                # Usa bot token
                return await self._send_via_bot_token(payload, item)
                        
        except Exception as e:
            logger.error(f"❌ Erro ao enviar para Discord: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _send_via_bot_token(self, payload: Dict, item: Dict) -> bool:
        """
        Envia mensagem via bot token do Discord.
        
        Args:
            payload: Payload da mensagem
            item: Dados do item
            
        Returns:
            bool: True se enviou com sucesso, False caso contrário
        """
        try:
            # Remove campos específicos do webhook
            bot_payload = {
                "embeds": payload["embeds"],
                "content": f"🎯 **Nova Oportunidade Encontrada!**\n{item.get('name', 'Unknown')}"
            }
            
            # Headers para bot token
            headers = {
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json"
            }
            
            # URL da API do Discord
            url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=bot_payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"✅ Oportunidade enviada para Discord via bot: {item.get('name', 'Unknown')}")
                        return True
                    else:
                        logger.error(f"❌ Erro ao enviar via bot: {response.status}")
                        error_text = await response.text()
                        logger.error(f"❌ Resposta: {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao enviar via bot token: {e}")
            return False
    
    def _create_embed(self, item: Dict) -> Dict:
        """
        Cria um embed do Discord com as informações do item.
        
        Args:
            item: Dicionário com dados do item
            
        Returns:
            Dict: Embed formatado para Discord
        """
        try:
            # Dados básicos do item
            name = item.get('name', 'Item Desconhecido')
            price = item.get('price', 0)
            price_buff163 = item.get('price_buff163')
            liquidity_score = item.get('liquidity_score')
            condition = item.get('condition', 'Unknown')
            marketplace = item.get('marketplace', 'csgoempire')
            item_id = item.get('id', 'Unknown')
            
            # Calcula lucro se tiver preço do Buff163
            profit_percentage = None
            profit_usd = None
            
            if price_buff163 and price > 0:
                profit_usd = price_buff163 - price
                profit_percentage = ((price_buff163 - price) / price) * 100
            
            # Cor do embed baseada no lucro
            if profit_percentage:
                if profit_percentage >= 20:
                    color = 0x00FF00  # Verde claro (lucro alto)
                elif profit_percentage >= 10:
                    color = 0x32CD32  # Verde
                elif profit_percentage >= 5:
                    color = 0xFFD700  # Dourado
                else:
                    color = 0xFFA500  # Laranja
            else:
                color = 0x808080  # Cinza (sem dados de lucro)
            
            # Emoji para liquidez
            if liquidity_score:
                if liquidity_score >= 80:
                    liquidity_emoji = "🔥"
                elif liquidity_score >= 60:
                    liquidity_emoji = "💧"
                elif liquidity_score >= 40:
                    liquidity_emoji = "💦"
                else:
                    liquidity_emoji = "❄️"
            else:
                liquidity_emoji = "❓"
            
            # URL do item - formato correto para o CSGOEmpire
            # O CSGOEmpire usa o formato: https://csgoempire.com/item/{item_id}
            item_url = f"https://csgoempire.com/item/{item_id}"
            
            # Título do embed
            title = f"🎯 Oportunidade Encontrada!"
            
            # Descrição
            description = f"**{name}**\n[🔗 Ver no CSGOEmpire]({item_url}) (ID: {item_id})"
            
            # Campos do embed
            fields = []
            
            # Preços
            fields.append({
                "name": "💰 Preços",
                "value": (
                    f"**CSGOEmpire:** ${price:.2f}\n"
                    f"**Buff163:** ${price_buff163:.2f}" if price_buff163 else "**Buff163:** Não encontrado"
                ),
                "inline": True
            })
            
            # Lucro
            if profit_percentage and profit_usd:
                fields.append({
                    "name": "📈 Lucro Potencial",
                    "value": (
                        f"**${profit_usd:.2f}**\n"
                        f"**{profit_percentage:.1f}%**"
                    ),
                    "inline": True
                })
            else:
                fields.append({
                    "name": "📈 Lucro",
                    "value": "Não calculável",
                    "inline": True
                })
            
            # Liquidez
            if liquidity_score:
                fields.append({
                    "name": f"{liquidity_emoji} Liquidez",
                    "value": f"**{liquidity_score:.0f}/100**",
                    "inline": True
                })
            else:
                fields.append({
                    "name": "❓ Liquidez",
                    "value": "Não encontrada",
                    "inline": True
                })
            
            # Detalhes do item
            fields.append({
                "name": "🔍 Detalhes",
                "value": (
                    f"**Condição:** {condition}\n"
                    f"**ID:** {item_id}\n"
                    f"**Marketplace:** {marketplace.upper()}"
                ),
                "inline": True
            })
            
            # Timestamp
            timestamp = datetime.now().isoformat()
            
            # Embed completo
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields,
                "timestamp": timestamp,
                "footer": {
                    "text": f"Opportunity Bot • {marketplace.upper()}",
                    "icon_url": "https://i.imgur.com/4M34hi2.png"
                },
                "thumbnail": {
                    "url": "https://i.imgur.com/4M34hi2.png"
                }
            }
            
            return embed
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar embed: {e}")
            # Embed de fallback
            return {
                "title": "❌ Erro ao processar item",
                "description": f"Item: {item.get('name', 'Unknown')}",
                "color": 0xFF0000,
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_webhook(self) -> bool:
        """
        Testa se o webhook está funcionando.
        
        Returns:
            bool: True se o webhook funciona, False caso contrário
        """
        try:
            if not self.webhook_url:
                logger.error("❌ Discord webhook URL não configurada")
                return False
            
            # Payload de teste
            test_payload = {
                "embeds": [{
                    "title": "🧪 Teste do Opportunity Bot",
                    "description": "Webhook configurado com sucesso!",
                    "color": 0x00FF00,
                    "timestamp": datetime.now().isoformat(),
                    "footer": {
                        "text": "Opportunity Bot • Teste"
                    }
                }],
                "username": "Opportunity Bot",
                "avatar_url": "https://i.imgur.com/4M34hi2.png"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=test_payload) as response:
                    if response.status == 204:
                        logger.info("✅ Webhook do Discord testado com sucesso")
                        return True
                    else:
                        logger.error(f"❌ Erro no teste do webhook: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao testar webhook: {e}")
            return False