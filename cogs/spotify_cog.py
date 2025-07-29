import discord
from discord import app_commands
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import asyncio
from utils.embeds import Embeds

class SpotifyCog(commands.Cog):
    """Cog para integrar o Spotify e tocar músicas, playlists e álbuns."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=os.getenv("SPOTIPY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            print("SpotifyCog carregado com sucesso.")
        except Exception as e:
            self.sp = None
            print(f"ERRO: Falha ao carregar SpotifyCog. Verifique as credenciais. Detalhe: {e}")
            
    def _create_youtube_query(self, track) -> str:
        """Cria uma string de busca 'Nome da Música Artista' a partir de um objeto de track do Spotify."""
        if not track or not track.get('name'):
            return None
        return f"{track['name']} {track['artists'][0]['name']}"

    @app_commands.command(name="splay", description="Toca músicas, playlists ou álbuns do Spotify (use link ou nome).")
    @app_commands.describe(busca="Link do Spotify (música/playlist/álbum) ou nome da música para buscar.")
    async def spotify_play(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer(thinking=True)

        if not self.sp:
            return await interaction.followup.send(embed=Embeds.erro("Integração com Spotify Falhou", "Não consegui me conectar ao Spotify.", bot_user=self.bot.user))
        music_cog = self.bot.get_cog('MusicCog')
        if not music_cog:
            return await interaction.followup.send(embed=Embeds.erro("Módulo de Música Desligado", "Não consigo acessar a funcionalidade de tocar música.", bot_user=self.bot.user))
        if not interaction.user.voice:
            return await interaction.followup.send(embed=Embeds.erro("Onde você está?", "Você precisa estar em um canal de voz.", bot_user=self.bot.user))
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()

        try:
            queries = []
            entity_name = ""
            entity_type = ""

            # --- LÓGICA DE DETECÇÃO INTELIGENTE ---
            if "open.spotify.com" in busca: # É um link do Spotify
                parts = busca.split('/')
                entity_type = parts[-2]
                entity_id = parts[-1].split('?')[0]
                
                if entity_type == 'track':
                    track = self.sp.track(entity_id)
                    queries.append(self._create_youtube_query(track))
                    entity_name = track['name']
                
                elif entity_type == 'playlist':
                    playlist = self.sp.playlist(entity_id, fields="name,tracks.total,tracks.items(track(name,artists))")
                    entity_name = playlist['name']
                    tracks = playlist['tracks']['items']
                    # Paginação para playlists grandes
                    results = playlist['tracks']
                    while results['next']:
                        results = self.sp.next(results)
                        tracks.extend(results['items'])
                    for item in tracks:
                        if item and item.get('track'):
                            queries.append(self._create_youtube_query(item['track']))
                
                elif entity_type == 'album':
                    album = self.sp.album(entity_id)
                    entity_name = album['name']
                    tracks = album['tracks']['items']
                    # Paginação para álbuns grandes
                    results = album['tracks']
                    while results['next']:
                        results = self.sp.next(results)
                        tracks.extend(results['items'])
                    for track in tracks:
                        queries.append(self._create_youtube_query(track))

                else:
                    return await interaction.followup.send(embed=Embeds.erro("Link Inválido", "Só consigo tocar links de músicas, playlists ou álbuns.", bot_user=self.bot.user))

            else: # Não é um link, então é uma busca por texto
                entity_type = "busca"
                result = self.sp.search(q=busca, type='track', limit=1)
                if not result['tracks']['items']:
                    return await interaction.followup.send(embed=Embeds.erro("Não Encontrado", f"Não encontrei nenhuma música no Spotify para: `{busca}`.", bot_user=self.bot.user))
                track = result['tracks']['items'][0]
                queries.append(self._create_youtube_query(track))
                entity_name = track['name']

            if not queries:
                 return await interaction.followup.send(embed=Embeds.erro("Nada para Tocar", f"Não consegui extrair nenhuma música de '{entity_name}'.", bot_user=self.bot.user))

            await interaction.followup.send(embed=Embeds.info("Processando...", f"Encontrei **{entity_name}** no Spotify! Buscando no YouTube agora...", bot_user=self.bot.user))
            
            songs_to_add = []
            for query in filter(None, queries): # filter(None,...) ignora queries vazias
                with music_cog.yt_dlp.YoutubeDL(music_cog.YDL_OPTIONS) as ydl:
                    try:
                        info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                        song_data = {'title': info.get('title'), 'url': info.get('url'), 'webpage_url': info.get('webpage_url'), 'duration_str': music_cog.format_duration(info.get('duration')), 'thumbnail': info.get('thumbnail'), 'requester': interaction.user}
                        songs_to_add.append(song_data)
                    except Exception:
                        pass # Ignora músicas que não foram encontradas no YouTube
                await asyncio.sleep(0.1)

            if not songs_to_add:
                return await interaction.channel.send(embed=Embeds.erro("Nenhuma música encontrada", "Não consegui encontrar nenhuma das músicas do Spotify no YouTube.", bot_user=self.bot.user))

            await music_cog._add_to_queue(interaction, songs_to_add)

        except Exception as e:
            print(f"Erro ao processar /splay: {e}")
            await interaction.followup.send(embed=Embeds.erro("Erro no Spotify", "Não consegui processar sua solicitação. Verifique se o link/nome é válido e se o conteúdo é público.", bot_user=self.bot.user))


async def setup(bot: commands.Bot):
    await bot.add_cog(SpotifyCog(bot))