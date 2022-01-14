import sys
import time

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from utils import fund, TOKEN_NUM_BASE, show_extrinsic, calculate_multi_sig
from utils import deposit_money_to_multsig_wallet, send_service_request
from utils import send_spent_token_from_multisig_wallet
from utils import send_refund_token_from_multisig_wallet
from utils import send_spent_token_service_delievered
from utils import send_refund_token_service_delievered
from utils import approve_spent_token
from utils import approve_refund_token
from scalecodec.base import RuntimeConfiguration

import pprint
pp = pprint.PrettyPrinter(indent=4)


MNEMONIC = [
    'trouble kangaroo brave step craft valve have dash unique vehicle melt broccoli',
    # 0x434DB4884Fa631c89E57Ea04411D6FF73eF0E297
    'lunar hobby hungry vacant imitate silly amused soccer face census keep kiwi',
    # 0xC5BDf22635Df81f897C1BB2B24b758dEB21f522d,
    'mansion dynamic turkey army feel rescue choose achieve hurdle gentle phrase pair',
    # 0xe3D5bca5420d451885bA73035F4F06d10cd72eb5,
]


SCALE_CODEC = {
    "types": {
         "Keys": {
          "type": "struct",
          "type_mapping": [
             ["grandpa", "GenericAccountId"],
             ["babe", "GenericAccountId"],
             ["im_online", "AccountId"],
             ["authority_discovery", "AccountId"],
             ["parachains", "AccountId"]
          ]
        },
        "EthereumAddress": "H160",
        "Address": "EthereumAddress",
        "LookupSource": "GenericEthereumAccountId",
        "AccountId": "GenericEthereumAccountId",
        "ExtrinsicSignature": "EcdsaSignature",

        ### ???
        "ContractExecResult": "ContractExecResultTo260",
        "ValidatorPrefs": "ValidatorPrefsWithBlocked",
        "AccountInfo": "AccountInfoWithTripleRefCount",

        "EthAddress": "EthereumAddress",
        "AuthorId": "GenericAccountId",
    }
}

def show_account(substrate, addr, out_str):
    result = substrate.query("System", "Account", [addr])
    print(f'{out_str} {addr}')
    pp.pprint(result.value)
    print('')
    return result.value['data']['free']


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


def evm_test():
    try:

        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url="ws://127.0.0.1:9944",
                                type_registry=SCALE_CODEC
                               ) as conn:

            existential_deposit = conn.get_constant('Balances', 'ExistentialDeposit').value

            kp_src = Keypair.create_from_mnemonic(MNEMONIC[0], crypto_type=KeypairType.ECDSA)

            kp_dst = Keypair.create_from_mnemonic(MNEMONIC[1], crypto_type=KeypairType.ECDSA)
            substrate_balance = show_account(conn, kp_dst.ss58_address, '=== Dst before === ')

            eth_balance = int(conn.rpc_request("eth_getBalance", [kp_dst.ss58_address]).get('result'), 16)
            if substrate_balance != eth_balance + existential_deposit:
                raise IOError(f'sub({substrate_balance}) != eth({eth_balance}) + deposit({existential_deposit})')

            transfer(conn, kp_src, kp_dst.ss58_address, 5)

            kp_dst = Keypair.create_from_mnemonic(MNEMONIC[1], crypto_type=KeypairType.ECDSA)
            substrate_balance = show_account(conn, kp_dst.ss58_address, '=== Dst End === ')
            eth_balance = int(conn.rpc_request("eth_getBalance", [kp_dst.ss58_address]).get('result'), 16)
            if substrate_balance != eth_balance + existential_deposit:
                raise IOError(f'sub({substrate_balance}) != eth({eth_balance}) + deposit({existential_deposit})')


    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    evm_test()
