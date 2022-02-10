import sys
import time
import json
from substrateinterface import SubstrateInterface, Keypair
from utils import fund, send_service_request
from utils import deposit_money_to_multsig_wallet
from utils import _approve_token
from threading import Thread
import requests

import eventlet
eventlet.monkey_patch()


def user_simulation_test(kp_consumer):
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        substrate = SubstrateInterface(
            url="ws://127.0.0.1:9944",
        )
    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()

    kp_provider = Keypair.create_from_uri('//Alice')
    # Fund first
    fund(substrate, kp_consumer, 500)

    token_deposit = 10
    deposit_money_to_multsig_wallet(substrate, kp_consumer, kp_provider, token_deposit)
    send_service_request(substrate, kp_consumer, kp_provider, token_deposit)
    print('---- charging start and wait')


class SubstrateMonitor():
    def __init__(self, kp_consumer, threshold):
        self._threshold = threshold
        self._kp_consumer = kp_consumer
        try:
            # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
            # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
            self._substrate = SubstrateInterface(
                url="ws://127.0.0.1:9944",
            )
        except ConnectionRefusedError:
            print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
            sys.exit()

    def subscription_event_handler(self, objs, update_nr, subscription_id):
        for obj in objs:
            event = obj['event'].value
            if event['event_id'] == 'ServiceRequested':
                time.sleep(10)
                print('---- send request !!')
                requests.post('http://127.0.0.1:25566/end_charging',
                              data=json.dumps({'success': True}))
            if event['event_id'] == 'ServiceDelivered':
                provider_addr = event['attributes'][0]
                info = {
                    'token_num': event['attributes'][2],
                    'timepoint': event['attributes'][4],
                    'call_hash': event['attributes'][5]
                }
                _approve_token(
                    self._substrate, self._kp_consumer, [provider_addr], self._threshold, info)
            print(f"{event['event_id']}: {event['attributes']}")
            continue

    def run_substrate_monitor(self):
        self._substrate.query("System", "Events", None,
                              subscription_handler=self.subscription_event_handler)


if __name__ == '__main__':
    kp_consumer = Keypair.create_from_uri('//Alice/stash')
    monitor = SubstrateMonitor(kp_consumer, 2)
    monitor_thread = Thread(target=monitor.run_substrate_monitor)
    monitor_thread.start()

    user_simulation_test(kp_consumer)
    monitor_thread.join()
