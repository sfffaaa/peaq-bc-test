import time
from tools.utils import show_extrinsic, WS_URL
from substrateinterface import SubstrateInterface, Keypair
import sys
sys.path.append('./')

# from tools.pallet_assets_test import pallet_assets_test


def utf8_to_ascii(utf8str):
    return [int(utf8str[i:i+2], 16) for i in range(0, len(utf8str), 2)]


def storage_rpc_read(substrate, kp_src, item_type, item):
    data = substrate.rpc_request('peaqstorage_readAttribute', [
                                 kp_src.ss58_address, item_type])
    assert (data["result"]["item"] == item)


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


def pallet_storage_test():
    print('---- pallet_storage_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            item_type = f'0x{int(time.time())}'
            item = '0x032132'

            storage_add_item(substrate, kp_src, item_type, item)
            storage_rpc_read(substrate, kp_src, item_type, item)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()
