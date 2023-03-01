import sys
import traceback

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL
import time

sys.path.append('./')

RANDOM_PREFIX = hex(int(time.time()))[2:] * 3

##############################################################################
# Constants for global test-setup defaults
ROLE_ID1 = '{0}03456789abcdef0123456789abcdef0123456789'.format(RANDOM_PREFIX)
ROLE_ID2 = '{0}04567890bcdefa1234567890bcdefa1234567890'.format(RANDOM_PREFIX)
ROLE_ID3 = '{0}05678901cdefab2345678901cdefab2345678901'.format(RANDOM_PREFIX)
ROLE_NM1 = '{0}RoleA'.format(RANDOM_PREFIX)
ROLE_NM2 = '{0}RoleB'.format(RANDOM_PREFIX)
ROLE_NM3 = '{0}RoleC'.format(RANDOM_PREFIX)

GROUP_ID1 = '{0}0defabcdabcdefabcdefabcdabcdefabcdefabcd'.format(RANDOM_PREFIX)
GROUP_ID2 = '{0}0efabcdebcdefabcdefabcdebcdefabcdefabcde'.format(RANDOM_PREFIX)
GROUP_ID3 = '{0}0fabcdefcdefabcdefabcdefcdefabcdefabcdef'.format(RANDOM_PREFIX)
GROUP_NM1 = '{0}GroupA'.format(RANDOM_PREFIX)
GROUP_NM2 = '{0}GroupB'.format(RANDOM_PREFIX)
GROUP_NM3 = '{0}DisabledGroup'.format(RANDOM_PREFIX)
# GROUP_MK is only a marker group for test-interal-logic, see set_test_mk1/2()
GROUP_MK1 = '{0}0abcdefadefabcdefabcdefadefabcdefabcdefa'.format(RANDOM_PREFIX)
GROUP_MK1N = '{0}MarkerGroup'.format(RANDOM_PREFIX)

PERM_ID1 = '{0}0901234501234567890123450123456789012345'.format(RANDOM_PREFIX)
PERM_ID2 = '{0}0012345612345678901234561234567890123456'.format(RANDOM_PREFIX)
PERM_ID3 = '{0}0123456723456789012345672345678901234567'.format(RANDOM_PREFIX)
PERM_ID4 = '{0}0234567834567890123456783456789012345678'.format(RANDOM_PREFIX)
PERM_NM1 = '{0}PermissionA'.format(RANDOM_PREFIX)
PERM_NM2 = '{0}PermissionB'.format(RANDOM_PREFIX)
PERM_NM3 = '{0}PermissionC'.format(RANDOM_PREFIX)
PERM_NM4 = '{0}PermissionD'.format(RANDOM_PREFIX)

USER_ID1 = '{0}05ef6789ab012cd345ef6789ab012cd345ef6789'.format(RANDOM_PREFIX)
USER_ID2 = '{0}05fa6789bc012de345fa6789bc012de345fa6789'.format(RANDOM_PREFIX)
USER_ID3 = '{0}05ab6789cd012ef345ab6789cd012ef345ab6789'.format(RANDOM_PREFIX)
# USER_IDE does not exist in chain -> error
USER_IDE = '{0}05bc6789de012fa345bc6789de012fa345bc6789'.format(RANDOM_PREFIX)


##############################################################################
# Composes a substrate-call on PeaqRbac-methods
# Example:
#   cl_fcn = 'add_role'
#   cl_par = {'role_id': entity_id, 'name': name }
def comp_rbac_call(substrate, cl_fcn, cl_par):
    return substrate.compose_call(
        call_module='PeaqRbac',
        call_function=cl_fcn,
        call_params=cl_par
    )


# Executes a stack-extrinsic-call on substrate
def exec_stack_extrinsic_call(substrate, kp_src, stack):
    # Wrape payload into a utility batch cal
    call = substrate.compose_call(
        call_module='Utility',
        call_function='batch_all',
        call_params={
            'calls': stack,
        })

    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    show_extrinsic(receipt, 'batch_transaction')

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError


##############################################################################
# Adds a new role to the RBAC-pallet via extrinsic call
def rbac_add_role(substrate, entity_id, name):
    return comp_rbac_call(
        substrate,
        'add_role',
        {
            'role_id': entity_id,
            'name': name,
        })


# Adds a group to the RBAC-pallet via extrinsic call
def rbac_add_group(substrate, group_id, name):
    return comp_rbac_call(
        substrate,
        'add_group',
        {
            'group_id': group_id,
            'name': name,
        })


# Adds a permission to the RBAC-pallet via extrinsic call
def rbac_add_permission(substrate, permission_id, name):
    return comp_rbac_call(
        substrate,
        'add_permission',
        {
            'permission_id': permission_id,
            'name': name,
        })


# Assigns a permission to a role...
def rbac_permission2role(substrate, permission_id, role_id):
    return comp_rbac_call(
        substrate,
        'assign_permission_to_role',
        {
            'permission_id': permission_id,
            'role_id': role_id,
        })


# Assigns a role to a group...
def rbac_role2group(substrate, role_id, group_id):
    return comp_rbac_call(
        substrate,
        'assign_role_to_group',
        {
            'role_id': role_id,
            'group_id': group_id,
        })


# Assigns a role to a user...
def rbac_role2user(substrate, role_id, user_id):
    return comp_rbac_call(
        substrate,
        'assign_role_to_user',
        {
            'role_id': role_id,
            'user_id': user_id,
        })


# Assigns a user to a group...
def rbac_user2group(substrate, user_id, group_id):
    return comp_rbac_call(
        substrate,
        'assign_user_to_group',
        {
            'user_id': user_id,
            'group_id': group_id,
        })


# Disable an existing group...
def rbac_disable_group(substrate, group_id):
    return comp_rbac_call(
        substrate,
        'disable_group',
        {
            'group_id': group_id,
        })


##############################################################################
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

    # Test-progress will marked as group and users within parachain
    stack = []
    # Add some roles
    stack.append(rbac_add_role(
        substrate, f'0x{ROLE_ID1}', ROLE_NM1))
    stack.append(rbac_add_role(
        substrate, f'0x{ROLE_ID2}', ROLE_NM2))
    stack.append(rbac_add_role(
        substrate, f'0x{ROLE_ID3}', ROLE_NM3))

    # Add some groups
    stack.append(rbac_add_group(
        substrate, f'0x{GROUP_ID1}', GROUP_NM1))
    stack.append(rbac_add_group(
        substrate, f'0x{GROUP_ID2}', GROUP_NM2))
    stack.append(rbac_add_group(
        substrate, f'0x{GROUP_ID3}', GROUP_NM3))
    stack.append(rbac_disable_group(
        substrate, f'0x{GROUP_ID3}'))

    # Add some permissions
    stack.append(rbac_add_permission(
        substrate, f'0x{PERM_ID1}', PERM_NM1))
    stack.append(rbac_add_permission(
        substrate, f'0x{PERM_ID2}', PERM_NM2))
    stack.append(rbac_add_permission(
        substrate, f'0x{PERM_ID3}', PERM_NM3))
    stack.append(rbac_add_permission(
        substrate, f'0x{PERM_ID4}', PERM_NM4))

    # Assign permissions to roles
    stack.append(rbac_permission2role(
        substrate, f'0x{PERM_ID1}', f'0x{ROLE_ID1}'))
    stack.append(rbac_permission2role(
        substrate, f'0x{PERM_ID2}', f'0x{ROLE_ID1}'))
    stack.append(rbac_permission2role(
        substrate, f'0x{PERM_ID3}', f'0x{ROLE_ID2}'))
    stack.append(rbac_permission2role(
        substrate, f'0x{PERM_ID4}', f'0x{ROLE_ID3}'))

    # Assign roles to groups
    stack.append(rbac_role2group(
        substrate, f'0x{ROLE_ID1}', f'0x{GROUP_ID1}'))
    stack.append(rbac_role2group(
        substrate, f'0x{ROLE_ID2}', f'0x{GROUP_ID1}'))
    stack.append(rbac_role2group(
        substrate, f'0x{ROLE_ID3}', f'0x{GROUP_ID2}'))

    # Assign users to groups
    stack.append(rbac_user2group(
        substrate, f'0x{USER_ID1}', f'0x{GROUP_ID1}'))
    stack.append(rbac_user2group(
        substrate, f'0x{USER_ID2}', f'0x{GROUP_ID2}'))

    # Assign roles to users
    stack.append(rbac_role2user(
        substrate, f'0x{ROLE_ID2}', f'0x{USER_ID3}'))
    stack.append(rbac_role2user(
        substrate, f'0x{ROLE_ID3}', f'0x{USER_ID3}'))

    # Execute extrinsic-call-stack
    exec_stack_extrinsic_call(substrate, kp_src, stack)


##############################################################################
# Converts a HEX-string without 0x into ASCII-string
def rpc_id(entity_id):
    return [int(entity_id[i:i + 2], 16) for i in range(0, len(entity_id), 2)]


def test_success_msg(msg):
    print(f'✅ Test/{msg}, Success')


def check_ok_and_return(data, cnt=1):
    assert 'Ok' in data['result']
    if type(data['result']['Ok']) == 'list':
        assert len(data['result']['Ok']) == cnt
    return data['result']['Ok']


def check_err_and_return(data):
    assert 'Err' in data['result']
    return data['result']['Err']


##############################################################################
def rbac_rpc_fetch_entity(substrate, kp_src, entity, entity_id, name):
    data = substrate.rpc_request(
        f'peaqrbac_fetch{entity}',
        [kp_src.ss58_address, entity_id]
    )
    data = check_ok_and_return(data)
    assert data['id'] == entity_id
    # assert(binascii.unhexlify(data['name'][2:]) == bytes(name, 'utf-8'))
    assert bytes(data['name']) == bytes(name, 'utf-8')


def rbac_rpc_fetch_entities(substrate, kp_src, entity, entity_ids, names):
    data = substrate.rpc_request(
        f'peaqrbac_fetch{entity}s',
        [kp_src.ss58_address]
    )
    data = check_ok_and_return(data, len(entity_ids))
    for i in range(0, len(names)):
        data.index({
            'id': entity_ids[i],
            'name': [ord(x) for x in names[i]],
            'enabled': True
        })


def rbac_rpc_fetch_group_roles(substrate, kp_src, group_id, role_ids):
    data = substrate.rpc_request(
        'peaqrbac_fetchGroupRoles',
        [kp_src.ss58_address, group_id])
    data = check_ok_and_return(data, len(role_ids))
    for i in range(0, len(role_ids)):
        data.index({
            'role': role_ids[i],
            'group': group_id
        })


def rbac_rpc_fetch_group_permissions(
        substrate, kp_src, group_id, perm_ids, names):
    data = substrate.rpc_request(
        'peaqrbac_fetchGroupPermissions',
        [kp_src.ss58_address, group_id])
    data = check_ok_and_return(data, len(perm_ids))
    for i in range(0, len(perm_ids)):
        data.index({
            'id': perm_ids[i],
            'name': [ord(x) for x in names[i]],
            'enabled': True
        })


def rbac_rpc_fetch_role_permissions(substrate, kp_src, role_id, perm_ids):
    data = substrate.rpc_request(
        'peaqrbac_fetchRolePermissions',
        [kp_src.ss58_address, role_id])
    data = check_ok_and_return(data, len(perm_ids))
    for i in range(0, len(perm_ids)):
        data.index({
            'permission': perm_ids[i],
            'role': role_id
        })


def rbac_rpc_fetch_user_roles(substrate, kp_src, user_id, role_ids):
    data = substrate.rpc_request(
        'peaqrbac_fetchUserRoles',
        [kp_src.ss58_address, user_id])
    data = check_ok_and_return(data, len(role_ids))
    for i in range(0, len(role_ids)):
        data.index({
            'role': role_ids[i],
            'user': user_id
        })


def rbac_rpc_fetch_user_groups(substrate, kp_src, user_id, group_ids):
    data = substrate.rpc_request(
        'peaqrbac_fetchUserGroups',
        [kp_src.ss58_address, user_id])
    data = check_ok_and_return(data, len(group_ids))
    for i in range(0, len(group_ids)):
        data.index({
            'group': group_ids[i],
            'user': user_id
        })


def rbac_rpc_fetch_user_permissions(
        substrate, kp_src, user_id, perm_ids, names):
    data = substrate.rpc_request(
        'peaqrbac_fetchUserPermissions',
        [kp_src.ss58_address, user_id])
    data = check_ok_and_return(data, len(perm_ids))
    for i in range(0, len(perm_ids)):
        data.index({
            'id': perm_ids[i],
            'name': [ord(x) for x in names[i]],
            'enabled': True
        })


##############################################################################
# Single, simple test for RPC fetchRole
def test_rpc_fetch_role(substrate, kp_src):
    rbac_rpc_fetch_entity(
        substrate, kp_src, 'Role', rpc_id(ROLE_ID1), ROLE_NM1)
    rbac_rpc_fetch_entity(
        substrate, kp_src, 'Role', rpc_id(ROLE_ID3), ROLE_NM3)
    test_success_msg('rpc_fetch_role')


# Single, simple test for RPC fetchRoles
def test_rpc_fetch_roles(substrate, kp_src):
    rbac_rpc_fetch_entities(
        substrate, kp_src, 'Role',
        [rpc_id(ROLE_ID1), rpc_id(ROLE_ID2), rpc_id(ROLE_ID3)],
        [ROLE_NM1, ROLE_NM2, ROLE_NM3]
    )
    test_success_msg('rpc_fetch_roles')


# Single, simple test for RPC fetchPermission
def test_rpc_fetch_permission(substrate, kp_src):
    rbac_rpc_fetch_entity(
        substrate, kp_src, 'Permission', rpc_id(PERM_ID2), PERM_NM2)
    rbac_rpc_fetch_entity(
        substrate, kp_src, 'Permission', rpc_id(PERM_ID4), PERM_NM4)
    test_success_msg('rpc_fetch_permission')


# Single, simple test for RPC fetchRoles
def test_rpc_fetch_permissions(substrate, kp_src):
    rbac_rpc_fetch_entities(
        substrate, kp_src, 'Permission',
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2),
            rpc_id(PERM_ID3), rpc_id(PERM_ID4)],
        [PERM_NM1, PERM_NM2, PERM_NM3, PERM_NM4]
    )
    test_success_msg('test_rpc_fetch_permissions')


# Single, simple test for RPC fetchGroup
def test_rpc_fetch_group(substrate, kp_src):
    rbac_rpc_fetch_entity(
        substrate, kp_src, 'Group', rpc_id(GROUP_ID2), GROUP_NM2)
    test_success_msg('rpc_fetch_group')


# Single, simple test for RPC fetchRoles
def test_rpc_fetch_groups(substrate, kp_src):
    rbac_rpc_fetch_entities(
        substrate, kp_src, 'Group',
        [rpc_id(GROUP_ID1), rpc_id(GROUP_ID2)],
        [GROUP_NM1, GROUP_NM2])
    test_success_msg('test_rpc_fetch_groups')


# Single test for RPC fetchGroupRoles
def test_rpc_fetch_group_roles(substrate, kp_src):
    rbac_rpc_fetch_group_roles(
        substrate, kp_src,
        rpc_id(GROUP_ID1),
        [rpc_id(ROLE_ID1), rpc_id(ROLE_ID2)])
    rbac_rpc_fetch_group_roles(
        substrate, kp_src,
        rpc_id(GROUP_ID2),
        [rpc_id(ROLE_ID3)])
    test_success_msg('test_rpc_fetch_group_roles')


# Single test for RPC fetchRolePermissions
def test_rpc_fetch_role_permissions(substrate, kp_src):
    rbac_rpc_fetch_role_permissions(
        substrate, kp_src,
        rpc_id(ROLE_ID1),
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2)])
    rbac_rpc_fetch_role_permissions(
        substrate, kp_src,
        rpc_id(ROLE_ID2),
        [rpc_id(PERM_ID3)])
    rbac_rpc_fetch_role_permissions(
        substrate, kp_src,
        rpc_id(ROLE_ID3),
        [rpc_id(PERM_ID4)])
    test_success_msg('test_rpc_fetch_role_permissions')


# Single, simple test for RPC fetchGroupPermissions
def test_rpc_fetch_group_permissions(substrate, kp_src):
    rbac_rpc_fetch_group_permissions(
        substrate, kp_src,
        rpc_id(GROUP_ID1),
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2), rpc_id(PERM_ID3)],
        [PERM_NM1, PERM_NM2, PERM_NM3])
    rbac_rpc_fetch_group_permissions(
        substrate, kp_src,
        rpc_id(GROUP_ID2),
        [rpc_id(PERM_ID4)],
        [PERM_NM4])
    test_success_msg('test_rpc_fetch_group_permissions')


# Single test for RPC fetchUserGroups
def test_rpc_fetch_user_roles(substrate, kp_src):
    rbac_rpc_fetch_user_roles(
        substrate, kp_src,
        rpc_id(USER_ID3),
        [rpc_id(ROLE_ID2), rpc_id(ROLE_ID3)])
    test_success_msg('test_rpc_fetch_user_roles')


# Single test for RPC fetchUserGroups
def test_rpc_fetch_user_groups(substrate, kp_src):
    rbac_rpc_fetch_user_groups(
        substrate, kp_src,
        rpc_id(USER_ID1),
        [rpc_id(GROUP_ID1)])
    rbac_rpc_fetch_user_groups(
        substrate, kp_src,
        rpc_id(USER_ID2),
        [rpc_id(GROUP_ID2)])
    test_success_msg('test_rpc_fetch_user_groups')


# Single test for RPC fetchUserPermissions
def test_rpc_fetch_user_permissions(substrate, kp_src):
    rbac_rpc_fetch_user_permissions(
        substrate, kp_src,
        rpc_id(USER_ID1),
        [rpc_id(PERM_ID1), rpc_id(PERM_ID2), rpc_id(PERM_ID3)],
        [PERM_NM1, PERM_NM2, PERM_NM3])
    test_success_msg('test_rpc_fetch_user_permissions')


# Simple test for RBAC-fail (request entity, which does not exist)
def test_rpc_fail_wrong_id(substrate, kp_src):
    user_id = rpc_id(USER_IDE)
    data = substrate.rpc_request(
        'peaqrbac_fetchUserGroups',
        [kp_src.ss58_address, user_id])
    data = check_err_and_return(data)
    assert data['typ'] == 'AssignmentDoesNotExist'
    assert data['param'] == user_id
    test_success_msg('test_rpc_fail_wrong_id')


# Simple test for RBAC-fail (request entity, which is disabled)
def test_rpc_fail_disabled_id(substrate, kp_src):
    group_id = rpc_id(GROUP_ID3)
    data = substrate.rpc_request(
        'peaqrbac_fetchGroup',
        [kp_src.ss58_address, group_id])
    data = check_err_and_return(data)
    assert data['typ'] == 'EntityDisabled'
    assert data['param'] == group_id
    test_success_msg('test_rpc_fail_disabled_id')


##############################################################################
# Entry function to do all RBAC-RPC tests
# Check before:
# type_registry_preset_dict = load_type_registry_preset(type_registry_name)
# ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
def pallet_rbac_test():
    print('---- pallet_rbac_test!! ----')
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            # Success tests, default test setup
            kp_src = Keypair.create_from_uri('//Alice')
            rbac_rpc_test_setup(substrate, kp_src)

            test_rpc_fetch_role(substrate, kp_src)
            test_rpc_fetch_roles(substrate, kp_src)
            test_rpc_fetch_permission(substrate, kp_src)
            test_rpc_fetch_permissions(substrate, kp_src)
            test_rpc_fetch_group(substrate, kp_src)
            test_rpc_fetch_groups(substrate, kp_src)

            test_rpc_fetch_group_roles(substrate, kp_src)
            test_rpc_fetch_group_permissions(substrate, kp_src)
            test_rpc_fetch_role_permissions(substrate, kp_src)

            test_rpc_fetch_user_roles(substrate, kp_src)
            test_rpc_fetch_user_groups(substrate, kp_src)
            test_rpc_fetch_user_permissions(substrate, kp_src)

            # Failure tests
            test_rpc_fail_wrong_id(substrate, kp_src)
            test_rpc_fail_disabled_id(substrate, kp_src)

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, \
            try running 'start_local_substrate_node.sh' first")
        sys.exit()

    except AssertionError:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        filename, line, func, text = tb_info[1]
        print(f'🔥 Test/{func}, Failed')
