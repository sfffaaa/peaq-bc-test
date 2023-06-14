import sys

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from utils import show_extrinsic, WS_URL
# from scalecodec.base import RuntimeConfiguration
# from scalecodec.base import ScaleBytes

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

        # ## ???
        "ContractExecResult": "ContractExecResultTo260",
        "ValidatorPrefs": "ValidatorPrefsWithBlocked",
        "AccountInfo": "AccountInfoWithTripleRefCount",

        "EthAddress": "EthereumAddress",
        "AuthorId": "GenericAccountId",
    }
}


def upgrade(substrate, kp_src):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)

    with open('frontier_template_runtime.failure.wasm', 'rb') as f:
        data = f.read()

    call_internal = substrate.compose_call(
        call_module='System',
        call_function='set_code',
        call_params={
            'code': data
        })

    call = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo_unchecked_weight',
        call_params={
            'call': call_internal.value,
            'max_weight': {'ref_time': 1000000000}
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'upgrade?')


def upgrade_test():
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL,
                                type_registry=SCALE_CODEC) as conn:
            kp_src = Keypair.create_from_mnemonic(MNEMONIC[0], crypto_type=KeypairType.ECDSA)

            upgrade(conn, kp_src)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    upgrade_test()
