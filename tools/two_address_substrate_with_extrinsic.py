import sys
sys.path.append('./')
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import TOKEN_NUM_BASE, show_extrinsic, WS_URL
# from tools.pallet_assets_test import pallet_assets_test


def service_request(substrate, kp_src, kp_dst, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module='Transaction',
        call_function='service_requested',
        call_params={
            'provider': kp_dst.ss58_address,
            'token_deposited': token_num
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'service_requested')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    return receipt, call


def service_deliver(substrate, kp_src, kp_dst, receipt, call):
    # Do the request service
    info = receipt.get_extrinsic_identifier().split('-')
    timepoint = {'height': int(info[0]), 'index': int(info[1])}

    # Do the deleivery_server
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module='Transaction',
        call_function='service_delivered',
        call_params={
            'consumer': kp_dst.ss58_address,
            'refund_info': {
                'token_num': 10,
                'tx_hash': receipt.extrinsic_hash,
                'time_point': timepoint,
                'call_hash': f'0x{call.call_hash.hex()}',
            },
            'spent_info': {
                'token_num': 20,
                'tx_hash': receipt.extrinsic_hash,
                'time_point': timepoint,
                'call_hash': f'0x{call.call_hash.hex()}',
            }
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'service_delivered')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


def pallet_transaction_test():
    print('---- pallet_transaction_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            kp_dst = Keypair.create_from_uri('//Bob//stash')
            # fund(substrate, kp_src, 500)
            # transfer(substrate, kp_src, kp_dst.ss58_address, 50)
            receipt, call = service_request(substrate, kp_src, kp_dst, 50)
            service_deliver(substrate, kp_src, kp_dst, receipt, call)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def did_add(substrate, kp_src, name, value):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqDid',
        call_function='add_attribute',
        call_params={
            'did_account': kp_src.ss58_address,
            'name': name,
            'value': value,
            'valid_for': None,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'did_add')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


def did_rpc_read(substrate, kp_src, name, value):
    data = substrate.rpc_request('peaqdid_readAttribute', [kp_src.ss58_address, name])
    assert(data['result']['name'] == name)
    assert(data['result']['value'] == value)


def pallet_did_test():
    print('---- pallet_did_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            name = int(time.time())
            did_add(substrate, kp_src, f'0x{name}', '0x02')
            did_rpc_read(substrate, kp_src, f'0x{name}', '0x02')

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


def create_as_approve(substrate, kp_provider, kp_consumer, kp_target, token_num, threshold):
    print('----- Provider asks the spent token')
    payload_spent = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_target.ss58_address,
            'value': token_num * TOKEN_NUM_BASE
        })

    as_multi_call = substrate.compose_call(
        call_module='Multisig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp_consumer.ss58_address],
            'maybe_timepoint': None,
            'call': payload_spent.value,
            'store_call': True,
            'max_weight': {'ref_time': 1000000000, 'proof_size': 1000000},
        })
    return payload_spent, as_multi_call


if __name__ == '__main__':
    # kp_src = Keypair.create_from_mnemonic('nature exchange gasp toy result bacon coin broccoli rule oyster believe lyrics')
    # print(kp_src.ss58_address)
    # kp_dst = Keypair.create_from_mnemonic('oak salt spring reason nephew awake track income tissue inner book any')
    # print(kp_dst.ss58_address)
    # print(calculate_multi_sig([kp_src, kp_dst], 2))

    # pallet_transaction_test()
    pallet_did_test()
    # pallet_assets_test()
