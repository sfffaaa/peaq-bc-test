import sys
sys.path.append('./')
import os

from peaq.utils import ExtrinsicBatch
from peaq.utils import show_extrinsic
from substrateinterface import SubstrateInterface
from peaq.utils import wait_for_n_blocks
from tools.runtime_upgrade import send_upgrade_call
from tools.runtime_upgrade import wait_relay_upgrade_block
from tools.utils import KP_GLOBAL_SUDO
# from tools.asset import convert_enum_to_asset_id
import argparse


PEAQ_WS_URL = 'wss://docker-test.peaq.network'
RELAY_WS_URL = 'wss://docker1-test.peaq.network'

RELAY_TOKEN_ASSET_ID = 1
ACA_TOKEN_ASSET_ID = 2


# def setup_relay_token(substrate, asset_id):
#     asset = substrate.query("Assets", "Asset", [convert_enum_to_asset_id({'Token': asset_id})])
#     if asset.value:
#         return
#     batch = ExtrinsicBatch(substrate, KP_GLOBAL_SUDO)
#     batch_register_asset(batch, asset_id, "Relay Token", "RT")
#
#
# def setup_aca_token(substrate, asset_id):
#     pass


def parachain_behaviour(wasm_path):
    substrate = SubstrateInterface(url=PEAQ_WS_URL)

    # Do the runtime upgrade for the docker env: peaq env
    do_runtime_upgrade(substrate, wasm_path)

    # setup_relay_token(substrate, RELAY_TOKEN_ASSET_ID)
    # setup_aca_token(substrate, ACA_TOKEN_ASSET_ID)

    # Setup the relay chain asset with ? : peaq env
    # Setup the aca chain asset with ? : peaq env
    # Setup the relay chain's multi location: peaq env


def upgrade(substrate, runtime_path):
    wait_for_n_blocks(substrate, 1)

    print(f'Global Sudo: {KP_GLOBAL_SUDO.ss58_address}')
    receipt = send_upgrade_call(substrate, KP_GLOBAL_SUDO, runtime_path)
    show_extrinsic(receipt, 'upgrade?')
    wait_relay_upgrade_block(RELAY_WS_URL)


def do_runtime_upgrade(substrate, wasm_path):
    if not os.path.exists(wasm_path):
        raise IOError(f'Runtime not found: {wasm_path}')

    upgrade(substrate, wasm_path)
    wait_for_n_blocks(substrate, 10)


def setup_slot(substrate):
    result = substrate.query(
        'Paras',
        'Parachains',
    )
    batch = ExtrinsicBatch(substrate, KP_GLOBAL_SUDO)
    for para_id in result.value:
        batch.compose_sudo_call(
            'Slots',
            'force_lease',
            {
                'para': para_id,
                'leaser': KP_GLOBAL_SUDO.ss58_address,
                'amount': 0,
                'period_begin': 0,
                'period_count': 365,
            }
        )
    receipt = batch.execute()
    show_extrinsic(receipt, 'force_lease?')


def relaychain_behavior():
    substrate = SubstrateInterface(url=RELAY_WS_URL)
    setup_slot(substrate)


def main():
    parser = argparse.ArgumentParser(description='Upgrade the runtime')
    parser.add_argument('-r', '--runtime', required=True, type=str, help='Your runtime poisiton')

    args = parser.parse_args()
    runtime_path = args.runtime

    parachain_behaviour(runtime_path)
    relaychain_behavior()


if __name__ == '__main__':
    main()
