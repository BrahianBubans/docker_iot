import asyncio, ssl, certifi, logging, os
import aiomqtt
from dotenv import load_dotenv  

load_dotenv()
logging.basicConfig(format='%(asctime)s - [%(taskName)s] - %(levelname)s:%(message)s', level=logging.INFO, datefmt='%d/%m/%Y %H:%M:%S %z')

#Topico  de prueba 1
async def manejo_prueba1(payload):
        logging.info(f"Topico 1: {payload}")

#Topico de prueba 2
async def manejo_prueba2(payload):
        logging.info(f"Topico 2: {payload}")

#Topico 3 contador
async def manejo_contador(dicc_referencia):
    while True:
        await asyncio.sleep(3)
        dicc_referencia["contador"] += 1
        logging.info(f"Contador incrementado: {dicc_referencia['contador']}")


#Topico 3 publicacion del contador
async def manejo_publicacion(client, dicc_referencia):
    topico_c=os.environ['TOPICO_3']
    while True:
        await asyncio.sleep(5)
        valor=dicc_referencia["contador"] 
        await client.publish(topico_c, payload=str(valor).encode("utf-8"))
        logging.info(f"MQTT publicado en {topico_c}: {valor}")

#Para manejar los mensajes entrantes y dirigirlos a la funcion correspondiente
async def manejo_mensajes(client, t1, t2):
    async for message in client.messages:
        payload = message.payload.decode("utf-8")
        if message.topic.matches(t1):
            asyncio.create_task(manejo_prueba1(payload), name="Topico1")
        elif message.topic.matches(t2):
            asyncio.create_task(manejo_prueba2(payload), name="Topico2")

async def main():

    d_contador ={"contador": 0}
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = True
    tls_context.load_default_certs()

    servidor = os.environ.get('SERVIDOR', '').strip()
    
    async with aiomqtt.Client(
        servidor,
        port=8883,
        tls_context=tls_context,
    ) as client:
        topico1 = os.environ['TOPICO_1']
        topico2 = os.environ['TOPICO_2']

        await client.subscribe(topico1)
        await client.subscribe(topico2)

        async with asyncio.TaskGroup() as grupo:
            
            grupo.create_task(manejo_mensajes(client, topico1, topico2), name="ManejoMensajes")
            grupo.create_task(manejo_contador(d_contador), name="ManejoContador")
            grupo.create_task(manejo_publicacion(client, d_contador), name="ManejoPublicacion")

if __name__ == "__main__":
    try:
     asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("interrupcion por teclado")