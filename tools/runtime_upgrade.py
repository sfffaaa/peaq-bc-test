import sys
sys.path.append('./')
import os
import time

from substrateinterface import SubstrateInterface
from tools.utils import WS_URL, KP_GLOBAL_SUDO, RELAYCHAIN_WS_URL
from peaq.sudo_extrinsic import funds
from peaq.utils import show_extrinsic, get_block_height
from substrateinterface.utils.hasher import blake2_256
from peaq.utils import wait_for_n_blocks
from tools.restart import restart_parachain_launch
from peaq.utils import ExtrinsicBatch
import argparse

import pprint
pp = pprint.PrettyPrinter(indent=4)


def send_upgrade_call(substrate, kp_sudo, wasm_file):
    with open(wasm_file, 'rb') as f:
        data = f.read()
    file_hash = f'0x{blake2_256(data).hex()}'
    print(f'File hash: {file_hash}')
    batch = ExtrinsicBatch(substrate, kp_sudo)
    batch.compose_sudo_call(
        'ParachainSystem',
        'authorize_upgrade',
        {'code_hash': file_hash, 'check_version': False}
    )
    batch.compose_sudo_call(
        'ParachainSystem',
        'enact_authorized_upgrade',
        {'code': data}
    )
    return batch.execute()


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
    receipt = send_upgrade_call(substrate, KP_GLOBAL_SUDO, runtime_path)
    show_extrinsic(receipt, 'upgrade?')
    wait_relay_upgrade_block()


def fund_account():
    print('update the info')
    substrate = SubstrateInterface(url=WS_URL)
    funds(substrate, KP_GLOBAL_SUDO, [
        '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',
        '5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY',
        '5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty',
        '5HpG9w8EBLe5XCrbczpwq5TSXvedjrBGCwqxK1iQ7qUsSWFc',
        '5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y',
        '5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy',
        '5HGjWAeFDfFCWPsjFQdVV2Msvz2XtMktvgocEZcCj68kUMaw',
        '5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL',
    ], 302231 * 10 ** 18)


def do_runtime_upgrade(wasm_path):
    if not os.path.exists(wasm_path):
        raise IOError(f'Runtime not found: {wasm_path}')

    upgrade(wasm_path)
    substrate = SubstrateInterface(url=WS_URL)
    wait_for_n_blocks(substrate, 10)
    fund_account()


def main():
    parser = argparse.ArgumentParser(description='Upgrade the runtime')
    parser.add_argument('-r', '--runtime', type=str, required=True, help='Your runtime poisiton')
    parser.add_argument('-d', '--docker-restart', type=bool, default=False, help='Restart the docker container')

    args = parser.parse_args()
    if args.docker_restart:
        restart_parachain_launch()
    do_runtime_upgrade(args.runtime)
    print('Done but wait 30s')
    time.sleep(30)


if __name__ == '__main__':
    main()
