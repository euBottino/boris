import discord
from discord import app_commands
from discord.ext import commands
# <<< CORREÇÃO 1: Importando a CLASSE Embeds >>>
from utils.embeds import Embeds

class GeneralCog(commands.Cog):
    """Cog para os comandos gerais do bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Verifica a latência do bot.")
    async def ping(self, interaction: discord.Interaction):
        """Responde com a latência atual do bot em milissegundos."""
        latencia = round(self.bot.latency * 1000)
        
        # <<< CORREÇÃO 2: Usando Embeds.info(...) >>>
        await interaction.response.send_message(embed=Embeds.info(
            "Pong! 🏓", 
            f"Minha latência está em `{latencia}ms`.",
            bot_user=self.bot.user
        ))

    @app_commands.command(name="ajuda", description="Mostra todos os meus comandos.")
    async def ajuda(self, interaction: discord.Interaction):
        """Mostra uma mensagem de ajuda dinâmica com todos os comandos do bot."""
        await interaction.response.defer()

        embed = discord.Embed(
            title="🎧 Comandos do DJ Boris",
            description="Aqui está a lista de tudo que eu posso fazer! Use os comandos com a barra `/`.",
            color=0x6f42c1
        )

        cog_display_names = {
            "GeneralCog": "⚙️ Geral",
            "MusicCog": "🎵 Música",
            "SpotifyCog": "🎧 Spotify"
        }

        for cog_name, cog in self.bot.cogs.items():
            display_name = cog_display_names.get(cog_name, cog_name)
            cog_commands = sorted(cog.get_app_commands(), key=lambda c: c.name)
            
            if cog_commands:
                command_text = "\n".join(
                    f"`/{cmd.name}` - {cmd.description}" for cmd in cog_commands
                )
                embed.add_field(name=display_name, value=command_text, inline=False)
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        embed.set_footer(text=f"DJ Boris | Bot de música 24/7")
        
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))