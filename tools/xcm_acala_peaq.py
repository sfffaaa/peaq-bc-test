import sys
sys.path.append('./')

import time
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL as PEAQ_WS_URL
from tools.two_address_substrate_with_extrinsic import show_account

ACA_WS_URL = 'ws://127.0.0.1:10047'
ROCOCO_WS_URL = 'ws://127.0.0.1:9944'


LOCATION = {
    'V1': {
        'parents': 1,
        'interior': {
            'X2': [{
                'Parachain': 3000
            }, {
                'GeneralKey': '0x0000'
            }]
        }
    }
}


METADATA = {
    'name': 'ACA',
    'symbol': 'ACA',
    'decimals': 15,
    'minimal_balance': 0
}


def setup_aca_asset(substrate, kp_src):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    payload = substrate.compose_call(
        call_module='AssetRegistry',
        call_function='register_foreign_asset',
        call_params={
            'location': LOCATION,
            'metadata': METADATA,
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


def asset_dot_get(substrate, kp_src):
    result = substrate.query("Tokens", "Accounts", [kp_src.ss58_address, {'Token': 'DOT'}])
    return result


def transfer_xcm_token(substrate, kp_src, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    xcm_transfer = substrate.compose_call(
        call_module='XTokens',
        call_function='transfer',
        call_params={
            'currency_id': {'Token': 'ACA'},
            'amount': token_num,
            'dest': {
                'V1': {
                    'parents': 1,
                    'interior': {
                        'X2': [{
                            'Parachain': 2000
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
        token_num = 100000
        kp_src = Keypair.create_from_uri('//Alice')
        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            setup_aca_asset(peaq_substrate, kp_src)
            current_balance = asset_aca_get(peaq_substrate, kp_src)['free']

        with SubstrateInterface(url=ACA_WS_URL) as aca_substrate:
            transfer_xcm_token(aca_substrate, kp_src, token_num)

        latest_balance = 0
        print('Wait for two blocks')
        time.sleep(24)
        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            # setup_aca_asset(peaq_substrate, kp_src)
            latest_balance = asset_aca_get(peaq_substrate, kp_src)['free']

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
                            'Parachain': 2000
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

        print('Wait for two blocks')
        time.sleep(24)

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            latest_balance = asset_dot_get(peaq_substrate, kp_src)['free']

        weight_percentage = float(int(str(latest_balance)) - int(str(current_balance))) / float(token_num)
        assert(weight_percentage > 0.99)

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

        print('Wait for two blocks')
        time.sleep(24)

        with SubstrateInterface(url=ROCOCO_WS_URL) as rococo_substrate:
            current_balance = show_account(rococo_substrate, kp_src.ss58_address, 'before')

        with SubstrateInterface(url=PEAQ_WS_URL) as peaq_substrate:
            transfer_dot_to_relay(peaq_substrate, kp_src, token_num)

        print('Wait for two blocks')
        time.sleep(24)

        with SubstrateInterface(url=ROCOCO_WS_URL) as rococo_substrate:
            latest_balance = show_account(rococo_substrate, kp_src.ss58_address, 'before')

        weight_percentage = float(int(str(latest_balance)) - int(str(current_balance))) / float(token_num)
        assert(weight_percentage > 0.99)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    acala_to_peaq_test()
    dot_to_peaq_test()
    peaq_to_dot_test()
