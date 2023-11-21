from substrateinterface import SubstrateInterface
import datetime
import time


WS = 'wss://docker-test.peaq.network'

while 1:
    before = datetime.datetime.now()
    substrate = SubstrateInterface(
        url=WS,
    )
    substrate.get_block_metadata()
    after = datetime.datetime.now()
    print(f'{after}: {after - before}')
    time.sleep(5)
    substrate.close()
