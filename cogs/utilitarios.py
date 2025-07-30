import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import Embeds # Importamos nossa classe de embeds padronizados

class UtilitariosCog(commands.Cog):
    """Cog para comandos de utilidade e moderação."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="limpar", description="[ADMIN] Limpa uma quantidade específica de mensagens do canal.")
    @app_commands.describe(quantidade="O número de mensagens que você deseja apagar (entre 1 e 100).")
    # Define que apenas membros com permissão de "Gerenciar Mensagens" podem usar o comando.
    # Isso é crucial para a segurança do seu servidor.
    @app_commands.checks.has_permissions(manage_messages=True)
    async def limpar(self, interaction: discord.Interaction, quantidade: int):
        """
        Apaga um número de mensagens do canal atual.
        Limitado a 100 mensagens por vez devido às restrições do Discord.
        """
        # Adia a resposta para o Discord não dar timeout, especialmente se a limpeza demorar.
        await interaction.response.defer(ephemeral=True)

        if quantidade <= 0:
            return await interaction.followup.send(
                embed=Embeds.erro("Valor Inválido", "A quantidade de mensagens deve ser maior que zero.", bot_user=self.bot.user),
                ephemeral=True # A mensagem de erro só será visível para quem usou o comando
            )

        if quantidade > 100:
            return await interaction.followup.send(
                embed=Embeds.erro("Limite Excedido", "Você só pode apagar até 100 mensagens por vez.", bot_user=self.bot.user),
                ephemeral=True
            )

        try:
            # O método purge do canal de texto faz a limpeza.
            # O +1 é para incluir a mensagem do próprio comando /limpar na contagem, se aplicável,
            # mas como a resposta é adiada, geralmente não é necessário. Limitamos a quantidade exata.
            deleted_messages = await interaction.channel.purge(limit=quantidade)

            # Envia uma mensagem de sucesso que só o autor do comando vê (ephemeral=True)
            await interaction.followup.send(
                embed=Embeds.sucesso("Limpeza Concluída!", f"**{len(deleted_messages)}** mensagens foram apagadas deste canal.", bot_user=self.bot.user),
                ephemeral=True
            )

        except discord.Forbidden:
            # Caso o bot não tenha a permissão necessária no canal.
            await interaction.followup.send(
                embed=Embeds.erro("Permissão Negada", "Eu não tenho permissão para apagar mensagens neste canal.", bot_user=self.bot.user),
                ephemeral=True
            )
        except Exception as e:
            # Captura outros erros inesperados.
            print(f"Erro ao executar /limpar: {e}")
            await interaction.followup.send(
                embed=Embeds.erro("Ocorreu um Erro", "Não foi possível completar a limpeza das mensagens.", bot_user=self.bot.user),
                ephemeral=True
            )

    # Tratamento de erro para o caso de o usuário não ter a permissão necessária.
    @limpar.error
    async def limpar_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=Embeds.erro("Acesso Negado", "Você não tem permissão para usar este comando.", bot_user=self.bot.user),
                ephemeral=True
            )
        else:
            # Para outros erros, envia uma mensagem genérica e loga no console.
            print(f"Erro inesperado no comando /limpar: {error}")
            await interaction.response.send_message(
                embed=Embeds.erro("Erro Inesperado", "Algo deu errado ao tentar executar o comando.", bot_user=self.bot.user),
                ephemeral=True
            )

# Função setup para carregar a cog no bot
async def setup(bot: commands.Bot):
    await bot.add_cog(UtilitariosCog(bot))
