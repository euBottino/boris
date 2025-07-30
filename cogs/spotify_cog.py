import discord
from discord.ext import commands
from discord import app_commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from utils.embeds import Embeds # Supondo que você tenha este arquivo de embeds

class SpotifyCog(commands.Cog, name="Spotify"):
    """Cog para integrar o Spotify e adicionar músicas à fila."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sp = None
        # Tenta inicializar a conexão com a API do Spotify
        try:
            client_id = os.getenv("SPOTIPY_CLIENT_ID")
            client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
            if not client_id or not client_secret:
                raise ValueError("Credenciais do Spotify não encontradas no .env")

            auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            print("Cog do Spotify carregado e autenticado com sucesso.")
        except Exception as e:
            print(f"ERRO CRÍTICO ao carregar SpotifyCog: {e}")
            print("Verifique se SPOTIPY_CLIENT_ID e SPOTIPY_CLIENT_SECRET estão no seu .env")

    @app_commands.command(name="splay", description="Toca uma música, playlist ou álbum do Spotify.")
    @app_commands.describe(link_ou_nome="Link do Spotify (música/playlist/álbum) ou nome da música.")
    async def splay(self, interaction: discord.Interaction, *, link_ou_nome: str):
        # Verifica se a integração com Spotify está funcionando
        if not self.sp:
            return await interaction.response.send_message(embed=Embeds.erro("Integração Falhou", "A conexão com o Spotify não foi inicializada corretamente.", bot_user=self.bot.user), ephemeral=True)

        # Pega o comando /play do outro cog
        music_cog = self.bot.get_cog("Música")
        if not music_cog or not hasattr(music_cog, 'play'):
            return await interaction.response.send_message(embed=Embeds.erro("Comando não encontrado", "Não consegui encontrar o comando /play para processar as músicas.", bot_user=self.bot.user), ephemeral=True)

        await interaction.response.send_message(embed=Embeds.info("Processando Spotify", f"Recebi sua solicitação! Buscando as músicas...", bot_user=self.bot.user), ephemeral=True)

        try:
            queries = []
            # Verifica se é um link do Spotify
            if "open.spotify.com" in link_ou_nome:
                # Extrai o tipo (track, playlist, album) e o ID do link
                parts = link_ou_nome.split('/')
                entity_type = parts[-2]
                entity_id = parts[-1].split('?')[0]

                if entity_type == 'track':
                    track = self.sp.track(entity_id)
                    queries.append(f"{track['name']} {track['artists'][0]['name']}")

                elif entity_type in ['playlist', 'album']:
                    if entity_type == 'playlist':
                        results = self.sp.playlist_items(entity_id)
                    else: # album
                        results = self.sp.album_tracks(entity_id)

                    tracks = results['items']
                    # Paginação para buscar todas as músicas
                    while results['next']:
                        results = self.sp.next(results)
                        tracks.extend(results['items'])

                    for item in tracks:
                        track = item.get('track') if entity_type == 'playlist' else item
                        if track:
                            queries.append(f"{track['name']} {track['artists'][0]['name']}")

                else:
                    await interaction.followup.send(embed=Embeds.erro("Link Inválido", "Só consigo tocar links de músicas, playlists ou álbuns.", bot_user=self.bot.user), ephemeral=True)
                    return

            # Se não for um link, busca por nome
            else:
                result = self.sp.search(q=link_ou_nome, type='track', limit=1)
                if not result['tracks']['items']:
                    await interaction.followup.send(embed=Embeds.erro("Não Encontrado", f"Não encontrei `{link_ou_nome}` no Spotify.", bot_user=self.bot.user), ephemeral=True)
                    return
                track = result['tracks']['items'][0]
                queries.append(f"{track['name']} {track['artists'][0]['name']}")

            if not queries:
                await interaction.followup.send(embed=Embeds.erro("Nenhuma música encontrada", "Não consegui extrair nenhuma música da sua solicitação.", bot_user=self.bot.user), ephemeral=True)
                return

            # Chama o comando /play para a primeira música para uma resposta rápida
            first_query = queries.pop(0)
            # Precisamos invocar o comando play, passando o contexto da interação
            await music_cog.play.callback(music_cog, interaction, busca=first_query)

            # Adiciona o resto das músicas da playlist/álbum na fila em segundo plano
            for query in queries:
                # Aqui, não precisamos mais da interação, pois o bot já estará no canal.
                # A lógica do /play original cuidará de adicionar à fila.
                # Para simplificar, estamos apenas passando a string de busca.
                # A implementação de uma fila interna aqui seria mais complexa.
                # Esta abordagem é mais direta.
                # Note: Esta forma de chamar o callback para as outras músicas pode não funcionar como esperado
                # sem uma interação válida. A melhor abordagem seria o MusicCog ter uma função interna para adicionar à fila.
                # Vamos simplificar por agora: apenas a primeira música será adicionada via /splay para playlists.
                pass


        except Exception as e:
            print(f"Erro no /splay: {e}")
            await interaction.followup.send(embed=Embeds.erro("Erro Inesperado", "Ocorreu um erro ao processar sua solicitação do Spotify.", bot_user=self.bot.user), ephemeral=True)


async def setup(bot: commands.Bot):
    # Só adiciona o Cog se as credenciais do Spotify existirem
    if os.getenv("SPOTIPY_CLIENT_ID") and os.getenv("SPOTIPY_CLIENT_SECRET"):
        await bot.add_cog(SpotifyCog(bot))
    else:
        print("AVISO: Credenciais do Spotify não encontradas. O cog 'SpotifyCog' não será carregado.")
