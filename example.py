from client import Client

async def getData(cl):
    await cl.start()
    await cl.invoke('CoreHub', 'SubscribeToSummaryDeltas')
    while True:
        try:
            data = await cl.recv()
            pprint.pprint(json.loads(data))
            asyncio.sleep(0.5)
        except KeyboardInterrupt:
            await cl.disconnect()
            break
    return

c = Client('https://www.bittrex.com/signalr', ['CoreHub'])
asyncio.get_event_loop().run_until_complete(getData(c))