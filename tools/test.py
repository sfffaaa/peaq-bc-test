import sys
import time

from substrateinterface import SubstrateInterface, Keypair
from utils import fund, TOKEN_NUM_BASE, show_extrinsic, calculate_multi_sig
from utils import deposit_money_to_multsig_wallet, send_service_request
from utils import send_spent_token_from_multisig_wallet
from utils import send_refund_token_from_multisig_wallet
from utils import send_spent_token_service_delievered
from utils import send_refund_token_service_delievered
from utils import approve_spent_token
from utils import approve_refund_token


def show_account(substrate, addr, out_str):
    result = substrate.query("System", "Account", [addr])
    print(f'{addr} {out_str}')
    print(result)


def send_proposal(substrate, kp_src, kps, threshold, payload):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    as_multi_call = substrate.compose_call(
        call_module='MultiSig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp.ss58_address for kp in kps],
            'maybe_timepoint': None,
            'call': str(payload.data),
            'store_call': True,
            'max_weight': 1000000000,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=as_multi_call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'as_multi')
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
            'max_weight': 1000000000,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=as_multi_call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'approve_as_multi')


def transfer(substrate, kp_src, kp_dst_addr, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    call = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst_addr,
            'value': token_num * TOKEN_NUM_BASE
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'transfer')


def multisig_test(substrate, kp_src, kp_dst):
    threshold = 2
    signators = [kp_src, kp_dst]
    multi_sig_addr = calculate_multi_sig(signators, threshold)

    # Deposit to wallet addr
    transfer(substrate, kp_src, multi_sig_addr, 50)

    payload = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_src.ss58_address,
            'value': 10 * TOKEN_NUM_BASE
        })

    # Send proposal
    show_account(substrate, multi_sig_addr, 'before transfer')
    show_account(substrate, kp_src.ss58_address, 'before transfer')

    print(f'show me the call_hash {payload.call_hash}')
    print(f'show me the call_hash 0x{payload.call_hash.hex()}')
    raise IOError
    timepoint = send_proposal(substrate, kp_src, [kp_dst],
                              threshold, payload)

    send_approval(substrate, kp_dst, [kp_src],
                  threshold, payload, timepoint)

    show_account(substrate, multi_sig_addr, 'after transfer')
    show_account(substrate, kp_src.ss58_address, 'after transfer')


def charging_station_test():
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        substrate = SubstrateInterface(
            url="ws://127.0.0.1:9944",
        )
    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()

    kp_consumer = Keypair.create_from_uri('//Bob')
    kp_provider = Keypair.create_from_uri('//Bob//stash')
    # Fund first
    fund(substrate, kp_consumer, 500)

    token_deposit = 10
    deposit_money_to_multsig_wallet(substrate, kp_consumer, kp_provider, token_deposit)
    send_service_request(substrate, kp_consumer, kp_provider, token_deposit)
    print('---- charging start')
    time.sleep(1)
    # charging start
    threshold = 2
    token_spent = 7
    raise IOError()
    token_refund = token_deposit - token_spent

    print('---- charging end')
    spent_info = send_spent_token_from_multisig_wallet(
        substrate, kp_consumer, kp_provider, token_spent, threshold)
    refund_info = send_refund_token_from_multisig_wallet(
        substrate, kp_consumer, kp_provider, token_refund, threshold)

    send_spent_token_service_delievered(
        substrate, kp_consumer, kp_provider, token_spent,
        spent_info['tx_hash'], spent_info['timepoint'], spent_info['call_hash'])
    send_refund_token_service_delievered(
        substrate, kp_consumer, kp_provider, token_refund,
        refund_info['tx_hash'], refund_info['timepoint'], refund_info['call_hash'])

    print('---- user approve')
    approve_spent_token(
        substrate, kp_consumer, kp_provider.ss58_address, threshold, spent_info)
    approve_refund_token(
        substrate, kp_consumer, kp_provider.ss58_address, threshold, refund_info)


def pallet_transaction_test():
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        substrate = SubstrateInterface(
            url="ws://127.0.0.1:9944",
        )
    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()

    kp_src = Keypair.create_from_uri('//Bob')
    kp_dst = Keypair.create_from_uri('//Bob//stash')
    # fund(substrate, kp_src, 500)
    # transfer(substrate, kp_src, kp_dst.ss58_address, 50)

    # Do the request service
    token_num = 50
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqTransaction',
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
    info = receipt.get_extrinsic_identifier().split('-')
    timepoint = {'height': int(info[0]), 'index': int(info[1])}

    # Do the deleivery_server
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqTransaction',
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


def pallet_multisig_test():
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        substrate = SubstrateInterface(
            url="ws://127.0.0.1:9944",
        )
    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()

    # Fund first

    kp_src = Keypair.create_from_uri('//Bob')
    kp_dst = Keypair.create_from_uri('//Bob//stash')
    fund(substrate, kp_src, 500)
    transfer(substrate, kp_src, kp_dst.ss58_address, 50)

    multisig_test(substrate, kp_src, kp_dst)


if __name__ == '__main__':
    # pallet_multisig_test()
    pallet_transaction_test()
    # charging_station_test()
