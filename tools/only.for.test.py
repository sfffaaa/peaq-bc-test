import sys
sys.path.append(".")
import time
import math
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, TOKEN_NUM_BASE_DEV
from tools.utils import get_account_balance, get_account_balance_locked
from tools.utils import check_and_fund_account

# Assumptions
# 1. Alice is the sudo key
# 2. Parachain block generation time is 12 Secs

# Global Constants
# deinfe a conneciton with a peaq-network node
substrate = SubstrateInterface(
        url=WS_URL
    )

# Global constants
KP_SUDO = Keypair.create_from_uri('//Alice')
KP_SOURCE = Keypair.create_from_uri('//Bob')
KP_TARGET = Keypair.create_from_uri('//Dave')
KP_TARGET_SECOND = Keypair.create_from_uri('//Eve')
TRANSFER_AMOUNT = 100*TOKEN_NUM_BASE_DEV
PER_BLOCK_AMOUNT = 20*TOKEN_NUM_BASE_DEV
NO_OF_BLOCKS_TO_WAIT = math.ceil(TRANSFER_AMOUNT / PER_BLOCK_AMOUNT)


if __name__ == '__main__':
    substrate = SubstrateInterface(
        url=WS_URL
    )
    call = substrate.compose_call(
        call_module='Vesting',
        call_function='vested_transfer',
        call_params={
            'target': '5GZ7f6de6HdPGrFpzAac3HDSB6bJHBvwUDqUPjBiG7dq2bTm',
            'schedule': {'locked': 10000000000000, 'per_block': 20000000000000000000, 'starting_block': 5}
        }
    )

    if 0:
        kp_special = Keypair.create_from_mnemonic(
            'credit tell tooth equip extend dinosaur shrug deny spray clerk misery erase',
            crypto_type=0)

        signed_extrinsic = substrate.create_signed_extrinsic(
            keypair=kp_special,
            nonce=1,
            era='00',
            tip=0,
            tip_asset_id=None,
            call=call,
        )
        print(f'signed_extrinsic: {signed_extrinsic}')
        print(f'call.value: {call.value}')
        print(f'call.data: {str(call.data)}')
        extrinsic_payload = substrate.generate_signature_payload(
            call=call,
            nonce=1,
            era='00',
            tip=0,
            tip_asset_id=None,
        )

        print(f'extrinsic_payload: {extrinsic_payload}')
        signature = kp_special.sign(extrinsic_payload)
        print(f'signature: 0x{signature.hex()}')
        signature = kp_special.sign(extrinsic_payload)
        print(f'signature: 0x{signature.hex()}')
        raise IOError

    fake_keypair = Keypair(
        '5ERYqxKZiar6a28fGRMwKPHdpV7L9Cxo7UHFoUzxjttQC55K',
        None, None, None, None,
        0
    )

    extrinsic = substrate.create_signed_extrinsic(
        keypair=fake_keypair,
        nonce=1,
        era='00',
        tip=0,
        tip_asset_id=None,
        call=call,
        signature='0xc6cbd02561ada0a592d3b27792239764a67918bdfce8c3881ef91079b8cdf18503e2d0a1ce71d56800bd1a79d75bcfd130b0155de3f6b2f724b14f6ae1b3d709',
    )
    print(f'extrinsic: {extrinsic}')

    receipt = substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=True,
    )

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'vestedTranser')
