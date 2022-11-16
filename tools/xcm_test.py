import sys
sys.path.append('./')

import time
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL as PEAQ_WS_URL, ACA_WS_URL, ROCOCO_WS_URL
from tools.utils import PEAQ_PARACHAIN_ID, ACA_PARACHAIN_ID
from tools.two_address_substrate_with_extrinsic import show_account


ACA_TOKEN = {'Token': 'ACA'}
ACA_FORIGN_ASSET = {'ForeignAsset': 0}
PEAQ_TOKEN = {'Token': 'PEAQ'}
PEAQ_FORIGN_ASSET = {'ForeignAsset': 0}

WEIGHT_LIMIT_RATE = 0.99

ACA_LOCATION = {
    'V1': {
        'parents': 1,
        'interior': {
            'X2': [{
                'Parachain': ACA_PARACHAIN_ID
            }, {
                'GeneralKey': '0x0000'
            }]
        }
    }
}


ACA_METADATA = {
    'name': 'ACA',
    'symbol': 'ACA',
    'decimals': 15,
    'minimal_balance': 0
}


PEAQ_LOCATION = {
    'V1': {
        'parents': 1,
        'interior': {
            'X2': [{
                'Parachain': PEAQ_PARACHAIN_ID
            }, {
                'GeneralKey': '0x0000'
            }]
        }
    }
}


PEAQ_METADATA = {
    'name': 'PEAQ',
    'symbol': 'PEAQ',
    'decimals': 18,
    'minimal_balance': 0
}

WAIT_BLOCK_TIME = 3
SLEEP_TIME = WAIT_BLOCK_TIME * 12


def setup_foreign_asset(substrate, kp_src, location, metadata):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    payload = substrate.compose_call(
        call_module='AssetRegistry',
        call_function='register_foreign_asset',
        call_params={
            'location': location,
            'metadata': metadata,
        })

    sudo = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo',
        call_params={
            'call': payload.value,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=sudo,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'sudo + register_foreign_asset')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    return receipt


def asset_aca_get(substrate, kp_src):
    result = substrate.query("Tokens", "Accounts", [kp_src.ss58_address, {'ForeignAsset': 0}])
    return result


def asset_peaq_get(substrate, kp_src):
    result = substrate.query("Tokens", "Accounts", [kp_src.ss58_address, {'ForeignAsset': 0}])
    return result


def asset_dot_get(substrate, kp_src):
    result = substrate.query("Tokens", "Accounts", [kp_src.ss58_address, {'Token': 'DOT'}])
    return result


def transfer_xcm_token(substrate, kp_src, token_num, token, parachain_id):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    xcm_transfer = substrate.compose_call(
        call_module='XTokens',
        call_function='transfer',
        call_params={
            'currency_id': token,
            'amount': token_num,
            'dest': {
                'V1': {
                    'parents': 1,
                    'interior': {
                        'X2': [{
                            'Parachain': parachain_id
                        }, {
                            'AccountId32': [
                                'Any',
                                f'0x{kp_src.public_key.hex()}'
                            ]
                        }]
                    }
                }
            },
            'dest_weight': 20000000000
        })
    extrinsic = substrate.create_signed_extrinsic(
        call=xcm_transfer,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'aca: xcm_transfer')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    return receipt


def acala_to_peaq_test():
    print('---- acala to peaq !! ----')
    try:
        current_balance = 0
        latest_balance = 0
        token_num = 100000
        kp_src = Keypair.create_from_uri('//Alice')
        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            setup_foreign_asset(peaq_substrate, kp_src, ACA_LOCATION, ACA_METADATA)
            current_balance = asset_aca_get(peaq_substrate, kp_src)['free']

        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            transfer_xcm_token(aca_substrate, kp_src, token_num, ACA_TOKEN, PEAQ_PARACHAIN_ID)

        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)
        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            latest_balance = asset_aca_get(peaq_substrate, kp_src)['free']

        assert(int(str(latest_balance)) == int(str(current_balance)) + int(str(token_num)))

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def acala_to_peaq_to_acala_test():
    print('---- acala to peaq to acala !! ----')
    try:
        current_balance = 0
        latest_balance = 0
        token_num = 2 * 10 ** 12
        prepare_token_num = 2 * token_num
        kp_src = Keypair.create_from_uri('//Alice')
        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            setup_foreign_asset(peaq_substrate, kp_src, ACA_LOCATION, ACA_METADATA)
            current_balance = asset_aca_get(peaq_substrate, kp_src)['free']

        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            transfer_xcm_token(aca_substrate, kp_src, prepare_token_num, ACA_TOKEN, PEAQ_PARACHAIN_ID)

        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)

        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            current_balance = show_account(aca_substrate, kp_src.ss58_address, 'aca before')

        # Execute
        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            transfer_xcm_token(peaq_substrate, kp_src, token_num, ACA_FORIGN_ASSET, ACA_PARACHAIN_ID)

        # Check
        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)

        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            latest_balance = show_account(aca_substrate, kp_src.ss58_address, 'aca after')

        weight_percentage = float(int(str(latest_balance)) - int(str(current_balance))) / float(token_num)
        assert(weight_percentage > WEIGHT_LIMIT_RATE)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def peaq_to_acala_to_peaq_test():
    print('---- peaq to acala to peaq !! ----')
    try:
        current_balance = 0
        latest_balance = 0
        token_num = 2 * 10 ** 18
        prepare_token_num = 2 * token_num
        kp_src = Keypair.create_from_uri('//Bob')
        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            setup_foreign_asset(aca_substrate, kp_src, PEAQ_LOCATION, PEAQ_METADATA)
            current_balance = asset_peaq_get(aca_substrate, kp_src)['free']

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            transfer_xcm_token(peaq_substrate, kp_src, prepare_token_num, PEAQ_TOKEN, ACA_PARACHAIN_ID)

        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            current_balance = show_account(peaq_substrate, kp_src.ss58_address, 'peaq before')

        # Execute
        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            transfer_xcm_token(aca_substrate, kp_src, token_num, PEAQ_FORIGN_ASSET, PEAQ_PARACHAIN_ID)

        # Check
        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            latest_balance = show_account(peaq_substrate, kp_src.ss58_address, 'peaq after')

        weight_percentage = float(int(str(latest_balance)) - int(str(current_balance))) / float(token_num)
        assert(weight_percentage > WEIGHT_LIMIT_RATE)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def peaq_to_acala_test():
    print('---- peaq to acala !! ----')
    try:
        current_balance = 0
        token_num = 100000
        kp_src = Keypair.create_from_uri('//Bob')
        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            setup_foreign_asset(aca_substrate, kp_src, PEAQ_LOCATION, PEAQ_METADATA)
            current_balance = asset_peaq_get(aca_substrate, kp_src)['free']

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            transfer_xcm_token(peaq_substrate, kp_src, token_num, PEAQ_TOKEN, ACA_PARACHAIN_ID)

        latest_balance = 0
        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)
        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            latest_balance = asset_peaq_get(aca_substrate, kp_src)['free']

        assert(int(str(latest_balance)) == int(str(current_balance)) + int(str(token_num)))

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def transfer_dot_to_para(substrate, kp_src, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    xcm_transfer = substrate.compose_call(
        call_module='XcmPallet',
        call_function='reserve_transfer_assets',
        call_params={
            'dest': {
                'V1': {
                    'parents': 0,
                    'interior': {
                        'X1': {
                            'Parachain': PEAQ_PARACHAIN_ID
                        }
                    }
                }
            },
            'beneficiary': {
                'V1': {
                    'parents': 0,
                    'interior': {
                        'X1': {
                            'AccountId32': [
                                'Any',
                                f'0x{kp_src.public_key.hex()}'
                            ]
                        }
                    }
                }
            },
            'assets': {
                'V1': [[{
                    'id': {
                        'Concrete': {
                            'parents': 0,
                            'interior': 'Here'
                        }
                    },
                    'fun': {
                        'Fungible': token_num
                    }
                }]]
            },
            'fee_asset_item': 0
        })
    extrinsic = substrate.create_signed_extrinsic(
        call=xcm_transfer,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'relay: reserve_transfer_assets')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    return receipt


def transfer_dot_to_relay(substrate, kp_src, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    xcm_transfer = substrate.compose_call(
        call_module='XTokens',
        call_function='transfer',
        call_params={
            'currency_id': {'Token': 'DOT'},
            'amount': token_num,
            'dest': {
                'V1': {
                    'parents': 1,
                    'interior': {
                        'X1': {
                            'AccountId32': [
                                'Any',
                                f'0x{kp_src.public_key.hex()}'
                            ]
                        }
                    }
                }
            },
            'dest_weight': 20000000000
        })
    extrinsic = substrate.create_signed_extrinsic(
        call=xcm_transfer,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'peaq: xcm_transfer')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    return receipt


def dot_to_peaq_test():
    print('---- rococo to peaq !! ----')
    try:
        current_balance = 0
        latest_balance = 0
        token_num = 2 * 10 ** 13

        kp_src = Keypair.create_from_uri('//Alice')
        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            current_balance = asset_dot_get(peaq_substrate, kp_src)['free']

        with SubstrateInterface(url=ROCOCO_WS_URL) as rococo_substrate:
            transfer_dot_to_para(rococo_substrate, kp_src, token_num)

        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            latest_balance = asset_dot_get(peaq_substrate, kp_src)['free']

        weight_percentage = float(int(str(latest_balance)) - int(str(current_balance))) / float(token_num)
        assert(weight_percentage > WEIGHT_LIMIT_RATE)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def peaq_to_dot_test():
    print('---- peaq to dot!! ----')
    try:
        current_balance = 0
        latest_balance = 0
        token_num = 10 ** 13
        prepare_token_num = token_num * 2

        kp_src = Keypair.create_from_uri('//Alice')

        with SubstrateInterface(url=ROCOCO_WS_URL) as rococo_substrate:
            transfer_dot_to_para(rococo_substrate, kp_src, prepare_token_num)

        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)

        with SubstrateInterface(url=ROCOCO_WS_URL) as rococo_substrate:
            current_balance = show_account(rococo_substrate, kp_src.ss58_address, 'before')

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            transfer_dot_to_relay(peaq_substrate, kp_src, token_num)

        print(f'Wait for {WAIT_BLOCK_TIME} blocks')
        time.sleep(SLEEP_TIME)

        with SubstrateInterface(url=ROCOCO_WS_URL) as rococo_substrate:
            latest_balance = show_account(rococo_substrate, kp_src.ss58_address, 'before')

        weight_percentage = float(int(str(latest_balance)) - int(str(current_balance))) / float(token_num)
        assert(weight_percentage > WEIGHT_LIMIT_RATE)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    peaq_to_acala_test()
    peaq_to_acala_to_peaq_test()
    acala_to_peaq_test()
    acala_to_peaq_to_acala_test()
    dot_to_peaq_test()
    peaq_to_dot_test()
