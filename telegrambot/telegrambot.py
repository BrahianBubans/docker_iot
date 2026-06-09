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

active_chats = set()
estado_rele = 1

# Estructura para gestión de estados de la interfaz
estado_sistema = {
    "modo": "auto",
    "esperando_input": None
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_chats.add(update.message.chat.id)
    logging.info("se conectó: " + str(update.message.from_user.id))
    nombre = update.message.from_user.first_name if update.message.from_user.first_name else ""
    apellido = update.message.from_user.last_name if update.message.from_user.last_name else ""
    
    kb = [
        ["MODO AUTOMATICO", "MODO MANUAL"],
        ["SETPOINT", "PERIODO"],
        ["RELE", "DESTELLO"]
    ]
    
    await context.bot.send_message(update.message.chat.id, text="Bienvenido al Bot " + nombre + " " + apellido, reply_markup=ReplyKeyboardMarkup(kb))

async def acercade(update: Update, context):
    await context.bot.send_message(update.message.chat.id, text="Este bot fue creado para el curso de IoT FIO")

async def enviar_comando_mqtt(topico, payload):
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = False
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

async def automatico(update: Update, context):
    estado_sistema["modo"] = "auto"
    estado_sistema["esperando_input"] = None
    await enviar_comando_mqtt(f"{ID_DISPOSITIVO}/modo", "auto")
    await context.bot.send_message(update.message.chat.id, text="config: MODO AUTOMATICO emitido.")

async def manual(update: Update, context):  
    estado_sistema["modo"] = "manual"
    estado_sistema["esperando_input"] = None
    await enviar_comando_mqtt(f"{ID_DISPOSITIVO}/modo", "manual")
    await context.bot.send_message(update.message.chat.id, text="config: MODO MANUAL emitido. (habilitados SETPOINT, PERIODO y RELE)")

async def destello(update: Update, context):
    await enviar_comando_mqtt(f"{ID_DISPOSITIVO}/destello", "1")
    await context.bot.send_message(update.message.chat.id, text="comando: DESTELLO emitido.")

async def rele(update: Update, context):
    if estado_sistema["modo"] != "manual":
        await context.bot.send_message(update.message.chat.id, text="NO ES POSIBLE. El sistema opera en MODO AUTOMATICO.")
        return

    global estado_rele
    estado_rele = 0 if estado_rele == 1 else 1
    await enviar_comando_mqtt(f"{ID_DISPOSITIVO}/rele", str(estado_rele))
    estado_texto = "ENCENDIDO" if estado_rele == 0 else "APAGADO"
    await context.bot.send_message(update.message.chat.id, text=f"comando: RELE {estado_texto} emitido.")

async def pedir_setpoint(update: Update, context):
    if estado_sistema["modo"] != "manual":
        await context.bot.send_message(update.message.chat.id, text="NO ES POSIBLE. El sistema opera en MODO AUTOMATICO.")
        return

    estado_sistema["esperando_input"] = "setpoint"
    await context.bot.send_message(update.message.chat.id, text="Ingrese el valor de temperatura para el SETPOINT (entero):")

async def pedir_periodo(update: Update, context):
    if estado_sistema["modo"] != "manual":
        await context.bot.send_message(update.message.chat.id, text="NO ES POSIBLE. El sistema opera en MODO AUTOMATICO.")
        return

    estado_sistema["esperando_input"] = "periodo"
    await context.bot.send_message(update.message.chat.id, text="Ingrese el valor en segundos para el PERIODO (entero):")

async def procesar_entrada_texto(update: Update, context):
    esperando = estado_sistema["esperando_input"]
    if not esperando:
        return

    texto = update.message.text.strip()
    
    try:
        if esperando == "setpoint":
            valor = float(texto)
            await enviar_comando_mqtt(f"{ID_DISPOSITIVO}/setpoint", str(valor))
            await context.bot.send_message(update.message.chat.id, text=f"parametro actualizado: SETPOINT = {valor}°C")
            
        elif esperando == "periodo":
            valor = int(texto)
            await enviar_comando_mqtt(f"{ID_DISPOSITIVO}/periodo", str(valor))
            await context.bot.send_message(update.message.chat.id, text=f"parametro actualizado: PERIODO = {valor} segundos")
        
        estado_sistema["esperando_input"] = None
        
    except ValueError:
        await context.bot.send_message(update.message.chat.id, text="Error de formato. Ingrese un valor numérico válido.")

async def mqtt_listener(application: Application):
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = False
    tls_context.load_default_certs()
    
    while True:
        try:
            async with aiomqtt.Client(
                hostname=MQTT_BROKER,
                port=MQTT_PORT,
                username=MQTT_USER,
                password=MQTT_PASS,
                tls_context=tls_context
            ) as client:
                await client.subscribe(ID_DISPOSITIVO)
                async for message in client.messages:
                    payload = message.payload.decode()
                    datos = json.loads(payload)
                    msg_text = (
                        f"datos desde el micro:\n"
                        f"temp: {datos['temperatura']}°C - hum: {datos['humedad']}%\n"
                        f"modo: {datos['modo'].upper()} - setpoint: {datos['setpoint']}°C"
                    )
                    for chat_id in list(active_chats):
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=msg_text)
                        except Exception as e:
                            logging.error(f"fallo de transmision al chat {chat_id}: {e}")
        except Exception as e:
            logging.error(f"fallo en listener MQTT. Reiniciando ciclo: {e}")
            await asyncio.sleep(5)

async def post_init(application: Application):
    asyncio.create_task(mqtt_listener(application))

def main():
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
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
    application.add_handler(MessageHandler(filters.Regex(re.compile("^(SETPOINT)$", re.IGNORECASE)), pedir_setpoint))
    application.add_handler(MessageHandler(filters.Regex(re.compile("^(PERIODO)$", re.IGNORECASE)), pedir_periodo))
    
    # Manejador genérico de texto para procesar los ingresos numéricos (debe registrarse al final)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_entrada_texto))
    
    application.run_polling()

if __name__ == '__main__':
    main()