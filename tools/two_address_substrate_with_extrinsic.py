import sys
sys.path.append('./')
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import TOKEN_NUM_BASE, show_extrinsic, calculate_multi_sig, WS_URL
from tools.utils import transfer
# from tools.pallet_assets_test import pallet_assets_test
import random


def show_account(substrate, addr, out_str):
    result = substrate.query("System", "Account", [addr])
    print(f'{addr} {out_str}: {result["data"]["free"]}')
    return int(result['data']['free'].value)


def send_proposal(substrate, kp_src, kp_dst, threshold, payload):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    as_multi_call = substrate.compose_call(
        call_module='MultiSig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp_dst.ss58_address],
            'maybe_timepoint': None,
            'call': payload.value,
            'store_call': True,
            'max_weight': {'ref_time': 1000000000},
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=as_multi_call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'as_multi')
    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    info = receipt.get_extrinsic_identifier().split('-')
    return {'height': int(info[0]), 'index': int(info[1])}


def send_approval(substrate, kp_src, kps, threshold, payload, timepoint):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    as_multi_call = substrate.compose_call(
        call_module='MultiSig',
        call_function='approve_as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp.ss58_address for kp in kps],
            'maybe_timepoint': timepoint,
            'call_hash': f'0x{payload.call_hash.hex()}',
            'max_weight': {'ref_time': 1000000000},
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=as_multi_call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'approve_as_multi')
    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


def multisig_test(substrate, kp_src, kp_dst):
    threshold = 2
    signators = [kp_src, kp_dst]
    multi_sig_addr = calculate_multi_sig(signators, threshold)

    num = random.randint(1, 10000)
    # Deposit to wallet addr
    transfer(substrate, kp_src, multi_sig_addr, num)

    payload = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_src.ss58_address,
            'value': num * TOKEN_NUM_BASE
        })

    # Send proposal
    pre_multisig_token = show_account(substrate, multi_sig_addr, 'before transfer')

    timepoint = send_proposal(substrate, kp_src, kp_dst, threshold, payload)
    send_approval(substrate, kp_dst, [kp_src],
                  threshold, payload, timepoint)

    post_multisig_token = show_account(substrate, multi_sig_addr, 'after transfer')
    assert(post_multisig_token + num * TOKEN_NUM_BASE == pre_multisig_token)


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


def pallet_multisig_test():
    print('---- pallet_multisig_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        substrate = SubstrateInterface(url=WS_URL,)
    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()

    # Fund first

    kp_src = Keypair.create_from_uri('//Alice')
    kp_dst = Keypair.create_from_uri('//Bob//stash')
    # fund(substrate, kp_dst, 500000)

    multisig_test(substrate, kp_src, kp_dst)


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
            'max_weight': {'ref_time': 1000000000},
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

def storage_add_item(substrate, kp_src, item_type, item):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqStorage',
        call_function='add_item',
        call_params={
            'item_type': item_type,
            'item': item,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'add_item')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

def utf8_to_ascii(utf8str):
    return [int(utf8str[i:i+2],16) for i in range(0,len(utf8str),2)]

from ast import literal_eval
def storage_rpc_read(substrate, kp_src, item_type, item):
    data = substrate.rpc_request('peaqstorage_readAttribute', [kp_src.ss58_address, item_type])
    # TODO RPC returns an array containing the value, not key-value struct as it should.
    assert(data['result'][0] == literal_eval(item))

def pallet_storage_test():
    print('---- pallet_storage_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice') 
            item_type = utf8_to_ascii("aa")
            item = '0x02'

            storage_add_item(substrate, kp_src, item_type, item)
            storage_rpc_read(substrate, kp_src, item_type, item)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()

if __name__ == '__main__':
    # kp_src = Keypair.create_from_mnemonic('nature exchange gasp toy result bacon coin broccoli rule oyster believe lyrics')
    # print(kp_src.ss58_address)
    # kp_dst = Keypair.create_from_mnemonic('oak salt spring reason nephew awake track income tissue inner book any')
    # print(kp_dst.ss58_address)
    # print(calculate_multi_sig([kp_src, kp_dst], 2))

    # pallet_batchall_test()
    # pallet_multisig_test()
    # pallet_transaction_test()
    pallet_did_test()
    # pallet_assets_test()
