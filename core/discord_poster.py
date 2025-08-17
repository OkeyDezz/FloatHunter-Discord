"""
Sistema de postagem no Discord para o Opportunity Bot.
"""

import discord
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from config.settings import Settings

logger = logging.getLogger(__name__)

class DiscordPoster:
    """Gerencia postagens no Discord."""
    
    def __init__(self):
        self.settings = Settings()
        self.client = None
        self.is_ready = False
        
    async def initialize(self):
        """Inicializa o cliente do Discord."""
        try:
            if not self.settings.DISCORD_TOKEN:
                logger.error("❌ Token do Discord não configurado")
                return False
            
            intents = discord.Intents.default()
            intents.message_content = True
            
            self.client = discord.Client(intents=intents)
            
            @self.client.event
            async def on_ready():
                logger.info(f"🤖 Bot do Discord conectado como {self.client.user}")
                self.is_ready = True
            
            # Inicia o cliente em background
            asyncio.create_task(self.client.start(self.settings.DISCORD_TOKEN))
            
            # Aguarda conexão
            timeout = 30
            while not self.is_ready and timeout > 0:
                await asyncio.sleep(1)
                timeout -= 1
            
            if not self.is_ready:
                logger.error("❌ Timeout ao conectar ao Discord")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Discord: {e}")
            return False
    
    async def post_opportunity(self, item: Dict, marketplace: str = "csgoempire"):
        """
        Posta uma oportunidade no canal do Discord.
        
        Args:
            item: Dados do item
            marketplace: Nome do marketplace
        """
        try:
            if not self.is_ready or not self.client:
                logger.warning("Discord não está pronto")
                return False
            
            channel_id = self._get_channel_id(marketplace)
            if not channel_id:
                logger.warning(f"Canal não configurado para {marketplace}")
                return False
            
            channel = self.client.get_channel(channel_id)
            if not channel:
                logger.error(f"Canal {channel_id} não encontrado")
                return False
            
            # Formata a mensagem
            embed = self._create_opportunity_embed(item, marketplace)
            
            # Envia a mensagem
            await channel.send(embed=embed)
            logger.info(f"✅ Oportunidade postada no Discord: {item.get('name', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao postar no Discord: {e}")
            return False
    
    def _get_channel_id(self, marketplace: str) -> Optional[int]:
        """Retorna o ID do canal para o marketplace."""
        mapping = {
            'csgoempire': self.settings.CSGOEMPIRE_CHANNEL_ID,
            # Futuros marketplaces
            # 'csfloat': self.settings.CSFLOAT_CHANNEL_ID,
            # 'whitemarket': self.settings.WHITEMARKET_CHANNEL_ID,
        }
        return mapping.get(marketplace)
    
    def _create_opportunity_embed(self, item: Dict, marketplace: str) -> discord.Embed:
        """Cria um embed do Discord para a oportunidade."""
        try:
            embed = discord.Embed(
                title="🎯 OPORTUNIDADE ENCONTRADA!",
                description=f"**{item.get('name', 'Item desconhecido')}**",
                color=0x00ff00,  # Verde
                timestamp=datetime.now()
            )
            
            # Adiciona campos
            if 'price' in item:
                embed.add_field(
                    name="💰 Preço", 
                    value=f"${item['price']:.2f}", 
                    inline=True
                )
            
            if 'market_hash_name' in item:
                embed.add_field(
                    name="🏷️ Market Hash", 
                    value=item['market_hash_name'][:50] + "..." if len(item['market_hash_name']) > 50 else item['market_hash_name'], 
                    inline=True
                )
            
            embed.add_field(
                name="🏪 Marketplace", 
                value=marketplace.upper(), 
                inline=True
            )
            
            # Footer
            embed.set_footer(text="Opportunity Bot - Detectando oportunidades 24/7")
            
            return embed
            
        except Exception as e:
            logger.error(f"Erro ao criar embed: {e}")
            # Embed de fallback
            embed = discord.Embed(
                title="🎯 OPORTUNIDADE ENCONTRADA!",
                description="Item detectado no marketplace",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            return embed
    
    async def close(self):
        """Fecha a conexão com o Discord."""
        try:
            if self.client:
                await self.client.close()
                logger.info("Discord desconectado")
        except Exception as e:
            logger.error(f"Erro ao desconectar Discord: {e}")
