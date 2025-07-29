import discord
from discord import ui
from discord import app_commands
from discord.ext import commands
import wavelink
import asyncio
from utils.embeds import Embeds

# --- INTERFACE DE BOTÕES PARA O VOLUME ---
class VolumeControlView(ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=120.0)
        self.player = player
        self.volume_display.label = f"{player.volume}%"

    async def update_display(self, interaction: discord.Interaction):
        self.volume_display.label = f"{self.player.volume}%"
        embed = self.create_volume_embed(self.player.volume, interaction.client.user)
        await interaction.response.edit_message(embed=embed, view=self)

    def create_volume_embed(self, volume, bot_user):
        bar = "█" * (volume // 10) + "─" * ((200 - volume) // 10)
        return Embeds.info("Controle de Volume", f"Ajuste o volume do bot.\n\n`{bar}` **{volume}%**", bot_user=bot_user)

    @ui.button(style=discord.ButtonStyle.secondary, emoji="🔉")
    async def decrease_volume(self, interaction: discord.Interaction, button: ui.Button):
        new_volume = max(0, self.player.volume - 10)
        await self.player.set_volume(new_volume)
        await self.update_display(interaction)

    @ui.button(style=discord.ButtonStyle.grey, disabled=True)
    async def volume_display(self, interaction: discord.Interaction, button: ui.Button):
        pass

    @ui.button(style=discord.ButtonStyle.secondary, emoji="🔊")
    async def increase_volume(self, interaction: discord.Interaction, button: ui.Button):
        new_volume = min(200, self.player.volume + 10)
        await self.player.set_volume(new_volume)
        await self.update_display(interaction)

    @ui.button(style=discord.ButtonStyle.danger, emoji="✖️")
    async def close_panel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.message.delete()

# --- COG DE MÚSICA ---
class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_247 = {}

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        print(f"Nó Wavelink '{node.identifier}' está pronto.")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return
        
        # Toca a próxima música se a fila não estiver vazia
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
            
            if hasattr(player, 'text_channel') and player.text_channel:
                embed = Embeds.musica_tocando(musica_info=next_track.__dict__, proxima_musica=player.queue.peek().__dict__ if not player.queue.is_empty else None)
                await player.text_channel.send(embed=embed)
        # Se a fila estiver vazia, verifica se deve se desconectar
        else:
            if not self.is_247.get(player.guild.id, False):
                await asyncio.sleep(300) # Espera 5 minutos
                if player.is_connected() and not player.is_playing():
                    await player.disconnect()
                    if hasattr(player, 'text_channel') and player.text_channel:
                         await player.text_channel.send(embed=Embeds.info("Até mais!", "Fila vazia, estou de saída! 👋", bot_user=self.bot.user))

    async def get_player(self, interaction: discord.Interaction) -> wavelink.Player | None:
        """Helper para obter o player ou conectar se necessário."""
        if not interaction.user.voice:
            await interaction.followup.send(embed=Embeds.erro("Onde você está?", "Você precisa estar em um canal de voz.", bot_user=self.bot.user))
            return None
        
        if not interaction.guild.voice_client:
            return await interaction.user.voice.channel.connect(cls=wavelink.Player)
        return interaction.guild.voice_client

    @app_commands.command(name="play", description="Toca uma música ou playlist do YouTube/SoundCloud.")
    @app_commands.describe(busca="Nome ou link da música/playlist.")
    async def play(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer(thinking=True)
        player = await self.get_player(interaction)
        if not player:
            return
        
        player.text_channel = interaction.channel
        tracks: wavelink.Search = await wavelink.Playable.search(busca)
        if not tracks:
            return await interaction.followup.send(embed=Embeds.erro("Não Encontrado", f"Não encontrei nada para `{busca}`.", bot_user=self.bot.user))
        
        if isinstance(tracks, wavelink.Playlist):
            added = await player.queue.put_wait(tracks.tracks)
            await interaction.followup.send(embed=Embeds.sucesso("Playlist Adicionada", f"Adicionei **{added}** músicas da playlist **{tracks.name}** à fila.", bot_user=self.bot.user))
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            await interaction.followup.send(embed=Embeds.sucesso("Adicionado à Fila", f"**[{track.title}]({track.uri})** foi adicionado à fila.", bot_user=self.bot.user))

        if not player.is_playing():
            first_track = player.queue.get()
            await player.play(first_track)
            embed = Embeds.musica_tocando(musica_info=first_track.__dict__, proxima_musica=player.queue.peek().__dict__ if not player.queue.is_empty else None)
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="skip", description="Pula para a próxima música da fila.")
    async def skip(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_playing():
            return await interaction.response.send_message(embed=Embeds.erro("Nada tocando", "Não há nenhuma música tocando para eu pular."), ephemeral=True)
        
        skipped_track = player.current
        await player.skip(force=True)
        await interaction.response.send_message(embed=Embeds.sucesso("Música Pulada!", f"Pulei **{skipped_track.title}**.", bot_user=self.bot.user))

    @app_commands.command(name="stop", description="Para a música, limpa a fila e desconecta o bot.")
    async def stop(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message(embed=Embeds.erro("Não conectado", "Não estou em nenhum canal de voz."), ephemeral=True)
        
        await player.disconnect()
        await interaction.response.send_message(embed=Embeds.sucesso("Festa Encerrada!", "Música parada e fila limpa. Até a próxima!", bot_user=self.bot.user))

    @app_commands.command(name="queue", description="Mostra a fila de músicas.")
    async def queue(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or (not player.current and player.queue.is_empty):
            return await interaction.response.send_message(embed=Embeds.info("Fila Vazia", "Não há músicas na fila.", bot_user=self.bot.user))
        
        embed = discord.Embed(title="Fila de Músicas 🎵", color=Embeds.COR_MUSICA)
        if player.current:
            embed.add_field(name="▶️ Tocando Agora", value=f"**[{player.current.title}]({player.current.uri})**", inline=False)
        
        if not player.queue.is_empty:
            queue_list = "\n".join(f"`{i+1}.` **[{track.title}]({track.uri})**" for i, track in enumerate(player.queue) if i < 10)
            embed.add_field(name="⬇️ Próximas na Fila", value=queue_list, inline=False)
        
        if len(player.queue) > 10:
            embed.set_footer(text=f"... e mais {len(player.queue) - 10} músicas.")
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Abre o painel para ajustar o volume do bot.")
    async def volume(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message(embed=Embeds.erro("Não Conectado", "Preciso estar em um canal de voz para ajustar o volume."), ephemeral=True)
        
        view = VolumeControlView(player)
        embed = view.create_volume_embed(player.volume, self.bot.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @app_commands.command(name="247", description="Ativa/desativa o modo 24/7 (não sair do canal).")
    async def twentyfourseven(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        status = not self.is_247.get(guild_id, False)
        self.is_247[guild_id] = status
        
        message = "ativado! Não sairei mais do canal por inatividade." if status else "desativado. Sairei do canal após 5 minutos de inatividade."
        await interaction.response.send_message(embed=Embeds.info("Modo 24/7", f"O modo 24/7 foi **{message}**", bot_user=self.bot.user))


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))