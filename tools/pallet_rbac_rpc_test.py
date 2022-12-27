import sys
sys.path.append('./')
import time
import binascii

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import TOKEN_NUM_BASE, show_extrinsic, calculate_multi_sig, WS_URL
from tools.utils import transfer
# from tools.pallet_assets_test import pallet_assets_test
import random


# Generic extrinsic call: pass module & function to be called with params and an id for show_extrinsic-method
# Example:
#   cl_mod = 'PeaqRbac'
#   cl_fcn = 'add_role'
#   cl_par = {'role_id': entity_id, 'name': name }
#   ext_id = 'rbac_add_role'
def do_extrinsics(substrate, kp_src, cl_mod, cl_fcn, cl_par, ext_id):
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    call = substrate.compose_call(
        call_module=cl_mod,
        call_function=cl_fcn,
        call_params=cl_par
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, ext_id)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


# Simplification for all RBAC-related calls
def do_rbac_extrinsics(substrate, kp_src, cl_fcn, cl_par, ext_id):
    do_extrinsics(substrate, kp_src, 'PeaqRbac', cl_fcn, cl_par, ext_id)


# Adds a new role to the RBAC-pallet via extrinsic call
def rbac_add_role(substrate, kp_src, entity_id, name):
    do_rbac_extrinsics(substrate, kp_src, 'add_role', 
        {
            'role_id': entity_id,
            'name': name,
        },
        'rbac_add_role'
    )


def rbac_rpc_fetch_role(substrate, kp_src, entity_id, name):
    data = substrate.rpc_request('peaqrbac_fetchRole', [kp_src.ss58_address, entity_id])
    assert(data['result']['id'] == entity_id)
    assert(data['result']['name'] == name)


# Single, simple test for RPC fetchRole
def test_rpc_fetch_role(substrate, kp_src):
    id = 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789'
    id_str = [int(id[i:i+2],16) for i in range(0,len(id),2)]
    name = 'abcd0123'
    rbac_add_role(substrate, kp_src, f'0x{id}', f'0x{name}')
    rbac_rpc_fetch_role(substrate, kp_src, id_str, f'0x{name}')


# Entry function to do all RBAC-RPC tests
def pallet_rbac_test():
    print('---- pallet_rbac_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            test_rpc_fetch_role(substrate, kp_src)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()