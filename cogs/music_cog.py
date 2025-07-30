import discord
from discord import ui
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
from typing import cast

# --- Classe de Embeds (Adapte se a sua for diferente) ---
class Embeds:
    COR_PADRAO = 0x2B2D31
    COR_ERRO = 0xED4245
    COR_SUCESSO = 0x57F287
    COR_MUSICA = 0xEB459E

    @staticmethod
    def _base_embed(title: str, description: str, color: int, bot_user: discord.ClientUser):
        embed = discord.Embed(title=title, description=description, color=color)
        return embed

    @staticmethod
    def erro(title: str, description: str, bot_user: discord.ClientUser):
        return Embeds._base_embed(f"❌ {title}", description, Embeds.COR_ERRO, bot_user)

    @staticmethod
    def sucesso(title: str, description: str, bot_user: discord.ClientUser):
        return Embeds._base_embed(f"✅ {title}", description, Embeds.COR_SUCESSO, bot_user)

    @staticmethod
    def info(title: str, description: str, bot_user: discord.ClientUser):
        return Embeds._base_embed(f"ℹ️ {title}", description, Embeds.COR_PADRAO, bot_user)

    @staticmethod
    def musica_tocando(track: wavelink.Playable, bot_user: discord.ClientUser):
        embed = discord.Embed(title="▶️ Tocando Agora", description=f"**[{track.title}]({track.uri})**", color=Embeds.COR_MUSICA)
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        minutes, seconds = divmod(track.length / 1000, 60)
        embed.add_field(name="Duração", value=f"{int(minutes)}:{int(seconds):02d}", inline=True)
        embed.add_field(name="Autor", value=track.author, inline=True)

        embed.set_footer(text=f"DJ Boris | {bot_user.display_name}", icon_url=bot_user.avatar.url if bot_user.avatar else None)
        return embed

# --- INTERFACE DE BOTÕES PARA O VOLUME ---
class VolumeControlView(ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=120.0)
        self.player = player
        self.update_volume_label()

    def update_volume_label(self):
        self.volume_display.label = f"{self.player.volume}%"

    async def update_message(self, interaction: discord.Interaction):
        self.update_volume_label()
        embed = self.create_volume_embed(self.player.volume, interaction.client.user)
        await interaction.response.edit_message(embed=embed, view=self)

    def create_volume_embed(self, volume, bot_user):
        visual_volume = min(volume, 100)
        bar = "█" * (visual_volume // 10) + "─" * ((100 - visual_volume) // 10)
        return Embeds.info("Controle de Volume", f"Ajuste o volume do bot.\n\n`{bar}` **{volume}%**", bot_user=bot_user)

    @ui.button(style=discord.ButtonStyle.secondary, emoji="🔉")
    async def decrease_volume(self, interaction: discord.Interaction, button: ui.Button):
        new_volume = max(0, self.player.volume - 10)
        await self.player.set_volume(new_volume)
        await self.update_message(interaction)

    @ui.button(style=discord.ButtonStyle.grey, label="100%", disabled=True)
    async def volume_display(self, interaction: discord.Interaction, button: ui.Button): pass

    @ui.button(style=discord.ButtonStyle.secondary, emoji="🔊")
    async def increase_volume(self, interaction: discord.Interaction, button: ui.Button):
        new_volume = min(150, self.player.volume + 10)
        await self.player.set_volume(new_volume)
        await self.update_message(interaction)

    @ui.button(style=discord.ButtonStyle.danger, emoji="✖️", row=1)
    async def close_panel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.message.delete()

# --- COG DE MÚSICA ---
class MusicCog(commands.Cog, name="Música"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_247 = {}

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player or not player.connected: return

        if player.queue:
            next_track = player.queue.get()
            await player.play(next_track)

            if hasattr(player, 'text_channel') and player.text_channel:
                embed = Embeds.musica_tocando(next_track, bot_user=self.bot.user)
                await player.text_channel.send(embed=embed)
        elif not self.is_247.get(player.guild.id, False):
            await asyncio.sleep(300)
            if player.connected and not player.playing:
                await player.disconnect()
                if hasattr(player, 'text_channel') and player.text_channel:
                    await player.text_channel.send(embed=Embeds.info("Até mais!", "Fila vazia, estou de saída! 👋", bot_user=self.bot.user))

    async def get_player(self, interaction: discord.Interaction) -> wavelink.Player | None:
        if not interaction.user.voice:
            # Não use followup aqui, a resposta inicial já foi deferida
            await interaction.edit_original_response(embed=Embeds.erro("Onde você está?", "Você precisa estar em um canal de voz.", bot_user=self.bot.user), view=None)
            return None

        if not interaction.guild.voice_client:
            return await interaction.user.voice.channel.connect(cls=wavelink.Player)
        return cast(wavelink.Player, interaction.guild.voice_client)

    @app_commands.command(name="play", description="Toca uma música ou playlist do YouTube/SoundCloud.")
    @app_commands.describe(busca="Nome ou link da música/playlist.")
    async def play(self, interaction: discord.Interaction, *, busca: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        player = await self.get_player(interaction)
        if not player: return

        player.text_channel = interaction.channel

        tracks: wavelink.Search = await wavelink.Playable.search(busca)
        if not tracks:
            return await interaction.edit_original_response(embed=Embeds.erro("Não Encontrado", f"Não encontrei nada para `{busca}`.", bot_user=self.bot.user), view=None)

        if isinstance(tracks, wavelink.Playlist):
            player.queue.extend(tracks.tracks)
            await interaction.edit_original_response(embed=Embeds.sucesso("Playlist Adicionada", f"Adicionei **{len(tracks.tracks)}** músicas da playlist **{tracks.name}** à fila.", bot_user=self.bot.user), view=None)
        else:
            track: wavelink.Playable = tracks[0]
            player.queue.put(track)
            if player.playing:
                await interaction.edit_original_response(embed=Embeds.sucesso("Adicionado à Fila", f"**[{track.title}]({track.uri})** foi adicionado à fila.", bot_user=self.bot.user), view=None)

        if not player.playing:
            first_track = player.queue.get()
            await player.play(first_track)
            embed = Embeds.musica_tocando(first_track, bot_user=self.bot.user)
            await interaction.channel.send(embed=embed)
            await interaction.edit_original_response(content="Começando a festa! 🥳", view=None)

    @app_commands.command(name="skip", description="Pula para a próxima música da fila.")
    async def skip(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or not player.playing:
            return await interaction.response.send_message(embed=Embeds.erro("Nada tocando", "Não há nenhuma música tocando para eu pular.", bot_user=self.bot.user), ephemeral=True)

        current_title = player.current.title if player.current else "a música atual"
        await player.stop()
        await interaction.response.send_message(embed=Embeds.sucesso("Música Pulada!", f"Pulei **{current_title}**.", bot_user=self.bot.user), ephemeral=True)

    @app_commands.command(name="stop", description="Para a música, limpa a fila e desconecta o bot.")
    async def stop(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or not player.connected:
            return await interaction.response.send_message(embed=Embeds.erro("Não conectado", "Não estou em nenhum canal de voz.", bot_user=self.bot.user), ephemeral=True)

        player.queue.clear()
        await player.stop()
        await player.disconnect()
        await interaction.response.send_message(embed=Embeds.sucesso("Festa Encerrada!", "Música parada e fila limpa. Até a próxima!", bot_user=self.bot.user))

    @app_commands.command(name="queue", description="Mostra a fila de músicas.")
    async def queue(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or (not player.current and not player.queue):
            return await interaction.response.send_message(embed=Embeds.info("Fila Vazia", "Não há músicas na fila.", bot_user=self.bot.user))

        embed = discord.Embed(title="Fila de Músicas 🎵", color=Embeds.COR_MUSICA, description="")
        if player.current:
            embed.description += f"**▶️ Tocando Agora:** [{player.current.title}]({player.current.uri})\n\n"

        if player.queue:
            embed.description += "**⬇️ Próximas na Fila:**\n"
            queue_list = "\n".join(f"`{i+1}.` [{track.title}]({track.uri})" for i, track in enumerate(list(player.queue)[:10]))
            embed.description += queue_list

        if len(player.queue) > 10:
            embed.set_footer(text=f"... e mais {len(player.queue) - 10} músicas.")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Abre o painel para ajustar o volume do bot.")
    async def volume(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message(embed=Embeds.erro("Não Conectado", "Preciso estar em um canal de voz para ajustar o volume.", bot_user=self.bot.user), ephemeral=True)

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
