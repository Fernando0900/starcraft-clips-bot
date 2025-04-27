import discord
import json
import datetime
import os
from discord.ext import commands
from dotenv import load_dotenv

# Carga las variables de entorno
load_dotenv()

# Configuración inicial
TOKEN = os.getenv('DISCORD_TOKEN')
CANAL_CLIPS_ID = int(os.getenv('CANAL_CLIPS_ID'))

# Configuración de intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Inicialización del bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Cargar datos de usuarios
def cargar_datos():
    try:
        if os.path.exists('user_clips.json'):
            with open('user_clips.json', 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error cargando datos: {e}")
    return {}

user_clips = cargar_datos()

def guardar_datos():
    try:
        with open('user_clips.json', 'w') as f:
            json.dump(user_clips, f, indent=4)
    except IOError as e:
        print(f"Error guardando datos: {e}")

def es_replay_sc2(message):
    return any(
        attachment.filename.lower().endswith('.sc2replay')
        for attachment in message.attachments
    )

async def enviar_respuesta_privada(ctx, titulo, descripcion, color):
    """Envía un mensaje embed al usuario con la hora actual"""
    try:
        await ctx.message.delete()  # Borra el mensaje del comando
    except discord.Forbidden:
        print("No tengo permisos para borrar mensajes")
    except discord.NotFound:
        print("El mensaje ya fue borrado")
    
    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=color,
        timestamp=datetime.datetime.now()
    )
    embed.set_footer(text="Starcraft Clips Bot")
    
    try:
        await ctx.author.send(embed=embed)  # Intenta enviar por MD
    except discord.Forbidden:
        # Si falla, envía mensaje efímero en el canal
        await ctx.send(embed=embed, delete_after=10)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="!reglas para ayuda"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Procesar comandos PRIMERO
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    # Luego procesar replays solo si es en el canal correcto
    if message.channel.id == CANAL_CLIPS_ID:
        if not es_replay_sc2(message):
            await message.delete()
            ctx = await bot.get_context(message)
            await enviar_respuesta_privada(
                ctx,
                "❌ Archivo no válido",
                "Solo se permiten archivos .SC2Replay en este canal.",
                discord.Color.red()
            )
            return

        user_id = str(message.author.id)
        now = datetime.datetime.now()

        if user_id in user_clips:
            last_upload = datetime.datetime.fromisoformat(user_clips[user_id])
            if (now - last_upload).days < 30:
                await message.delete()
                ctx = await bot.get_context(message)
                await enviar_respuesta_privada(
                    ctx,
                    "⏳ Límite mensual alcanzado",
                    f"Ya has enviado un replay este mes. Podrás enviar otro en {30 - (now - last_upload).days} días.",
                    discord.Color.orange()
                )
                return

        # Registrar nuevo envío
        user_clips[user_id] = now.isoformat()
        guardar_datos()

        ctx = await bot.get_context(message)
        await enviar_respuesta_privada(
            ctx,
            "✅ Replay recibido",
            "Tu replay ha sido aceptado. Podrás enviar otro en 30 días.",
            discord.Color.green()
        )

@bot.command()
async def reglas(ctx):
    """Muestra las reglas del bot"""
    await enviar_respuesta_privada(
        ctx,
        "📜 Reglas de envío de replays",
        "1. Solo se permiten archivos .SC2Replay\n"
        "2. Cada usuario puede enviar **1 replay cada 30 días**\n"
        "3. Los replays deben ser de tu autoría\n\n"
        "¡Gracias por participar!",
        discord.Color.purple()
    )

@bot.command()
async def mi_estado(ctx):
    """Muestra cuándo puedes enviar tu próximo replay"""
    user_id = str(ctx.author.id)
    if user_id in user_clips:
        last_upload = datetime.datetime.fromisoformat(user_clips[user_id])
        dias_restantes = 30 - (datetime.datetime.now() - last_upload).days
        if dias_restantes > 0:
            await enviar_respuesta_privada(
                ctx,
                "⏳ Tu estado",
                f"Podrás enviar tu próximo replay en {dias_restantes} días.",
                discord.Color.orange()
            )
        else:
            await enviar_respuesta_privada(
                ctx,
                "✅ Listo para enviar",
                "Ya puedes enviar un nuevo replay.",
                discord.Color.green()
            )
    else:
        await enviar_respuesta_privada(
            ctx,
            "✅ Listo para enviar",
            "Aún no has enviado ningún replay. ¡Puedes enviar uno ahora!",
            discord.Color.green()
        )

@bot.command()
@commands.has_permissions(administrator=True)
async def reset_user(ctx, usuario: discord.Member):
    """Resetea el contador de un usuario (SOLO ADMINS)"""
    user_id = str(usuario.id)
    if user_id in user_clips:
        del user_clips[user_id]
        guardar_datos()
        await enviar_respuesta_privada(
            ctx,
            "🔄 Contador reseteado",
            f"Has reseteado el contador para {usuario.display_name}",
            discord.Color.blue()
        )
    else:
        await enviar_respuesta_privada(
            ctx,
            "⚠️ Usuario no encontrado",
            f"No se encontraron registros para {usuario.display_name}",
            discord.Color.gold()
        )

bot.run(TOKEN)