import discord
import json
import datetime
import os
import logging
from discord.ext import commands
from dotenv import load_dotenv

# Configuración avanzada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('starcraft_bot')

# Carga de variables de entorno
load_dotenv()

# Validación de configuración
TOKEN = os.getenv('DISCORD_TOKEN')
CANAL_CLIPS_ID = int(os.getenv('CANAL_CLIPS_ID', 0))

if not TOKEN:
    logger.error("ERROR: Falta la variable DISCORD_TOKEN")
    exit(1)

if not CANAL_CLIPS_ID:
    logger.error("ERROR: Falta la variable CANAL_CLIPS_ID")
    exit(1)

# Configuración de intents (IMPORTANTE)
intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix='!', 
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# Manejo de datos
DATA_FILE = os.path.join(os.path.dirname(__file__), 'user_clips.json')

def cargar_datos():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error cargando datos: {str(e)}")
        return {}

def guardar_datos():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_clips, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando datos: {str(e)}")

user_clips = cargar_datos()

# Funciones utilitarias
def es_replay_sc2(message):
    return any(
        attachment.filename.lower().endswith('.sc2replay')
        for attachment in message.attachments
    )

async def enviar_respuesta(ctx, titulo, descripcion, color):
    """Envía mensajes embebidos con manejo de errores"""
    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Starcraft Clips Bot")
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    try:
        await ctx.author.send(embed=embed)
    except:
        try:
            await ctx.send(embed=embed, delete_after=15)
        except Exception as e:
            logger.error(f"Error enviando mensaje: {str(e)}")

# Eventos principales
@bot.event
async def on_ready():
    """Evento cuando el bot se conecta"""
    logger.info(f'✅ Bot conectado como: {bot.user}')
    logger.info(f'📡 En {len(bot.guilds)} servidor(es)')
    
    for guild in bot.guilds:
        logger.info(f' - {guild.name} (ID: {guild.id})')
        
    await bot.change_presence(activity=discord.Game(name="!ayuda"))

@bot.event
async def on_message(message):
    """Manejador principal de mensajes"""
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
    """Procesa los archivos .SC2Replay"""
    ctx = await bot.get_context(message)
    
    if not es_replay_sc2(message):
        await enviar_respuesta(
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
            await enviar_respuesta(
                ctx,
                "⏳ Límite mensual",
                f"Espera {dias_restantes} días para subir otro replay.",
                discord.Color.orange()
            )
            await message.delete()
            return

    # Registrar nuevo replay
    user_clips[user_id] = now.isoformat()
    guardar_datos()
    
    await enviar_respuesta(
        ctx,
        "✅ Replay aceptado",
        "Archivo recibido correctamente. Podrás subir otro en 30 días.",
        discord.Color.green()
    )

# Comandos principales
@bot.command(name='ayuda')
async def ayuda(ctx):
    """Muestra la ayuda del bot"""
    embed = discord.Embed(
        title="📜 Ayuda del Bot",
        description="Comandos disponibles:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="!ayuda",
        value="Muestra este mensaje",
        inline=False
    )
    embed.add_field(
        name="!estado",
        value="Muestra tu estado de subidas",
        inline=False
    )
    embed.add_field(
        name="Subir replay",
        value="Envía un .SC2Replay a este canal",
        inline=False
    )
    
    await ctx.author.send(embed=embed)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name='estado')
async def estado(ctx):
    """Muestra el estado de subidas del usuario"""
    user_id = str(ctx.author.id)
    
    if user_id in user_clips:
        last_upload = datetime.datetime.fromisoformat(user_clips[user_id])
        dias_restantes = 30 - (datetime.datetime.now(datetime.timezone.utc) - last_upload).days
        
        if dias_restantes > 0:
            await enviar_respuesta(
                ctx,
                "⏳ Estado actual",
                f"Podrás subir otro replay en {dias_restantes} días.",
                discord.Color.orange()
            )
        else:
            await enviar_respuesta(
                ctx,
                "✅ Listo para subir",
                "Ya puedes enviar un nuevo replay.",
                discord.Color.green()
            )
    else:
        await enviar_respuesta(
            ctx,
            "✅ Primer replay",
            "Puedes subir tu primer replay cuando quieras!",
            discord.Color.green()
        )

@bot.command(name='test')
async def test(ctx):
    """Comando de prueba"""
    perms = ctx.channel.permissions_for(ctx.me)
    
    embed = discord.Embed(
        title="✅ Prueba exitosa",
        description="El bot está funcionando correctamente",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Permisos en este canal",
        value=f"Leer mensajes: {'✅' if perms.read_messages else '❌'}\n"
              f"Enviar mensajes: {'✅' if perms.send_messages else '❌'}\n"
              f"Ver historial: {'✅' if perms.read_message_history else '❌'}",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Sistema keep-alive para Render
def iniciar_servidor_web():
    try:
        from flask import Flask
        import threading
        
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return "Bot de Starcraft en línea"
        
        @app.route('/health')
        def health():
            return "OK", 200
            
        thread = threading.Thread(
            target=lambda: app.run(
                host='0.0.0.0',
                port=8080,
                debug=False,
                use_reloader=False
            )
        )
        thread.daemon = True
        thread.start()
        logger.info("🔄 Servidor web iniciado en puerto 8080")
    except ImportError:
        logger.warning("Flask no instalado. Servidor web no iniciado")

# Iniciar servidor web si está en Render
if 'RENDER' in os.environ:
    iniciar_servidor_web()

# Manejo de errores
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error(f"Error en comando: {str(error)}")
    await enviar_respuesta(
        ctx,
        "❌ Error",
        f"Ocurrió un error: {str(error)}",
        discord.Color.red()
    )

# Inicio del bot
try:
    logger.info("🚀 Iniciando bot...")
    bot.run(TOKEN)
except Exception as e:
    logger.error(f"❌ Error fatal: {str(e)}")
finally:
    logger.info("🔴 Bot detenido")