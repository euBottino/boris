import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from itertools import cycle
import wavelink

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", 2333))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!boris ', intents=intents)
        self.bot_activities = cycle([
            discord.Game(name="músicas com /play"),
            discord.Activity(type=discord.ActivityType.listening, name="suas dúvidas em /ajuda"),
            discord.Game(name="no seu servidor favorito!")
        ])

    async def setup_hook(self):
        print(f"Tentando conectar ao Lavalink em {LAVALINK_HOST}:{LAVALINK_PORT}...")
        node_uri = f"http://{LAVALINK_HOST}:{LAVALINK_PORT}"
        node = wavelink.Node(uri=node_uri, password=LAVALINK_PASSWORD)
        await wavelink.Pool.connect(client=self, nodes=[node])

        print("\nCarregando extensões (cogs)...")
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py') and not filename.startswith('__'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f'-> Cog "{filename[:-3]}" carregado com sucesso.')
                    except Exception as e:
                        print(f'-> Falha ao carregar o cog "{filename[:-3]}". Erro: {e}')

        try:
            synced = await self.tree.sync()
            print(f"Sincronizados {len(synced)} comandos de barra (/).")
        except Exception as e:
            print(f"Falha ao sincronizar comandos: {e}")

    @tasks.loop(minutes=1)
    async def change_status_task(self):
        await self.change_presence(activity=next(self.bot_activities))

    async def on_ready(self):
        await self.wait_until_ready()
        print('------')
        print(f'Logado como {self.user} (ID: {self.user.id})')
        print(f'Versão do Wavelink: {wavelink.__version__}')
        print('Iniciando tarefa de mudança de status...')
        print('------')
        if not self.change_status_task.is_running():
            self.change_status_task.start()

    # A CORREÇÃO FINAL E DEFINITIVA ESTÁ AQUI
    # O evento passa um objeto 'payload', que contém um objeto 'node', que por sua vez contém o 'identifier'.
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print('------')
        print(f"Nó do Wavelink '{payload.node.identifier}' está pronto e conectado!")
        print(f'DJ Boris está 100% online e funcional!')
        print('------')

bot = MyBot()

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("ERRO CRÍTICO: O token do Discord não foi encontrado no arquivo .env!")