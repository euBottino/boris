# --- IMPORTS PRINCIPAIS DO PROJETO ---
import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from itertools import cycle
import wavelink

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", 2333)) # 2333 é uma porta padrão comum
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")

# --- DEFINIÇÃO DOS INTENTS ---
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True 

# --- DEFINIÇÃO DA CLASSE DO BOT ---
class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix='!boris', intents=intents, *args, **kwargs)
        self.activities_list = cycle([
            discord.Game(name="músicas com /play"),
            discord.Activity(type=discord.ActivityType.listening, name="dúvidas em /ajuda")
        ])

    async def setup_hook(self):
        """Este hook é executado para configurar o bot antes de ficar online."""
        print(f"Tentando conectar ao Lavalink em {LAVALINK_HOST}:{LAVALINK_PORT}...")
        node_uri = f"http://{LAVALINK_HOST}:{LAVALINK_PORT}"
        node: wavelink.Node = wavelink.Node(uri=node_uri, password=LAVALINK_PASSWORD)

        try:
            # <-- CORREÇÃO PRINCIPAL: A função correta é wavelink.Pool.connect()
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
        except Exception as e:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("FALHA CRÍTICA AO CONECTAR AO LAVALINK.")
            print(f"ERRO: {type(e).__name__} - {e}")
            print("\nVERIFIQUE:")
            print("1. O servidor Lavalink está online?")
            print("2. O HOST, PORT e PASSWORD no seu arquivo .env estão corretos?")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return

        print("\nCarregando extensões (cogs)...")
        if os.path.isdir('./cogs'):
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

    async def on_ready(self):
        # await self.wait_until_ready() <-- CORREÇÃO: Esta linha é redundante dentro do on_ready.
        
        # A verificação de conexão é ótima, vamos mantê-la.
        node = wavelink.Pool.get_node() # Usamos Pool para pegar o nó
        if node and node.is_connected:
            print('------')
            print(f'Logado como {self.user} (ID: {self.user.id})')
            print(f'Conectado com sucesso ao Lavalink v{node.version}!')
            print(f'DJ Boris está 100% online e funcional!')
            print('------')
            self.change_status_task.start() # Inicia a troca de status
        else:
            print('------')
            print(f'Logado como {self.user} (ID: {self.user.id})')
            print('ERRO: A conexão com Lavalink falhou ou não foi estabelecida no setup_hook.')
            print('------')

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """Evento para confirmar que o nó do Wavelink está pronto."""
        print(f"Nó do Wavelink '{payload.node.identifier}' está pronto!")

    @tasks.loop(seconds=60)
    async def change_status_task(self):
        """Muda o status do bot a cada 60 segundos."""
        await self.change_presence(activity=next(self.activities_list))

# --- INICIALIZAÇÃO DO BOT ---
bot = MyBot()

if __name__ == "__main__":
    if TOKEN and LAVALINK_HOST and LAVALINK_PASSWORD:
        bot.run(TOKEN)
    else:
        print("ERRO CRÍTICO: Verifique se DISCORD_TOKEN, LAVALINK_HOST e LAVALINK_PASSWORD estão no seu arquivo .env!")