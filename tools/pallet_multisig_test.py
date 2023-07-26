import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import TOKEN_NUM_BASE, calculate_multi_sig, show_extrinsic, WS_URL
from tools.utils import transfer, show_account
import random


def send_proposal(substrate, kp_src, kp_dst, threshold, payload, timepoint=None):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    as_multi_call = substrate.compose_call(
        call_module='MultiSig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp_dst.ss58_address],
            'maybe_timepoint': timepoint,
            'call': payload.value,
            'max_weight': {'ref_time': 1000000000, 'proof_size': 1000000},
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
            'max_weight': {'ref_time': 1000000000, 'proof_size': 1000000},
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
    send_proposal(substrate, kp_src, kp_dst, threshold, payload, timepoint)

    post_multisig_token = show_account(substrate, multi_sig_addr, 'after transfer')
    print(f'pre_multisig_token: {pre_multisig_token}, post_multisig_token: {post_multisig_token}')
    print(f'num: {num}, num * TOKEN_NUM_BASE: {num * TOKEN_NUM_BASE}')
    assert(post_multisig_token + num * TOKEN_NUM_BASE == pre_multisig_token)


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


if __name__ == '__main__':
    pallet_multisig_test()
