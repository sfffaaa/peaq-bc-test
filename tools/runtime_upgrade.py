import sys
sys.path.append('./')
import os

from substrateinterface import SubstrateInterface
from tools.utils import show_extrinsic, WS_URL, KP_GLOBAL_SUDO, RELAYCHAIN_WS_URL, get_block_height, funds
from substrateinterface.utils.hasher import blake2_256
from tools.payload import sudo_call_compose, sudo_extrinsic_send
from tools.utils import wait_for_n_blocks
import argparse

import pprint
pp = pprint.PrettyPrinter(indent=4)


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


def wait_until_block_height(substrate, block_height):
    current_block = get_block_height(substrate)
    block_num = block_height - current_block + 1
    wait_for_n_blocks(substrate, block_num)


def wait_relay_upgrade_block():
    relay_substrate = SubstrateInterface(url=RELAYCHAIN_WS_URL, type_registry_preset='rococo')
    result = relay_substrate.query(
        'Paras',
        'UpcomingUpgrades',
    )
    if not result.value:
        print('No upgrade scheduled')
        return

    print('Upcoming upgrade:')
    wait_until_block_height(relay_substrate, int(result.value[0][1]))


def upgrade(runtime_path):
    substrate = SubstrateInterface(url=WS_URL)
    wait_for_n_blocks(substrate, 1)

    print(f'Global Sudo: {KP_GLOBAL_SUDO.ss58_address}')
    receipt = send_ugprade_call(substrate, runtime_path)
    show_extrinsic(receipt, 'upgrade?')
    wait_relay_upgrade_block()


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


def do_runtime_upgrade(wasm_path):
    if not os.path.exists(wasm_path):
        raise IOError(f'Runtime not found: {wasm_path}')

    upgrade(wasm_path)
    substrate = SubstrateInterface(url=WS_URL)
    wait_for_n_blocks(substrate, 4)
    fund_account()


def main():
    parser = argparse.ArgumentParser(description='Upgrade the runtime')
    parser.add_argument('-r', '--runtime', type=str, required=True, help='Your runtime poisiton')

    args = parser.parse_args()
    do_runtime_upgrade(args.runtime)


if __name__ == '__main__':
    main()
