import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface
from tools.utils import show_extrinsic, WS_URL, KP_GLOBAL_SUDO, RELAYCHAIN_WS_URL, get_block_height, funds
from substrateinterface.utils.hasher import blake2_256
from tools.payload import sudo_call_compose, sudo_extrinsic_send
import time

import pprint
pp = pprint.PrettyPrinter(indent=4)

RUNTIME_MODULE_PATH = '/home/jaypan/PublicSMB/peaq_dev_runtime.compact.compressed.wasm'


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def send_ugprade_call(substrate, wasm_file):
    with open(wasm_file, 'rb') as f:
        data = f.read()
    file_hash = f'0x{blake2_256(data).hex()}'
    print(f'File hash: {file_hash}')

    payloads = [
        substrate.compose_call(
            call_module='ParachainSystem',
            call_function='authorize_upgrade',
            call_params={'code_hash': file_hash}
        ),
        substrate.compose_call(
            call_module='ParachainSystem',
            call_function='enact_authorized_upgrade',
            call_params={'code': data}
        )
    ]

    batch_payload = substrate.compose_call(
        call_module='Utility',
        call_function='batch_all',
        call_params={
            'calls': payloads,
        })
    return batch_payload


def wait_untile_block_height(substrate, block_height):
    current_block = get_block_height(substrate)
    while current_block < block_height:
        print(f'Current block: {current_block}, but waiting at {block_height}')
        time.sleep(12)
        current_block = get_block_height(substrate)
    print(f'Upgrade block: {block_height}, now block is {current_block}')


def get_relay_upgrade_block():
    relay_substrate = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')
    result = relay_substrate.query(
        'Paras',
        'UpcomingUpgrades',
    )
    if not result.value:
        print('No upgrade scheduled')
        return

    print('Upcoming upgrade:')
    wait_untile_block_height(relay_substrate, int(result.value[0][1]))


def upgrade():
    substrate = SubstrateInterface(url=WS_URL)
    wait_untile_block_height(substrate, 1)

    print(f'Global Sudo: {KP_GLOBAL_SUDO.ss58_address}')
    receipt = send_ugprade_call(substrate, RUNTIME_MODULE_PATH)
    show_extrinsic(receipt, 'upgrade?')
    get_relay_upgrade_block()


def fund_account():
    print('update the info')
    substrate = SubstrateInterface(url=WS_URL)
    funds(substrate, [
        '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',
        '5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty',
        '5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y',
        '5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy',
        '5HGjWAeFDfFCWPsjFQdVV2Msvz2XtMktvgocEZcCj68kUMaw',
        '5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL'
    ], 302231 * 10 ** 18)


if __name__ == '__main__':
    fund_account()
    upgrade()
