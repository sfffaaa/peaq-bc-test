import sys
sys.path.append('./')
import time
import binascii
import traceback

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import TOKEN_NUM_BASE, show_extrinsic, calculate_multi_sig, WS_URL
from tools.utils import transfer
# from tools.pallet_assets_test import pallet_assets_test
import random


#########################################################################################################
# Constants for global test-setup defaults
ROLE_ID1 = 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789'
ROLE_ID2 = 'bcdefa1234567890bcdefa1234567890bcdefa1234567890bcdefa1234567890'
ROLE_ID3 = 'cdefab2345678901cdefab2345678901cdefab2345678901cdefab2345678901'
ROLE_NM1 = 'RoleA'
ROLE_NM2 = 'RoleB'
ROLE_NM3 = 'RoleC'

GROUP_ID1 = 'abcdefabcdefabcdabcdefabcdefabcdabcdefabcdefabcdabcdefabcdefabcd'
GROUP_ID2 = 'bcdefabcdefabcdebcdefabcdefabcdebcdefabcdefabcdebcdefabcdefabcde'
GROUP_NM1 = 'GroupA'
GROUP_NM2 = 'GroupB'

PERM_ID1 = '0123456789012345012345678901234501234567890123450123456789012345'
PERM_ID2 = '1234567890123456123456789012345612345678901234561234567890123456'
PERM_ID3 = '2345678901234567234567890123456723456789012345672345678901234567'
PERM_ID4 = '3456789012345678345678901234567834567890123456783456789012345678'
PERM_NM1 = 'PermissionA'
PERM_NM2 = 'PermissionB'
PERM_NM3 = 'PermissionC'
PERM_NM4 = 'PermissionD'

USER_ID1 = 'ab012cd345ef5678ab012cd345ef5678ab012cd345ef5678ab012cd345ef5678'
USER_ID2 = 'bc012de345fa5678ab012cd345ef5678ab012cd345ef5678ab012cd345ef5678'
USER_ID3 = 'cd012ef345ab5678cd012ef345ab5678cd012ef345ab5678cd012ef345ab5678'


#########################################################################################################
# Generic extrinsic call: pass module & function to be called with params and an id for show_extrinsic-method
# Example:
#   cl_mod = 'PeaqRbac'
#   cl_fcn = 'add_role'
#   cl_par = {'role_id': entity_id, 'name': name }
#   ext_id = 'rbac_add_role'
def do_extrinsics(substrate, kp_src, cl_mod, cl_fcn, cl_par):
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
    ext_id = f'{cl_mod}/{cl_fcn}({cl_par})'
    show_extrinsic(receipt, ext_id)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


# Simplification for all RBAC-related calls
def do_rbac_extrinsics(substrate, kp_src, cl_fcn, cl_par):
    do_extrinsics(substrate, kp_src, 'PeaqRbac', cl_fcn, cl_par)


#########################################################################################################
# Adds a new role to the RBAC-pallet via extrinsic call
def rbac_add_role(substrate, kp_src, entity_id, name):
    do_rbac_extrinsics(substrate, kp_src, 'add_role',
        {
            'role_id': entity_id,
            'name': name,
        }
    )

# Adds a group to the RBAC-pallet via extrinsic call
def rbac_add_group(substrate, kp_src, group_id, name):
    do_rbac_extrinsics(substrate, kp_src, 'add_group',
        {
            'group_id': group_id,
            'name': name,
        }
    )

# Adds a permission to the RBAC-pallet via extrinsic call
def rbac_add_permission(substrate, kp_src, permission_id, name):
    do_rbac_extrinsics(substrate, kp_src, 'add_permission',
        {
            'permission_id': permission_id,
            'name': name,
        }
    )

# Assigns a permission to a role...
def rbac_permission2role(substrate, kp_src, permission_id, role_id):
    do_rbac_extrinsics(substrate, kp_src, 'assign_permission_to_role',
        {
            'permission_id': permission_id,
            'role_id': role_id,
        }
    )

# Assigns a role to a group...
def rbac_role2group(substrate, kp_src, role_id, group_id):
    do_rbac_extrinsics(substrate, kp_src, 'assign_role_to_group',
        {
            'role_id': role_id,
            'group_id': group_id,
        }
    )

# Assigns a role to a user...
def rbac_role2user(substrate, kp_src, role_id, user_id):
    do_rbac_extrinsics(substrate, kp_src, 'assign_role_to_user',
        {
            'role_id': role_id,
            'user_id': user_id,
        }
    )

# Assigns a user to a group...
def rbac_user2group(substrate, kp_src, user_id, group_id):
    do_rbac_extrinsics(substrate, kp_src, 'assign_user_to_group',
        {
            'user_id': user_id,
            'group_id': group_id,
        }
    )


#########################################################################################################
# Does a generic test-setup on the parachain
def rbac_rpc_test_setup(substrate, kp_src):
    #   |u1|u2|u3|r1|r2|r3|g1|g2|
    # -------------------------
    # u1|  |  |  |xx|xx|  |  |xx|
    # u2|  |  |  |  |  |xx|xx|  |
    # u3|
    # r1|
    # r2|          ...
    # r3|
    # g1|
    # g2|

    # Add some roles
    rbac_add_role(substrate, kp_src, f'0x{ROLE_ID1}', ROLE_NM1)
    rbac_add_role(substrate, kp_src, f'0x{ROLE_ID2}', ROLE_NM2)
    rbac_add_role(substrate, kp_src, f'0x{ROLE_ID3}', ROLE_NM3)

    # Add some groups
    rbac_add_group(substrate, kp_src, f'0x{GROUP_ID1}', GROUP_NM1)
    rbac_add_group(substrate, kp_src, f'0x{GROUP_ID2}', GROUP_NM2)

    # Add some permissions
    rbac_add_permission(substrate, kp_src, f'0x{PERM_ID1}', PERM_NM1)
    rbac_add_permission(substrate, kp_src, f'0x{PERM_ID2}', PERM_NM2)
    rbac_add_permission(substrate, kp_src, f'0x{PERM_ID3}', PERM_NM3)
    rbac_add_permission(substrate, kp_src, f'0x{PERM_ID4}', PERM_NM4)

    # Assign permissions to roles
    rbac_permission2role(substrate, kp_src, f'0x{PERM_ID1}', f'0x{ROLE_ID1}')
    rbac_permission2role(substrate, kp_src, f'0x{PERM_ID2}', f'0x{ROLE_ID1}')
    rbac_permission2role(substrate, kp_src, f'0x{PERM_ID3}', f'0x{ROLE_ID2}')
    rbac_permission2role(substrate, kp_src, f'0x{PERM_ID4}', f'0x{ROLE_ID3}')

    # Assign roles to groups
    rbac_role2group(substrate, kp_src, f'0x{ROLE_ID1}', f'0x{GROUP_ID1}')
    rbac_role2group(substrate, kp_src, f'0x{ROLE_ID2}', f'0x{GROUP_ID1}')
    rbac_role2group(substrate, kp_src, f'0x{ROLE_ID3}', f'0x{GROUP_ID2}')

    # Assign users to groups
    rbac_user2group(substrate, kp_src, f'0x{USER_ID1}', f'0x{GROUP_ID1}')
    rbac_user2group(substrate, kp_src, f'0x{USER_ID2}', f'0x{GROUP_ID2}')

    # Assign roles to users
    rbac_role2user(substrate, kp_src, f'0x{ROLE_ID2}', f'0x{USER_ID3}')
    rbac_role2user(substrate, kp_src, f'0x{ROLE_ID3}', f'0x{USER_ID3}')


#########################################################################################################
# Converts a HEX-string without 0x into ASCII-string
def rpc_id(entity_id):
    return [int(entity_id[i:i+2],16) for i in range(0,len(entity_id),2)]

def test_success_msg(msg):
    print(f'✅ Test/{msg}, Success')

#########################################################################################################
def rbac_rpc_fetch_entity(substrate, kp_src, entity, entity_id, name):
    data = substrate.rpc_request(f'peaqrbac_fetch{entity}', [kp_src.ss58_address, entity_id])
    assert(data['result']['id'] == entity_id)
    assert(''.join([chr(x) for x in data['result']['name']]) == name)

def rbac_rpc_fetch_entities(substrate, kp_src, entity, entity_ids, names):
    data = substrate.rpc_request(f'peaqrbac_fetch{entity}s', [kp_src.ss58_address])
    assert(len(data['result']) == len(entity_ids))
    for i in range(0, len(names)):
        assert(data['result'][i]['id'] == entity_ids[i])
        assert(binascii.unhexlify(data['result'][i]['name'][2:]) == bytes(names[i], 'utf-8'))

def rbac_rpc_fetch_group_roles(substrate, kp_src, group_id, role_ids):
    data = substrate.rpc_request(f'peaqrbac_fetchGroupRoles', [kp_src.ss58_address, group_id])
    assert(len(data['result']) == len(role_ids))
    for i in range(0, len(role_ids)):
        assert(data['result'][i]['role'] == role_ids[i])
        assert(data['result'][i]['group'] == group_id)

def rbac_rpc_fetch_group_permissions(substrate, kp_src, group_id, perm_ids, names):
    data = substrate.rpc_request(f'peaqrbac_fetchGroupPermissions', [kp_src.ss58_address, group_id])
    assert(len(data['result']) == len(perm_ids))
    for i in range(0, len(perm_ids)):
        assert(data['result'][i]['id'] == perm_ids[i])
        assert(binascii.unhexlify(data['result'][i]['name'][2:]) == bytes(names[i], 'utf-8'))

def rbac_rpc_fetch_role_permissions(substrate, kp_src, role_id, perm_ids):
    data = substrate.rpc_request(f'peaqrbac_fetchRolePermissions', [kp_src.ss58_address, role_id])
    assert(len(data['result']) == len(perm_ids))
    for i in range(0, len(perm_ids)):
        assert(data['result'][i]['permission'] == perm_ids[i])
        assert(data['result'][i]['role'] == role_id)

def rbac_rpc_fetch_user_roles(substrate, kp_src, user_id, role_ids):
    data = substrate.rpc_request(f'peaqrbac_fetchUserRoles', [kp_src.ss58_address, user_id])
    assert(len(data['result']) == len(role_ids))
    for i in range(0, len(role_ids)):
        assert(data['result'][i]['role'] == role_ids[i])
        assert(data['result'][i]['user'] == user_id)

def rbac_rpc_fetch_user_groups(substrate, kp_src, user_id, group_ids):
    data = substrate.rpc_request(f'peaqrbac_fetchUserGroups', [kp_src.ss58_address, user_id])
    assert(len(data['result']) == len(group_ids))
    for i in range(0, len(group_ids)):
        assert(data['result'][i]['group'] == group_ids[i])
        assert(data['result'][i]['user'] == user_id)

def rbac_rpc_fetch_user_permissions(substrate, kp_src, user_id, perm_ids, names):
    data = substrate.rpc_request(f'peaqrbac_fetchUserPermissions', [kp_src.ss58_address, user_id])
    assert(len(data['result']) == len(perm_ids))
    for i in range(0, len(perm_ids)):
        assert(data['result'][i]['id'] == perm_ids[i])
        assert(binascii.unhexlify(data['result'][i]['name'][2:]) == bytes(names[i], 'utf-8'))


#########################################################################################################
# Single, simple test for RPC fetchRole
def test_rpc_fetch_role(substrate, kp_src):
    rbac_rpc_fetch_entity(substrate, kp_src, 'Role', rpc_id(ROLE_ID1), ROLE_NM1)
    rbac_rpc_fetch_entity(substrate, kp_src, 'Role', rpc_id(ROLE_ID3), ROLE_NM3)
    test_success_msg('rpc_fetch_role')

# Single, simple test for RPC fetchRoles
def test_rpc_fetch_roles(substrate, kp_src):
    rbac_rpc_fetch_entities(substrate, kp_src, 'Role',
        [rpc_id(ROLE_ID1), rpc_id(ROLE_ID2), rpc_id(ROLE_ID3)],
        [ROLE_NM1, ROLE_NM2, ROLE_NM3]
    )
    test_success_msg('rpc_fetch_roles')

# Single, simple test for RPC fetchPermission
def test_rpc_fetch_permission(substrate, kp_src):
    rbac_rpc_fetch_entity(substrate, kp_src, 'Permission', rpc_id(PERM_ID2), PERM_NM2)
    rbac_rpc_fetch_entity(substrate, kp_src, 'Permission', rpc_id(PERM_ID4), PERM_NM4)
    test_success_msg('rpc_fetch_permission')

# Single, simple test for RPC fetchRoles
def test_rpc_fetch_permissions(substrate, kp_src):
    rbac_rpc_fetch_entities(substrate, kp_src, 'Permission',
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2), rpc_id(PERM_ID3), rpc_id(PERM_ID4)],
        [PERM_NM1, PERM_NM2, PERM_NM3, PERM_NM4]
    )
    test_success_msg('test_rpc_fetch_permissions')

# Single, simple test for RPC fetchGroup
def test_rpc_fetch_group(substrate, kp_src):
    rbac_rpc_fetch_entity(substrate, kp_src, 'Group', rpc_id(GROUP_ID2), GROUP_NM2)
    test_success_msg('rpc_fetch_group')

# Single, simple test for RPC fetchRoles
def test_rpc_fetch_groups(substrate, kp_src):
    rbac_rpc_fetch_entities(substrate, kp_src, 'Group',
        [rpc_id(GROUP_ID1), rpc_id(GROUP_ID2)],
        [GROUP_NM1, GROUP_NM2]
    )
    test_success_msg('test_rpc_fetch_groups')

# Single test for RPC fetchGroupRoles
def test_rpc_fetch_group_roles(substrate, kp_src):
    rbac_rpc_fetch_group_roles(substrate, kp_src,
        rpc_id(GROUP_ID1),
        [rpc_id(ROLE_ID1), rpc_id(ROLE_ID2)]
    )
    rbac_rpc_fetch_group_roles(substrate, kp_src,
        rpc_id(GROUP_ID2),
        [rpc_id(ROLE_ID3)]
    )
    test_success_msg('test_rpc_fetch_group_roles')

# Single test for RPC fetchRolePermissions
def test_rpc_fetch_role_permissions(substrate, kp_src):
    rbac_rpc_fetch_role_permissions(substrate, kp_src,
        rpc_id(ROLE_ID1),
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2)]
    )
    rbac_rpc_fetch_role_permissions(substrate, kp_src,
        rpc_id(ROLE_ID2),
        [rpc_id(PERM_ID3)]
    )
    rbac_rpc_fetch_role_permissions(substrate, kp_src,
        rpc_id(ROLE_ID3),
        [rpc_id(PERM_ID4)]
    )
    test_success_msg('test_rpc_fetch_role_permissions')

# Single, simple test for RPC fetchGroupPermissions
def test_rpc_fetch_group_permissions(substrate, kp_src):
    rbac_rpc_fetch_group_permissions(substrate, kp_src,
        rpc_id(GROUP_ID1),
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2), rpc_id(PERM_ID3)],
        [PERM_NM1, PERM_NM2, PERM_NM3]
    )
    rbac_rpc_fetch_group_permissions(substrate, kp_src,
        rpc_id(GROUP_ID2),
        [rpc_id(PERM_ID4)],
        [PERM_NM4]
    )
    test_success_msg('test_rpc_fetch_group_permissions')

# Single test for RPC fetchUserGroups
def test_rpc_fetch_user_roles(substrate, kp_src):
    rbac_rpc_fetch_user_roles(substrate, kp_src,
        rpc_id(USER_ID3),
        [rpc_id(ROLE_ID2), rpc_id(ROLE_ID3)]
    )
    test_success_msg('test_rpc_fetch_user_roles')

# Single test for RPC fetchUserGroups
def test_rpc_fetch_user_groups(substrate, kp_src):
    rbac_rpc_fetch_user_groups(substrate, kp_src,
        rpc_id(USER_ID1),
        [rpc_id(GROUP_ID1)]
    )
    rbac_rpc_fetch_user_groups(substrate, kp_src,
        rpc_id(USER_ID2),
        [rpc_id(GROUP_ID2)]
    )
    test_success_msg('test_rpc_fetch_user_groups')

# Single test for RPC fetchUserPermissions
def test_rpc_fetch_user_permissions(substrate, kp_src):
    rbac_rpc_fetch_user_permissions(substrate, kp_src,
        rpc_id(USER_ID1),
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2), rpc_id(PERM_ID3)],
        [PERM_NM1, PERM_NM2, PERM_NM3]
    )
    test_success_msg('test_rpc_fetch_user_permissions')

# Simple test for API-fail
def test_rpc_api_fail(substrate):
    kp_src = Keypair.create_from_uri('//Bob')
    user_id = rpc_id(USER_ID1)
    data = substrate.rpc_request(f'peaqrbac_fetchUserGroups', [kp_src.ss58_address, user_id])
    print(data)


#########################################################################################################
# Entry function to do all RBAC-RPC tests
def pallet_rbac_rpc_test():
    print('---- pallet_rbac_rpc_test!! ----')
    try:
        # Check the type_registry_preset_dict = load_type_registry_preset(type_registry_name)
        # ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
        with SubstrateInterface(url=WS_URL) as substrate:
            kp_src = Keypair.create_from_uri('//Alice')
            rbac_rpc_test_setup(substrate, kp_src)

            test_rpc_fetch_role(substrate, kp_src)
            # test_rpc_fetch_roles(substrate, kp_src)
            # test_rpc_fetch_permission(substrate, kp_src)
            # test_rpc_fetch_permissions(substrate, kp_src)
            # test_rpc_fetch_group(substrate, kp_src)
            # test_rpc_fetch_groups(substrate, kp_src)

            # test_rpc_fetch_group_roles(substrate, kp_src)
            # test_rpc_fetch_group_permissions(substrate, kp_src)
            # test_rpc_fetch_role_permissions(substrate, kp_src)

            # test_rpc_fetch_user_roles(substrate, kp_src)
            # test_rpc_fetch_user_groups(substrate, kp_src)
            # test_rpc_fetch_user_permissions(substrate, kp_src)

            # test_rpc_api_fail(substrate)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()

    except AssertionError:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        filename, line, func, text = tb_info[1]
        print(f'🔥 Test/{func}, Failed')
