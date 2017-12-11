from client import Client
import asyncio
import pprint

async def getData(cl):
    await cl.start()
    await cl.invoke('CoreHub', 'SubscribeToSummaryDeltas')
    for _ in range(10):
        try:
            data = await cl.recv()
            #pprint.pprint(json.loads(data))
            print(data)
            asyncio.sleep(0.5)
        except Exception as e:
            print(e)
            await cl.disconnect()
    await cl.disconnect()
    return

c = Client('https://www.bittrex.com/signalr', ['CoreHub'])
loop = asyncio.get_event_loop()
loop.run_until_complete(getData(c))
loop.close()