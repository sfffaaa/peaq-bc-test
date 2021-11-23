# Python Substrate Interface Library
#
# Copyright 2018-2020 Stichting Polkascan (Polkascan Foundation).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from substrateinterface import SubstrateInterface, Keypair
from scalecodec.base import RuntimeConfiguration
from scalecodec.utils.ss58 import ss58_encode
from scalecodec.type_registry import load_type_registry_preset


TOKEN_NUM_BASE = pow(10, 19)


def calculate_multi_sig(kps, threshold):
    '''https://github.com/polkascan/py-scale-codec/blob/f063cfd47c836895886697e7d7112cbc4e7514b3/test/test_scale_types.py#L383'''

    addrs = [kp.ss58_address for kp in kps]
    RuntimeConfiguration().update_type_registry(load_type_registry_preset("default"))
    multi_account_id = RuntimeConfiguration().get_decoder_class("MultiAccountId")

    multi_sig_account = multi_account_id.create_from_account_list(addrs, threshold)
    return ss58_encode(multi_sig_account.value.replace('0x', ''), 2)


def show_account(substrate, addr, out_str):
    result = substrate.query("System", "Account", [addr])
    print(f'{addr} {out_str}')
    print(result)


def send_proposal(substrate, kp_src, kps, threshold, payload):
    multi_sig_addr = calculate_multi_sig(kps, threshold)
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    show_account(substrate, multi_sig_addr, 'before transfer')
    show_account(substrate, kp_src.ss58_address, 'before transfer')

    # length_obj = RuntimeConfiguration().get_decoder_class("Bytes")
    # call_data = str(length_obj.encode(str(payload.data)))
    # print(f'With length: {call_data}')
    #  print(f'W/o length: {payload.data}')
    #  raise IOError

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
    if receipt.is_success:
        print('✅ Success, triggered events: {receipt.get_extrinsic_identifier()}')
        for event in receipt.triggered_events:
            print(f'* {event.value}')

    else:
        print(f'⚠️ Extrinsic Failed: {receipt.error_message} {receipt.get_extrinsic_identifier()}')

    show_account(substrate, multi_sig_addr, 'after transfer')
    show_account(substrate, kp_src.ss58_address, 'after transfer')
    info = receipt.get_extrinsic_identifier().split('-')
    return {'height': int(info[0]), 'index': int(info[1])}


def send_approval(substrate, kp_src, kps, threshold, payload, timepoint):
    multi_sig_addr = calculate_multi_sig(kps, threshold)
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    show_account(substrate, multi_sig_addr, 'before transfer')
    show_account(substrate, kp_src.ss58_address, 'before transfer')

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
    print(receipt['extrinsic_hash'])
    if receipt.is_success:
        print('✅ Success, triggered events:')
        for event in receipt.triggered_events:
            print(f'* {event.value}')

    else:
        print(f'⚠️ Extrinsic Failed: {receipt.error_message} {receipt.get_extrinsic_identifier()}')

    show_account(substrate, multi_sig_addr, 'after transfer')
    show_account(substrate, kp_src.ss58_address, 'after transfer')


def fund(substrate, kp_dst, token_num):
    kp_sudo = Keypair.create_from_uri('//Alice')

    result = substrate.query("System", "Account", [kp_dst.ss58_address])
    print(f'{kp_dst.ss58_address} before fund ')
    print(result)

    payload = substrate.compose_call(
        call_module='Balances',
        call_function='set_balance',
        call_params={
            'who': kp_dst.ss58_address,
            'new_free': token_num * TOKEN_NUM_BASE,
            'new_reserved': 0
        }
    )

    call = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo',
        call_params={
            'call': payload.value,
        }
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo
    )

    substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    result = substrate.query("System", "Account", [kp_dst.ss58_address])
    print(f'{kp_dst.ss58_address} after fund ')
    print(result)


def transfer(substrate, kp_src, kp_dst_addr, token_num):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    result = substrate.query("System", "Account", [kp_dst_addr])
    print(f'{kp_dst_addr} before transfer ')
    print(result)

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

    substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    result = substrate.query("System", "Account", [kp_dst_addr])
    print(f'{kp_dst_addr} after transfer ')
    print(result)


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
    timepoint = send_proposal(substrate, kp_src, [kp_dst], threshold, payload)
    send_approval(substrate, kp_dst, [kp_src], threshold, payload, timepoint)


# import logging
# logging.basicConfig(level=logging.DEBUG)
def run():
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
    kp_dst = Keypair.create_from_uri('//Jay')
    fund(substrate, kp_src, 500)
    transfer(substrate, kp_src, kp_dst.ss58_address, 50)

    multisig_test(substrate, kp_src, kp_dst)


if __name__ == '__main__':
    run()
