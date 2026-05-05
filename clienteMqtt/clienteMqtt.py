import asyncio, ssl, certifi, logging, os
import aiomqtt

logging.basicConfig(format='%(asctime)s - [%(taskName)s] - %(levelname)s:%(message)s', level=logging.INFO, datefmt='%d/%m/%Y %H:%M:%S %z')

#Topico  de prueba 1
async def manejo_prueba1(messages):
    async for message in client.messages:
            logging.info(str(message.topic) + ": " + message.payload.decode("utf-8"))

#Topico de prueba 2
async def manejo_prueba2(messages):
   async for message in client.messages:
            logging.info(str(message.topic) + ": " + message.payload.decode("utf-8"))


#Topico 3 contador
async def manejo_contador(messages):
   while True:
        await asyncio.sleep(3)
        dicc_conteo["contador"] += 1
        logging.info("Contador incrementado: " + str(dicc_conteo["contador"]))

async def manejo_publicacion(messages):
    topico_c=os.environ['TOPICO_3']
    while True:
        await asyncio.sleep(5)
        valor=dicc_conteo["contador"] 
        await client.publish(topico_c, payload=str(valor).encode("utf-8"))
        logging.info(f"MQTT publicado en {topico_c}: {valor}")
        
async def main():
    d_contador ={"contador": 0}
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = True
    tls_context.load_default_certs()

    async with aiomqtt.Client(
        os.environ['SERVIDOR'],
        port=8883,
        tls_context=tls_context,
    ) as client:
        topico1 = "prueba/uno"
        topico2 = "prueba/dos"

        await client.subscribe(topico1)
        await client.subscribe(topico2)

        async with asyncio.TaskGroup() as grupo:
            grupo.create_task(manejo_prueba1(client.messages.filtered(topico1)),name="ManejoPrueba1")
            grupo.create_task(manejo_prueba2(client.messages.filtered(topico2)),name="ManejoPrueba2")
            grupo.create_task(manejo_contador(d_contador),name="ManejoContador")
            grupo.create_task(manejo_publicacion(client,d_contador),name="ManejoPublicacion")

if __name__ == "__main__":
    asyncio.run(main())
