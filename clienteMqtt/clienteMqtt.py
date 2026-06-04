import asyncio
import ssl
import logging
import os
import aiomqtt

logging.basicConfig(format='%(asctime)s - ClienteMQTT - %(levelname)s - %(message)s', level=logging.INFO)

ID_DISPOSITIVO = os.environ.get("PICO_DEVICE_ID", "TU_ID_DE_LA_PICO_AQUI")

async def main():
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = True
    tls_context.load_default_certs()

    while True:
        try:
            logging.info("Conectando al Broker MQTTS...")
            async with aiomqtt.Client(
                hostname=os.environ["SERVIDOR"],
                port=int(os.environ["PUERTO_MQTTS"]),
                username=os.environ["MQTT_USR"],
                password=os.environ["MQTT_PASS"],
                tls_context=tls_context,
                timeout=10
            ) as client:
                
                topico_escucha = f"{ID_DISPOSITIVO}/+"
                await client.subscribe(topico_escucha)
                logging.info(f"Suscrito a: {topico_escucha}")
                
                # Procesamiento seguro de mensajes
                async with client.messages() as messages:
                    async for message in messages:
                        topico = str(message.topic)
                        payload = message.payload.decode("utf-8")
                        print(f"[BROKER] {topico} -> {payload}")
                        
        except aiomqtt.MqttError as e:
            logging.error(f"Error de conexión o pérdida de enlace: {e}. Reintentando en 5 segundos...")
            await asyncio.sleep(5)
        except Exception as general_error:
            logging.critical(f"Falla inesperada: {general_error}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())