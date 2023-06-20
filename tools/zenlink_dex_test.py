import sys
import traceback

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import RELAYCHAIN_WS_URL, PARACHAIN_WS_URL
from tools.utils import compose_call, execute_extrinsic_call, show_extrinsic

sys.path.append('./')


PEAQ_PARACHAIN_ID = 2000
BIFROST_PARACHAIN_ID = 3000


# Composes a XCM Reserve-Transfer-Asset call to transfer DOT-tokens
# from relaychain to parachain
def compose_xcm_rta_relay2para(si_relay, kp_beneficiary, amount):
    dest = { 'V3': {
            'parents': '0',
            'interior': { 'X1': { 'Parachain': f'{PEAQ_PARACHAIN_ID}' }}
        }}
    beneficiary = { 'V3': {
            'parents': '0',
            'interior': { 'X1': { 'AccountId32': (None, kp_beneficiary.public_key) }}
        }}
    assets = { 'V3': [[{
            'id': { 'Concrete': { 'parents': '0', 'interior': 'Here' }},
            'fun': { 'Fungible': f'{amount}' }
            }]]}
    params = {
            'dest': dest,
            'beneficiary': beneficiary,
            'assets': assets,
            'fee_asset_item': '0'
        }
    return compose_call(si_relay, 'XcmPallet', 'reserve_transfer_assets', params)


def relaychain2parachain_test(si_relay, si_para):
    kp_sender = Keypair.create_from_uri('//Alice')
    # substrate.query(
    #     "ParachainStaking", "BlocksAuthored", [addr], block_hash=block_hash)
    kp_beneficiary = Keypair.create_from_uri('//Dave')
    call = compose_xcm_rta_relay2para(si_relay, kp_beneficiary, 2000000000000)
    print(call)
    execute_extrinsic_call(si_relay, kp_sender, call)


# def parachain2parachain_test():
    # TODO


def zenlink_dex_test():
    print('---- Zenlink-DEX-Protocol Test!! ----')
    try:
        # with SubstrateInterface(url=WS_URL) as substrate:
        # kp_src = Keypair.create_from_uri('//Alice')
        si_relay = SubstrateInterface(url=RELAYCHAIN_WS_URL)
        si_para = SubstrateInterface(url=PARACHAIN_WS_URL)
        relaychain2parachain_test(si_relay, si_para)
        # parachain2parachain_test()

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, \
            try running 'start_local_substrate_node.sh' first")
        sys.exit()

    except AssertionError:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        filename, line, func, text = tb_info[1]
        print(f'🔥 Test/{func}, Failed')


if __name__ == '__main__':
    zenlink_dex_test()
