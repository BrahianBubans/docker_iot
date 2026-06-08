from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import logging, os, asyncio, re, json, ssl
import aiomqtt

token = os.environ["TB_TOKEN"]
ID_DISPOSITIVO = os.environ["PICO_DEVICE_ID"]
MQTT_BROKER = os.environ["SERVIDOR"]
MQTT_PORT = int(os.environ["PUERTO_MQTTS"])
MQTT_USER = os.environ["MQTT_USR"]
MQTT_PASS = os.environ["MQTT_PASS"]

logging.basicConfig(format='%(asctime)s - TelegramBot - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("se conectó: " + str(update.message.from_user.id))
    nombre = update.message.from_user.first_name if update.message.from_user.first_name else ""
    apellido = update.message.from_user.last_name if update.message.from_user.last_name else ""
    kb = [["MODO AUTOMATICO"], ["MODO MANUAL"], ["DESTELLO"], ["RELE"]]
    await context.bot.send_message(update.message.chat.id, text="Bienvenido al Bot " + nombre + " " + apellido, reply_markup=ReplyKeyboardMarkup(kb))

async def acercade(update: Update, context):
    await context.bot.send_message(update.message.chat.id, text="Este bot fue creado para el curso de IoT FIO")

async def automatico(update: Update, context):
    await context.bot.send_message(update.message.chat.id, text="Modo automático activado. El sistema ajustará el setpoint y el periodo según las condiciones actuales.")

async def manual(update: Update, context):  
    await context.bot.send_message(update.message.chat.id, text="Modo manual activado. El sistema operará con los parámetros establecidos por el usuario.")

async def enviar_comando_mqtt(topico, payload):
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = True
    tls_context.load_default_certs()
    
    try:
        async with aiomqtt.Client(
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            username=MQTT_USER,
            password=MQTT_PASS,
            tls_context=tls_context,
            timeout=5
        ) as client:
            await client.publish(topico, payload=payload, qos=1)
            logging.info(f"MQTT Publicado: {topico} -> {payload}")
            return True
    except aiomqtt.MqttError as e:
        logging.error(f"Error de conexión o publicación MQTT: {e}")
        return False

async def destello(update: Update, context):
    topico_destello = f"{ID_DISPOSITIVO}/destello"
    exito = await enviar_comando_mqtt(topico_destello, "1")
    
    if exito:
        await context.bot.send_message(update.message.chat.id, text="Comando DESTELLO transmitido por MQTT.")
    else:
        await context.bot.send_message(update.message.chat.id, text="Fallo de transmisión al broker MQTT.")

async def rele(update: Update, context):
    topico_rele = f"{ID_DISPOSITIVO}/rele"
    # El payload debe ser "0" (encendido) o "1" (apagado) para ser convertido a entero en la placa.
    exito = await enviar_comando_mqtt(topico_rele, "0")
    
    if exito:
        await context.bot.send_message(update.message.chat.id, text="Comando RELE transmitido por MQTT.")
    else:
        await context.bot.send_message(update.message.chat.id, text="Fallo de transmisión al broker MQTT.")

def main():
    application = (
        Application.builder()
        .token(token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('acercade', acercade))
    application.add_handler(MessageHandler(filters.Regex(re.compile("^(MODO AUTOMATICO|AUTO|AUTOMATICO)$", re.IGNORECASE)), automatico))
    application.add_handler(MessageHandler(filters.Regex(re.compile("^(MODO MANUAL|MANUAL)$", re.IGNORECASE)), manual))
    application.add_handler(MessageHandler(filters.Regex(re.compile("^(DESTELLO)$", re.IGNORECASE)), destello))
    application.add_handler(MessageHandler(filters.Regex(re.compile("^(RELE)$", re.IGNORECASE)), rele))
    application.run_polling()

if __name__ == '__main__':
    main()