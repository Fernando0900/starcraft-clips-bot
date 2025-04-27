import discord
import json
import datetime
import os
import logging
from discord.ext import commands
from dotenv import load_dotenv

# Configuración mejorada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('starcraft_bot')

# Carga las variables de entorno
load_dotenv()

# Validación de variables de entorno
required_vars = {
    'DISCORD_TOKEN': 'Token de Discord',
    'CANAL_CLIPS_ID': 'ID del canal de clips'
}

for var, desc in required_vars.items():
    if not os.environ.get(var):
        logger.error(f"Falta la variable requerida: {desc} ({var})")
        exit(1)

TOKEN = os.environ['DISCORD_TOKEN']
CANAL_CLIPS_ID = int(os.environ['CANAL_CLIPS_ID'])

# Configuración de intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Inicialización del bot
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None
)

# Manejo de datos
DATA_FILE = os.path.join(os.path.dirname(__file__), 'user_clips.json')

def cargar_datos():
    """Carga los datos de usuarios desde el archivo JSON"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error cargando datos: {str(e)}")
        return {}

def guardar_datos():
    """Guarda los datos de usuarios en el archivo JSON"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_clips, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Error guardando datos: {str(e)}")

user_clips = cargar_datos()

# Funciones utilitarias
def es_replay_sc2(message):
    """Verifica si el mensaje contiene un archivo .SC2Replay"""
    return any(
        attachment.filename.lower().endswith('.sc2replay')
        for attachment in message.attachments
    )

async def enviar_respuesta_privada(ctx, titulo, descripcion, color):
    """Envía un mensaje embed al usuario"""
    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Starcraft Clips Bot")
    
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    
    try:
        await ctx.author.send(embed=embed)
    except discord.Forbidden:
        await ctx.send(embed=embed, delete_after=15)

# Eventos del bot
@bot.event
async def on_ready():
    """Evento cuando el bot se conecta exitosamente"""
    logger.info(f'Conectado como {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="!ayuda"))

@bot.event
async def on_message(message):
    """Procesa todos los mensajes recibidos"""
    if message.author.bot:
        return

    # Procesar comandos primero
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    # Procesar replays en el canal designado
    if message.channel.id == CANAL_CLIPS_ID:
        await procesar_replay(message)

async def procesar_replay(message):
    """Procesa los mensajes con replays en el canal designado"""
    if not es_replay_sc2(message):
        ctx = await bot.get_context(message)
        await enviar_respuesta_privada(
            ctx,
            "❌ Archivo no válido",
            "Solo se permiten archivos .SC2Replay en este canal.",
            discord.Color.red()
        )
        await message.delete()
        return

    user_id = str(message.author.id)
    now = datetime.datetime.now(datetime.timezone.utc)

    if user_id in user_clips:
        last_upload = datetime.datetime.fromisoformat(user_clips[user_id])
        dias_restantes = 30 - (now - last_upload).days
        if dias_restantes > 0:
            ctx = await bot.get_context(message)
            await enviar_respuesta_privada(
                ctx,
                "⏳ Límite mensual alcanzado",
                f"Ya has enviado un replay este mes. Podrás enviar otro en {dias_restantes} días.",
                discord.Color.orange()
            )
            await message.delete()
            return

    # Registrar nuevo replay
    user_clips[user_id] = now.isoformat()
    guardar_datos()

    ctx = await bot.get_context(message)
    await enviar_respuesta_privada(
        ctx,
        "✅ Replay recibido",
        "Tu replay ha sido aceptado. Podrás enviar otro en 30 días.",
        discord.Color.green()
    )

# Comandos del bot
@bot.command(name='ayuda')
async def ayuda(ctx):
    """Muestra información de ayuda"""
    embed = discord.Embed(
        title="📜 Ayuda del Bot de Starcraft Clips",
        description="Comandos disponibles:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="!ayuda",
        value="Muestra este mensaje de ayuda",
        inline=False
    )
    embed.add_field(
        name="!estado",
        value="Muestra cuándo puedes enviar tu próximo replay",
        inline=False
    )
    embed.add_field(
        name="Subir replay",
        value="Envía un archivo .SC2Replay al canal designado",
        inline=False
    )
    embed.set_footer(text="Límite: 1 replay cada 30 días por usuario")
    
    await ctx.author.send(embed=embed)
    await ctx.message.delete()

@bot.command(name='estado')
async def estado(ctx):
    """Muestra el estado de envíos del usuario"""
    user_id = str(ctx.author.id)
    
    if user_id in user_clips:
        last_upload = datetime.datetime.fromisoformat(user_clips[user_id])
        dias_restantes = 30 - (datetime.datetime.now(datetime.timezone.utc) - last_upload).days
        
        if dias_restantes > 0:
            await enviar_respuesta_privada(
                ctx,
                "⏳ Estado actual",
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

@bot.command(name='reset_user')
@commands.has_permissions(administrator=True)
async def reset_user(ctx, usuario: discord.Member):
    """Resetea el contador de un usuario (Solo admins)"""
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

# Sistema keep-alive para Render
def iniciar_servidor_web():
    """Inicia un servidor web simple para mantener vivo el bot en Render"""
    try:
        from flask import Flask
        import threading
        
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return "Bot de Starcraft Clips en funcionamiento"
        
        @app.route('/health')
        def health_check():
            return "OK", 200
        
        def run():
            app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        logger.info("Servidor web iniciado en el puerto 8080")
        
    except ImportError:
        logger.warning("Flask no está instalado. El servidor web no se iniciará")

# Iniciar servidor web si está en Render
if 'RENDER' in os.environ:
    iniciar_servidor_web()

# Manejo de errores
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await enviar_respuesta_privada(
            ctx,
            "⚠️ Permisos insuficientes",
            "No tienes permisos para ejecutar este comando.",
            discord.Color.red()
        )
    else:
        logger.error(f"Error en comando {ctx.command}: {str(error)}")
        await enviar_respuesta_privada(
            ctx,
            "❌ Error inesperado",
            "Ocurrió un error al procesar el comando.",
            discord.Color.red()
        )

# Iniciar el bot
try:
    logger.info("Iniciando bot...")
    bot.run(TOKEN)
except discord.LoginFailure:
    logger.error("Autenticación fallida. Verifica el token de Discord.")
except Exception as e:
    logger.error(f"Error fatal: {str(e)}")
finally:
    logger.info("Bot detenido")