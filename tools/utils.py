from substrateinterface import Keypair
from substrateinterface.utils import hasher, ss58
from scalecodec.base import RuntimeConfiguration
from scalecodec.type_registry import load_type_registry_preset
from scalecodec.utils.ss58 import ss58_encode
TOKEN_NUM_BASE = pow(10, 3)
PARACHAIN_WS_URL = 'ws://127.0.0.1:9947'
PARACHAIN_ETH_URL = "http://127.0.0.1:9937"
PARACHAIN_WS_URL = 'wss://wsspc1.agung.peaq.network'
PARACHAIN_ETH_URL = "https://rpcpc1.agung.peaq.network"
# WS_URL = 'ws://127.0.0.1:9944'
# ETH_URL = "http://127.0.0.1:9933"
WS_URL = PARACHAIN_WS_URL
ETH_URL = PARACHAIN_ETH_URL
# WS_URL = 'ws://192.168.178.23:9944'
# ETH_URL = "http://192.168.178.23:9933"
# WS_URL = "wss://wss.test.peaq.network"
# ETH_URL = "https://erpc.test.peaq.network:443"

import pprint
pp = pprint.PrettyPrinter(indent=4)


SCALE_CODEC = {
    "Address": "MultiAddress",
    "LookupSource": "MultiAddress",
    "Account": {
        "nonce": "U256",
        "balance": "U256"
    },
    "Transaction": {
        "nonce": "U256",
        "action": "String",
        "gas_price": "u64",
        "gas_limit": "u64",
        "value": "U256",
        "input": "Vec<u8>",
        "signature": "Signature"
    },
    "Signature": {
        "v": "u64",
        "r": "H256",
        "s": "H256"
    }
}


def show_extrinsic(receipt, info_type):
    if receipt.is_success:
        print(f'✅ {info_type}, Success: {receipt.get_extrinsic_identifier()}')
    else:
        print(f'⚠️  {info_type}, Extrinsic Failed: {receipt.error_message} {receipt.get_extrinsic_identifier()}')


def calculate_multi_sig(kps, threshold):
    '''https://github.com/polkascan/py-scale-codec/blob/f063cfd47c836895886697e7d7112cbc4e7514b3/test/test_scale_types.py#L383'''

    addrs = [kp.ss58_address for kp in kps]
    RuntimeConfiguration().update_type_registry(load_type_registry_preset("default"))
    multi_account_id = RuntimeConfiguration().get_decoder_class("MultiAccountId")

    multi_sig_account = multi_account_id.create_from_account_list(addrs, threshold)
    print(multi_sig_account)
    return ss58_encode(multi_sig_account.value.replace('0x', ''), 42)


def fund(substrate, kp_dst, token_num):
    kp_sudo = Keypair.create_from_uri('//Alice')

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

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'fund')


def deposit_money_to_multsig_wallet(substrate, kp_consumer, kp_provider, token_num):
    print('----- Consumer deposit money to multisig wallet')
    threshold = 2
    signators = [kp_consumer, kp_provider]
    multi_sig_addr = calculate_multi_sig(signators, threshold)
    call = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': multi_sig_addr,
            'value': token_num * TOKEN_NUM_BASE
        })

    nonce = substrate.get_account_nonce(kp_consumer.ss58_address)
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_consumer,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'transfer')


def send_service_request(substrate, kp_consumer, kp_provider, token_num):
    print('----- Consumer sends the serviice requested to peaq-transaction')
    nonce = substrate.get_account_nonce(kp_consumer.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqTransaction',
        call_function='service_requested',
        call_params={
            'provider': kp_provider.ss58_address,
            'token_deposited': token_num * TOKEN_NUM_BASE
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_consumer,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'service_requested')


def send_spent_token_from_multisig_wallet(substrate, kp_consumer, kp_provider, token_num, threshold):
    print('----- Provider asks the spent token')
    payload = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_provider.ss58_address,
            'value': token_num * TOKEN_NUM_BASE
        })

    nonce = substrate.get_account_nonce(kp_provider.ss58_address)

    as_multi_call = substrate.compose_call(
        call_module='MultiSig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp_consumer.ss58_address],
            'maybe_timepoint': None,
            'call': str(payload.data),
            'store_call': True,
            'max_weight': 1000000000,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=as_multi_call,
        keypair=kp_provider,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'as_multi')
    info = receipt.get_extrinsic_identifier().split('-')
    return {
        'tx_hash': receipt.extrinsic_hash,
        'timepoint': {'height': int(info[0]), 'index': int(info[1])},
        'call_hash': f'0x{payload.call_hash.hex()}',
    }


# [TODO] Can be extract function
def send_refund_token_from_multisig_wallet(substrate, kp_consumer, kp_provider, token_num, threshold):
    print('----- Provider asks the refund token')
    payload = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_consumer.ss58_address,
            'value': token_num * TOKEN_NUM_BASE
        })

    nonce = substrate.get_account_nonce(kp_provider.ss58_address)

    as_multi_call = substrate.compose_call(
        call_module='MultiSig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp_consumer.ss58_address],
            'maybe_timepoint': None,
            'call': str(payload.data),
            'store_call': True,
            'max_weight': 1000000000,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=as_multi_call,
        keypair=kp_provider,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'as_multi')
    info = receipt.get_extrinsic_identifier().split('-')
    return {
        'tx_hash': receipt.extrinsic_hash,
        'timepoint': {'height': int(info[0]), 'index': int(info[1])},
        'call_hash': f'0x{payload.call_hash.hex()}'
    }


# [TODO] Can be extract function
def send_spent_token_service_delievered(
        substrate, kp_consumer, kp_provider, token_num, tx_hash, timepoint, call_hash):

    print('----- Provider send the spent service delivered')
    nonce = substrate.get_account_nonce(kp_provider.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqTransaction',
        call_function='service_delivered',
        call_params={
            'consumer': kp_provider.ss58_address,
            'token_num': token_num,
            'tx_hash': tx_hash,
            'time_point': timepoint,
            'call_hash': call_hash,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_provider,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'service_delivered')


# [TODO] Can be extract function
def send_refund_token_service_delievered(
        substrate, kp_consumer, kp_provider, token_num, tx_hash, timepoint, call_hash):

    print('----- Provider send the refund service delivered')
    nonce = substrate.get_account_nonce(kp_provider.ss58_address)
    call = substrate.compose_call(
        call_module='PeaqTransaction',
        call_function='service_delivered',
        call_params={
            'consumer': kp_consumer.ss58_address,
            'token_num': token_num,
            'tx_hash': tx_hash,
            'time_point': timepoint,
            'call_hash': call_hash,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_provider,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'service_delivered')


def _approve_token(substrate, kp_sign, other_signatories, threshold, info):
    nonce = substrate.get_account_nonce(kp_sign.ss58_address)

    as_multi_call = substrate.compose_call(
        call_module='MultiSig',
        call_function='approve_as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': other_signatories,
            'maybe_timepoint': info['timepoint'],
            'call_hash': info['call_hash'],
            'max_weight': 1000000000,
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=as_multi_call,
        keypair=kp_sign,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'approve_as_multi')


def approve_spent_token(substrate, kp_consumer, provider_addr, threshold, spent_info):
    print('--- User approve spent token')
    _approve_token(substrate, kp_consumer, [provider_addr], threshold, spent_info)


def approve_refund_token(substrate, kp_consumer, provider_addr, threshold, refund_info):
    print('--- User approve refund token')
    _approve_token(substrate, kp_consumer, [provider_addr], threshold, refund_info)


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
    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


def calculate_evm_account(addr):
    evm_addr = b'evm:' + bytes.fromhex(addr[2:].upper())
    hash_key = hasher.blake2_256(evm_addr)
    return ss58.ss58_encode(hash_key)


def calculate_evm_addr(addr):
    return '0x' + ss58.ss58_decode(addr)[:40]
