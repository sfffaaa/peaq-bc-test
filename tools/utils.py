import sys
sys.path.append('.')

from substrateinterface import Keypair
from substrateinterface.utils import hasher, ss58
from scalecodec.base import RuntimeConfiguration
from scalecodec.type_registry import load_type_registry_preset
from scalecodec.utils.ss58 import ss58_encode

# Monkey patch
from scalecodec.types import FixedLengthArray
from tools.monkey_patch_scale_info import process_encode as new_process_encode
from tools.payload import sudo_call_compose, sudo_extrinsic_send, user_extrinsic_send
FixedLengthArray.process_encode = new_process_encode

TOKEN_NUM_BASE = pow(10, 3)
TOKEN_NUM_BASE_DEV = pow(10, 18)
STANDALONE_WS_URL = 'ws://127.0.0.1:9944'
PARACHAIN_WS_URL = 'ws://127.0.0.1:9947'
PARACHAIN_ETH_URL = 'http://127.0.0.1:9936'
RELAYCHAIN_WS_URL = 'ws://127.0.0.1:9944'
# PARACHAIN_WS_URL = 'wss://wsspc1.agung.peaq.network'
# PARACHAIN_ETH_URL = 'https://rpcpc1.agung.peaq.network'
# WS_URL = 'ws://127.0.0.1:9944'
# ETH_URL = 'http://127.0.0.1:9933'
WS_URL = PARACHAIN_WS_URL
ETH_URL = PARACHAIN_ETH_URL
# WS_URL = 'ws://192.168.178.23:9944'
# ETH_URL = 'http://192.168.178.23:9933'
# WS_URL = 'wss://wss.test.peaq.network'
# ETH_URL = 'https://erpc.test.peaq.network:443'
ETH_CHAIN_IDS = {
    'peaq-dev': 9999,
    'agung-network': 9999,
    'krest-network': 424242,
    'peaq-network': 424242,
}
KP_GLOBAL_SUDO = Keypair.create_from_uri('//Alice')
KP_COLLATOR = Keypair.create_from_uri('//Ferdie')

import pprint
pp = pprint.PrettyPrinter(indent=4)


def show_extrinsic(receipt, info_type):
    if receipt.is_success:
        print(f'✅ {info_type}, Success: {receipt.get_extrinsic_identifier()}')
    else:
        print(f'⚠️  {info_type}, Extrinsic Failed: {receipt.error_message} {receipt.get_extrinsic_identifier()}')


def calculate_multi_sig(kps, threshold):
    '''https://github.com/polkascan/py-scale-codec/blob/f063cfd47c836895886697e7d7112cbc4e7514b3/test/test_scale_types.py#L383'''

    addrs = [kp.ss58_address for kp in kps]
    RuntimeConfiguration().update_type_registry(load_type_registry_preset('legacy'))
    multi_account_id = RuntimeConfiguration().get_decoder_class('MultiAccountId')

    multi_sig_account = multi_account_id.create_from_account_list(addrs, threshold)
    print(multi_sig_account)
    return ss58_encode(multi_sig_account.value.replace('0x', ''), 42)


@user_extrinsic_send
def deposit_money_to_multsig_wallet(substrate, kp_consumer, kp_provider, token_num):
    print('----- Consumer deposit money to multisig wallet')
    threshold = 2
    signators = [kp_consumer, kp_provider]
    multi_sig_addr = calculate_multi_sig(signators, threshold)
    return substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': multi_sig_addr,
            'value': token_num * TOKEN_NUM_BASE
        })


@user_extrinsic_send
def send_service_request(substrate, kp_consumer, kp_provider, token_num):
    print('----- Consumer sends the serviice requested to peaq-transaction')
    return substrate.compose_call(
        call_module='PeaqTransaction',
        call_function='service_requested',
        call_params={
            'provider': kp_provider.ss58_address,
            'token_deposited': token_num * TOKEN_NUM_BASE
        })


# TODO, Depreciated
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
            'max_weight': {'ref_time': 1000000000},
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


# TODO, Depreciated
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
            'max_weight': {'ref_time': 1000000000},
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


# TODO, Depreciated
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


# TODO, Depreciated
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


# TODO, Depreciated
@user_extrinsic_send
def _approve_token(substrate, kp_sign, other_signatories, threshold, info):
    return substrate.compose_call(
        call_module='MultiSig',
        call_function='approve_as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': other_signatories,
            'maybe_timepoint': info['timepoint'],
            'call_hash': info['call_hash'],
            'max_weight': {'ref_time': 1000000000},
        })


# TODO, Depreciated
def approve_spent_token(substrate, kp_consumer, provider_addr, threshold, spent_info):
    print('--- User approve spent token')
    _approve_token(substrate, kp_consumer, [provider_addr], threshold, spent_info)


# TODO, Depreciated
def approve_refund_token(substrate, kp_consumer, provider_addr, threshold, refund_info):
    print('--- User approve refund token')
    _approve_token(substrate, kp_consumer, [provider_addr], threshold, refund_info)


def transfer(substrate, kp_src, kp_dst_addr, token_num, token_base=0):
    return transfer_with_tip(substrate, kp_src, kp_dst_addr, token_num, 0, token_base)


def transfer_with_tip(substrate, kp_src, kp_dst_addr, token_num, tip, token_base=0):
    if not token_base:
        token_base = TOKEN_NUM_BASE

    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    call = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst_addr,
            'value': token_num * token_base
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        tip=tip * token_base,
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'transfer')
    return receipt


def _calculate_evm_account(addr):
    evm_addr = b'evm:' + bytes.fromhex(addr[2:].upper())
    hash_key = hasher.blake2_256(evm_addr)
    return hash_key


def calculate_evm_account(addr):
    return ss58.ss58_encode(calculate_evm_account_hex(addr))


def calculate_evm_account_hex(addr):
    return '0x' + _calculate_evm_account(addr).hex()


def calculate_evm_addr(addr):
    return '0x' + ss58.ss58_decode(addr)[:40]


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def fund(substrate, kp_dst, token_num):
    return substrate.compose_call(
        call_module='Balances',
        call_function='set_balance',
        call_params={
            'who': kp_dst.ss58_address,
            'new_free': token_num * TOKEN_NUM_BASE,
            'new_reserved': 0
        }
    )


def get_block_hash(substrate, block_num):
    return substrate.get_block_hash(block_id=block_num)


def get_account_balance(substrate, addr, block_hash=None):
    result = substrate.query(
        'System', 'Account', [addr], block_hash=block_hash)
    return int(result['data']['free'].value)


def get_account_balance_locked(substrate, addr):
    result = substrate.query('System', 'Account', [addr])
    return int(result['data']['misc_frozen'].value)


def check_and_fund_account(substrate, addr, min_bal, req_bal):
    if get_account_balance(substrate, addr.ss58_address) < min_bal:
        print('Since sufficinet balance is not available in account: ', addr.ss58_address)
        print('account will be fund with an amount equalt to :', req_bal)
        fund(substrate, addr, req_bal)
        print('account balance after funding: ', get_account_balance(substrate, addr.ss58_address))


def show_account(substrate, addr, out_str):
    result = get_account_balance(substrate, addr)
    print(f'{addr} {out_str}: {result}')
    return result


def get_eth_chain_id(substrate):
    chain_name = substrate.rpc_request(method='system_chain', params=[]).get('result')
    return ETH_CHAIN_IDS[chain_name]


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_max_currency_supply(substrate, max_currency_supply):
    return substrate.compose_call(
        call_module='BlockReward',
        call_function='set_max_currency_supply',
        call_params={
            'limit': max_currency_supply
        }
    )


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_block_reward_configuration(substrate, data):
    return substrate.compose_call(
        call_module='BlockReward',
        call_function='set_configuration',
        call_params={
            'reward_distro_params': {
                'treasury_percent': data['treasury_percent'],
                'dapps_percent': data['dapps_percent'],
                'collators_percent': data['collators_percent'],
                'lp_percent': data['lp_percent'],
                'machines_percent': data['machines_percent'],
                'machines_subsidization_percent': data['machines_subsidization_percent'],
            }
        }
    )


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def setup_block_reward(substrate, block_reward):
    return substrate.compose_call(
        call_module='BlockReward',
        call_function='set_block_issue_reward',
        call_params={
            'block_reward': block_reward
        }
    )


@user_extrinsic_send
def send_proposal(substrate, kp_src, kp_dst, threshold, payload, timepoint=None):
    return substrate.compose_call(
        call_module='MultiSig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp_dst.ss58_address],
            'maybe_timepoint': timepoint,
            'call': payload.value,
            'max_weight': {'ref_time': 1000000000, 'proof_size': 1000000},
        })


def get_as_multi_extrinsic_id(receipt):
    info = receipt.get_extrinsic_identifier().split('-')
    return {'height': int(info[0]), 'index': int(info[1])}


@user_extrinsic_send
def send_approval(substrate, kp_src, kps, threshold, payload, timepoint):
    return substrate.compose_call(
        call_module='MultiSig',
        call_function='approve_as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': [kp.ss58_address for kp in kps],
            'maybe_timepoint': timepoint,
            'call_hash': f'0x{payload.call_hash.hex()}',
            'max_weight': {'ref_time': 1000000000, 'proof_size': 1000000},
        })


def get_chain(substrate):
    return substrate.rpc_request(method='system_chain', params=[]).get('result')


def get_collators(substrate, key):
    return substrate.query(
           module='ParachainStaking',
           storage_function='CandidatePool',
           params=[key.ss58_address]
    )


def get_block_height(substrate):
    latest_block = substrate.get_block()
    return latest_block['header']['number']


def exist_pallet(substrate, pallet_name):
    return substrate.get_block_metadata(decode=True).get_metadata_pallet(pallet_name)


if __name__ == '__main__':
    data = '5F1e2nuSgxwWZiL9jTxv3jrMQHeHHhuwP7oDmU87SMp1Ncxv'
    print(calculate_evm_addr(data))
