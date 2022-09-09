import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import TOKEN_NUM_BASE, show_extrinsic, calculate_multi_sig, WS_URL
# from tools.pallet_assets_test import pallet_assets_test


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
            'max_weight': 1000000000,
        })
    return payload_spent, as_multi_call


def batch_as_approve(substrate, kp_provider, kp_consumer, token_num, threshold):
    print('----- Provider asks the spent token')
    payload_spent, call_spent = create_as_approve(substrate, kp_provider, kp_consumer, kp_consumer, token_num, threshold)
    payload_refund, call_refund = create_as_approve(substrate, kp_provider, kp_consumer, kp_provider, token_num, threshold)

    nonce = substrate.get_account_nonce(kp_provider.ss58_address)

    batch = substrate.compose_call(
        call_module='Utility',
        call_function='batch_all',
        call_params={
            'calls': [call_spent.value, call_refund.value],
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=batch,
        keypair=kp_provider,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'batch_all')

    info = receipt.get_extrinsic_identifier().split('-')
    return {
        'spent': {
            'tx_hash': receipt.extrinsic_hash,
            'timepoint': {'height': int(info[0]), 'index': int(info[1])},
            'call_hash': f'0x{payload_spent.call_hash.hex()}',
        }, 'refund': {
            'tx_hash': receipt.extrinsic_hash,
            'timepoint': {'height': int(info[0]), 'index': int(info[1])},
            'call_hash': f'0x{payload_refund.call_hash.hex()}',
        }
    }


def batch_all(substrate, kp_src, kp_dst, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    payload = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst.ss58_address,
            'value': token_num * TOKEN_NUM_BASE
        })

    batch = substrate.compose_call(
        call_module='Utility',
        call_function='batch_all',
        call_params={
            'calls': [payload.value, payload.value],
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=batch,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'batch_all')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    return receipt


def pallet_batchall_test():
    print('---- batch_all_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            kp_dst = Keypair.create_from_uri('//Bob//stash')
            print(calculate_multi_sig([kp_src, kp_dst], 2))
            # receipt = batch_all(substrate, kp_src, kp_dst, 50)
            receipt = batch_as_approve(substrate, kp_src, kp_dst, 51, 2)
            print(receipt)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    pallet_batchall_test()
