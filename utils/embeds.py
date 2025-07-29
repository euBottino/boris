import discord
import random
from datetime import datetime, timezone

class Embeds:
    """Classe para gerenciar a criação de embeds padronizados."""

    # --- CORES PADRÃO MOVIDAS PARA DENTRO DA CLASSE ---
    COR_SUCESSO = 0x28a745
    COR_ERRO = 0xdc3545
    COR_INFO = 0x17a2b8
    COR_MUSICA = 0x6f42c1 # Roxo
    # --------------------------------------------------

    @staticmethod
    def _get_default_footer(bot_user: discord.User) -> tuple[str, str]:
        """Cria um rodapé divertido e contextual ao dia da semana."""
        
        agora = datetime.now()
        dia_da_semana = agora.weekday() # Segunda-feira é 0, Domingo é 6

        mensagens_gerais = [
            "Sempre no ritmo certo 🎶", "Aumentando o som da sua festa!",
            "Sua dose diária de grave 🎧", "Mantendo o beat vivo 🔥"
        ]

        if dia_da_semana == 4: # Sexta-feira
            mensagem_do_dia = "Sextou com o melhor som! 🕺"
        elif dia_da_semana in [5, 6]: # Fim de semana
            mensagem_do_dia = "O som não para no fim de semana! ✨"
        elif dia_da_semana == 0: # Segunda-feira
            mensagem_do_dia = "Começando a semana com o pé direito! 🚀"
        else: # Terça, Quarta, Quinta
            mensagem_do_dia = random.choice(mensagens_gerais)

        texto_rodape = f"DJ Boris | {mensagem_do_dia}"
        icone_url = bot_user.display_avatar.url if bot_user else None
        
        return texto_rodape, icone_url

    @classmethod
    def sucesso(cls, titulo: str, descricao: str, bot_user: discord.User = None):
        """Cria uma embed de sucesso."""
        embed = discord.Embed(
            title=f"✅ {titulo}",
            description=descricao,
            color=cls.COR_SUCESSO  # Corrigido para usar a variável da classe
        )
        if bot_user:
            footer_text, footer_icon = cls._get_default_footer(bot_user)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
        return embed

    @classmethod
    def erro(cls, titulo: str, descricao: str, bot_user: discord.User = None):
        """Cria uma embed de erro."""
        embed = discord.Embed(
            title=f"❌ {titulo}",
            description=descricao,
            color=cls.COR_ERRO  # Corrigido para usar a variável da classe
        )
        if bot_user:
            footer_text, footer_icon = cls._get_default_footer(bot_user)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
        return embed

    @classmethod
    def info(cls, titulo: str, descricao: str, bot_user: discord.User = None):
        """Cria uma embed de informação."""
        embed = discord.Embed(
            title=f"ℹ️ {titulo}",
            description=descricao,
            color=cls.COR_INFO  # Corrigido para usar a variável da classe
        )
        if bot_user:
            footer_text, footer_icon = cls._get_default_footer(bot_user)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
        return embed

    @classmethod
    def musica_tocando(cls, musica_info: dict, proxima_musica: dict = None):
        """Cria a embed bonita para a música que está tocando."""
        titulo = musica_info.get('title', 'Título Desconhecido')
        url = musica_info.get('webpage_url', '')
        thumbnail = musica_info.get('thumbnail', None)
        duracao = musica_info.get('duration_str', 'N/A')
        requester = musica_info.get('requester')
        
        embed = discord.Embed(
            title=f"▶️ Tocando Agora",
            description=f"**[{titulo}]({url})**",
            color=cls.COR_MUSICA,  # Corrigido para usar a variável da classe
            timestamp=datetime.now(timezone.utc)
        )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        embed.add_field(name="Duração", value=f"`{duracao}`", inline=True)
        
        if requester:
            embed.add_field(name="Pedido por", value=requester.mention, inline=True)

        if proxima_musica:
            prox_titulo = proxima_musica.get('title', 'N/A')
            embed.add_field(name="⬇️ Próxima", value=prox_titulo, inline=False)
        else:
            embed.add_field(name="⬇️ Próxima", value="Fim da fila!", inline=False)
        
        if requester:
            bot_user = requester.guild.me
            footer_text, footer_icon = cls._get_default_footer(bot_user)
            embed.set_footer(text=footer_text, icon_url=footer_icon)

        return embed