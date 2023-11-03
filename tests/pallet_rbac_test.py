import traceback
import sys

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, fund
from tools.payload import user_extrinsic_send
import unittest

KP_TEST = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
RANDOM_PREFIX = KP_TEST.public_key.hex()[2:26]

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
# Converts a HEX-string without 0x into ASCII-string
def rpc_id(entity_id):
    return [int(entity_id[i:i + 2], 16) for i in range(0, len(entity_id), 2)]


def show_success_msg(msg):
    print(f'✅ Test/{msg}, Success')


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
@user_extrinsic_send
def exec_stack_extrinsic_call(substrate, kp_src, stack):
    # Wrape payload into a utility batch cal
    return substrate.compose_call(
        call_module='Utility',
        call_function='batch_all',
        call_params={
            'calls': stack,
        })


##############################################################################
# Entry function to do all RBAC-RPC tests
# Check before:
# type_registry_preset_dict = load_type_registry_preset(type_registry_name)
# ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
class TestPalletRBAC(unittest.TestCase):

    ##############################################################################
    # Adds a new role to the RBAC-pallet via extrinsic call
    def rbac_add_role(self, entity_id, name):
        return comp_rbac_call(
            self.substrate,
            'add_role',
            {
                'role_id': entity_id,
                'name': name,
            })

    # Adds a group to the RBAC-pallet via extrinsic call
    def rbac_add_group(self, group_id, name):
        return comp_rbac_call(
            self.substrate,
            'add_group',
            {
                'group_id': group_id,
                'name': name,
            })

    # Adds a permission to the RBAC-pallet via extrinsic call
    def rbac_add_permission(self, permission_id, name):
        return comp_rbac_call(
            self.substrate,
            'add_permission',
            {
                'permission_id': permission_id,
                'name': name,
            })

    # Assigns a permission to a role...
    def rbac_permission2role(self, permission_id, role_id):
        return comp_rbac_call(
            self.substrate,
            'assign_permission_to_role',
            {
                'permission_id': permission_id,
                'role_id': role_id,
            })

    # Assigns a role to a group...
    def rbac_role2group(self, role_id, group_id):
        return comp_rbac_call(
            self.substrate,
            'assign_role_to_group',
            {
                'role_id': role_id,
                'group_id': group_id,
            })

    # Assigns a role to a user...
    def rbac_role2user(self, role_id, user_id):
        return comp_rbac_call(
            self.substrate,
            'assign_role_to_user',
            {
                'role_id': role_id,
                'user_id': user_id,
            })

    # Assigns a user to a group...
    def rbac_user2group(self, user_id, group_id):
        return comp_rbac_call(
            self.substrate,
            'assign_user_to_group',
            {
                'user_id': user_id,
                'group_id': group_id,
            })

    # Disable an existing group...
    def rbac_disable_group(self, group_id):
        return comp_rbac_call(
            self.substrate,
            'disable_group',
            {
                'group_id': group_id,
            })

    ##############################################################################
    # Does a generic test-setup on the parachain
    def rbac_rpc_setup(self, kp_src):
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
        stack.append(self.rbac_add_role(f'0x{ROLE_ID1}', ROLE_NM1))
        stack.append(self.rbac_add_role(f'0x{ROLE_ID2}', ROLE_NM2))
        stack.append(self.rbac_add_role(f'0x{ROLE_ID3}', ROLE_NM3))

        # Add some groups
        stack.append(self.rbac_add_group(f'0x{GROUP_ID1}', GROUP_NM1))
        stack.append(self.rbac_add_group(f'0x{GROUP_ID2}', GROUP_NM2))
        stack.append(self.rbac_add_group(f'0x{GROUP_ID3}', GROUP_NM3))
        stack.append(self.rbac_disable_group(f'0x{GROUP_ID3}'))

        # Add some permissions
        stack.append(self.rbac_add_permission(f'0x{PERM_ID1}', PERM_NM1))
        stack.append(self.rbac_add_permission(f'0x{PERM_ID2}', PERM_NM2))
        stack.append(self.rbac_add_permission(f'0x{PERM_ID3}', PERM_NM3))
        stack.append(self.rbac_add_permission(f'0x{PERM_ID4}', PERM_NM4))

        # Assign permissions to roles
        stack.append(self.rbac_permission2role(f'0x{PERM_ID1}', f'0x{ROLE_ID1}'))
        stack.append(self.rbac_permission2role(f'0x{PERM_ID2}', f'0x{ROLE_ID1}'))
        stack.append(self.rbac_permission2role(f'0x{PERM_ID3}', f'0x{ROLE_ID2}'))
        stack.append(self.rbac_permission2role(f'0x{PERM_ID4}', f'0x{ROLE_ID3}'))

        # Assign roles to groups
        stack.append(self.rbac_role2group(f'0x{ROLE_ID1}', f'0x{GROUP_ID1}'))
        stack.append(self.rbac_role2group(f'0x{ROLE_ID2}', f'0x{GROUP_ID1}'))
        stack.append(self.rbac_role2group(f'0x{ROLE_ID3}', f'0x{GROUP_ID2}'))

        # Assign users to groups
        stack.append(self.rbac_user2group(f'0x{USER_ID1}', f'0x{GROUP_ID1}'))
        stack.append(self.rbac_user2group(f'0x{USER_ID2}', f'0x{GROUP_ID2}'))

        # Assign roles to users
        stack.append(self.rbac_role2user(f'0x{ROLE_ID2}', f'0x{USER_ID3}'))
        stack.append(self.rbac_role2user(f'0x{ROLE_ID3}', f'0x{USER_ID3}'))

        # Execute extrinsic-call-stack
        receipt = exec_stack_extrinsic_call(self.substrate, kp_src, stack)
        self.assertTrue(receipt.is_success, f'Extrinsic-call-stack failed: {receipt.error_message}')

    def check_ok_wo_enable_and_return(self, data, cnt=1):
        self.assertIn('Ok', data['result'])
        if isinstance(data['result']['Ok'], list):
            self.assertEqual(
                len([e for e in data['result']['Ok'] if 'enabled' in e and e['enabled']]),
                cnt,
                f'Expected {cnt} enabled entities {data["result"]["Ok"]}')
        return data['result']['Ok']

    def check_all_ok_and_return_all(self, data, cnt=1):
        self.assertIn('Ok', data['result'])
        if isinstance(data['result']['Ok'], list):
            self.assertEqual(len(data['result']['Ok']), cnt, f'Expected {cnt} enabled entities {data["result"]["Ok"]}')
        return data['result']['Ok']

    def check_err_and_return(self, data):
        self.assertIn('Err', data['result'])
        return data['result']['Err']

    ##############################################################################
    def rbac_rpc_fetch_entity(self, kp_src, entity, entity_id, name):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            f'peaqrbac_fetch{entity}',
            [kp_src.ss58_address, entity_id, bl_hsh]
        )
        data = self.check_ok_wo_enable_and_return(data)
        self.assertEqual(data['id'], entity_id)
        # assert(binascii.unhexlify(data['name'][2:]) == bytes(name, 'utf-8'))
        self.assertEqual(bytes(data['name']), bytes(name, 'utf-8'))

    def rbac_rpc_fetch_entities(self, kp_src, entity, entity_ids, names):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            f'peaqrbac_fetch{entity}s',
            [kp_src.ss58_address, bl_hsh]
        )
        data = self.check_ok_wo_enable_and_return(data, len(entity_ids))
        for i in range(0, len(names)):
            data.index({
                'id': entity_ids[i],
                'name': [ord(x) for x in names[i]],
                'enabled': True
            })

    def rbac_rpc_fetch_group_roles(self, kp_src, group_id, role_ids):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchGroupRoles',
            [kp_src.ss58_address, group_id, bl_hsh])
        data = self.check_all_ok_and_return_all(data, len(role_ids))
        for i in range(0, len(role_ids)):
            data.index({
                'role': role_ids[i],
                'group': group_id
            })

    def rbac_rpc_fetch_group_permissions(
            self, kp_src, group_id, perm_ids, names):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchGroupPermissions',
            [kp_src.ss58_address, group_id, bl_hsh])
        data = self.check_ok_wo_enable_and_return(data, len(perm_ids))
        for i in range(0, len(perm_ids)):
            data.index({
                'id': perm_ids[i],
                'name': [ord(x) for x in names[i]],
                'enabled': True
            })

    def rbac_rpc_fetch_role_permissions(self, kp_src, role_id, perm_ids):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchRolePermissions',
            [kp_src.ss58_address, role_id, bl_hsh])
        data = self.check_all_ok_and_return_all(data, len(perm_ids))
        for i in range(0, len(perm_ids)):
            data.index({
                'permission': perm_ids[i],
                'role': role_id
            })

    def rbac_rpc_fetch_user_roles(self, kp_src, user_id, role_ids):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchUserRoles',
            [kp_src.ss58_address, user_id, bl_hsh])
        data = self.check_all_ok_and_return_all(data, len(role_ids))
        for i in range(0, len(role_ids)):
            data.index({
                'role': role_ids[i],
                'user': user_id
            })

    def rbac_rpc_fetch_user_groups(self, kp_src, user_id, group_ids):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchUserGroups',
            [kp_src.ss58_address, user_id, bl_hsh])
        data = self.check_all_ok_and_return_all(data, len(group_ids))
        for i in range(0, len(group_ids)):
            data.index({
                'group': group_ids[i],
                'user': user_id
            })

    def rbac_rpc_fetch_user_permissions(
            self, kp_src, user_id, perm_ids, names):
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchUserPermissions',
            [kp_src.ss58_address, user_id, bl_hsh])
        data = self.check_ok_wo_enable_and_return(data, len(perm_ids))
        for i in range(0, len(perm_ids)):
            data.index({
                'id': perm_ids[i],
                'name': [ord(x) for x in names[i]],
                'enabled': True
            })

    ##############################################################################
    # Single, simple test for RPC fetchRole
    def verify_rpc_fetch_role(self, kp_src):
        self.rbac_rpc_fetch_entity(
            kp_src, 'Role', rpc_id(ROLE_ID1), ROLE_NM1)
        self.rbac_rpc_fetch_entity(
            kp_src, 'Role', rpc_id(ROLE_ID3), ROLE_NM3)
        show_success_msg('rpc_fetch_role')

    # Single, simple test for RPC fetchRoles
    def verify_rpc_fetch_roles(self, kp_src):
        self.rbac_rpc_fetch_entities(
            kp_src, 'Role',
            [rpc_id(ROLE_ID1), rpc_id(ROLE_ID2), rpc_id(ROLE_ID3)],
            [ROLE_NM1, ROLE_NM2, ROLE_NM3]
        )
        show_success_msg('rpc_fetch_roles')

    # Single, simple test for RPC fetchPermission
    def verify_rpc_fetch_permission(self, kp_src):
        self.rbac_rpc_fetch_entity(
            kp_src, 'Permission', rpc_id(PERM_ID2), PERM_NM2)
        self.rbac_rpc_fetch_entity(
            kp_src, 'Permission', rpc_id(PERM_ID4), PERM_NM4)
        show_success_msg('rpc_fetch_permission')

    # Single, simple test for RPC fetchRoles
    def verify_rpc_fetch_permissions(self, kp_src):
        self.rbac_rpc_fetch_entities(
            kp_src, 'Permission',
            [rpc_id(PERM_ID1), rpc_id(PERM_ID2),
                rpc_id(PERM_ID3), rpc_id(PERM_ID4)],
            [PERM_NM1, PERM_NM2, PERM_NM3, PERM_NM4]
        )
        show_success_msg('verify_rpc_fetch_permissions')

    # Single, simple test for RPC fetchGroup
    def verify_rpc_fetch_group(self, kp_src):
        self.rbac_rpc_fetch_entity(
            kp_src, 'Group', rpc_id(GROUP_ID2), GROUP_NM2)
        show_success_msg('rpc_fetch_group')

    # Single, simple test for RPC fetchRoles
    def verify_rpc_fetch_groups(self, kp_src):
        self.rbac_rpc_fetch_entities(
            kp_src, 'Group',
            [rpc_id(GROUP_ID1), rpc_id(GROUP_ID2)],
            [GROUP_NM1, GROUP_NM2])
        show_success_msg('verify_rpc_fetch_groups')

    # Single test for RPC fetchGroupRoles
    def verify_rpc_fetch_group_roles(self, kp_src):
        self.rbac_rpc_fetch_group_roles(
            kp_src,
            rpc_id(GROUP_ID1),
            [rpc_id(ROLE_ID1), rpc_id(ROLE_ID2)])
        self.rbac_rpc_fetch_group_roles(
            kp_src,
            rpc_id(GROUP_ID2),
            [rpc_id(ROLE_ID3)])
        show_success_msg('verify_rpc_fetch_group_roles')

    # Single test for RPC fetchRolePermissions
    def verify_rpc_fetch_role_permissions(self, kp_src):
        self.rbac_rpc_fetch_role_permissions(
            kp_src,
            rpc_id(ROLE_ID1),
            [rpc_id(PERM_ID1), rpc_id(PERM_ID2)])
        self.rbac_rpc_fetch_role_permissions(
            kp_src,
            rpc_id(ROLE_ID2),
            [rpc_id(PERM_ID3)])
        self.rbac_rpc_fetch_role_permissions(
            kp_src,
            rpc_id(ROLE_ID3),
            [rpc_id(PERM_ID4)])
        show_success_msg('verify_rpc_fetch_role_permissions')

    # Single, simple test for RPC fetchGroupPermissions
    def verify_rpc_fetch_group_permissions(self, kp_src):
        self.rbac_rpc_fetch_group_permissions(
            kp_src,
            rpc_id(GROUP_ID1),
            [rpc_id(PERM_ID1), rpc_id(PERM_ID2), rpc_id(PERM_ID3)],
            [PERM_NM1, PERM_NM2, PERM_NM3])
        self.rbac_rpc_fetch_group_permissions(
            kp_src,
            rpc_id(GROUP_ID2),
            [rpc_id(PERM_ID4)],
            [PERM_NM4])
        show_success_msg('verify_rpc_fetch_group_permissions')

    # Single test for RPC fetchUserGroups
    def verify_rpc_fetch_user_roles(self, kp_src):
        self.rbac_rpc_fetch_user_roles(
            kp_src,
            rpc_id(USER_ID3),
            [rpc_id(ROLE_ID2), rpc_id(ROLE_ID3)])
        show_success_msg('verify_rpc_fetch_user_roles')

    # Single test for RPC fetchUserGroups
    def verify_rpc_fetch_user_groups(self, kp_src):
        self.rbac_rpc_fetch_user_groups(
            kp_src,
            rpc_id(USER_ID1),
            [rpc_id(GROUP_ID1)])
        self.rbac_rpc_fetch_user_groups(
            kp_src,
            rpc_id(USER_ID2),
            [rpc_id(GROUP_ID2)])
        show_success_msg('verify_rpc_fetch_user_groups')

    # Single test for RPC fetchUserPermissions
    def verify_rpc_fetch_user_permissions(self, kp_src):
        self.rbac_rpc_fetch_user_permissions(
            kp_src,
            rpc_id(USER_ID1),
            [rpc_id(PERM_ID1), rpc_id(PERM_ID2), rpc_id(PERM_ID3)],
            [PERM_NM1, PERM_NM2, PERM_NM3])
        show_success_msg('verify_rpc_fetch_user_permissions')

    # Simple test for RBAC-fail (request entity, which does not exist)
    def verify_rpc_fail_wrong_id(self, kp_src):
        user_id = rpc_id(USER_IDE)
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchUserGroups',
            [kp_src.ss58_address, user_id, bl_hsh])
        data = self.check_err_and_return(data)
        self.assertEqual(data['typ'], 'AssignmentDoesNotExist')
        self.assertEqual(data['param'], user_id)
        show_success_msg('verify_rpc_fail_wrong_id')

    # Simple test for RBAC-fail (request entity, which is disabled)
    def verify_rpc_fail_disabled_id(self, kp_src):
        group_id = rpc_id(GROUP_ID3)
        bl_hsh = self.substrate.get_block_hash(None)
        data = self.substrate.rpc_request(
            'peaqrbac_fetchGroup',
            [kp_src.ss58_address, group_id, bl_hsh])
        data = self.check_err_and_return(data)
        self.assertEqual(data['typ'], 'EntityDisabled')
        self.assertEqual(data['param'], group_id)
        show_success_msg('verify_rpc_fail_disabled_id')

    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)

    def test_pallet_rbac(self):
        print('---- pallet_rbac_test!! ----')
        try:
            # Success tests, default test setup
            kp_src = KP_TEST
            fund(self.substrate, KP_TEST, 1 * 10 ** 18)
            self.rbac_rpc_setup(kp_src)

            self.verify_rpc_fetch_role(kp_src)
            self.verify_rpc_fetch_roles(kp_src)
            self.verify_rpc_fetch_permission(kp_src)
            self.verify_rpc_fetch_permissions(kp_src)
            self.verify_rpc_fetch_group(kp_src)
            self.verify_rpc_fetch_groups(kp_src)

            self.verify_rpc_fetch_group_roles(kp_src)
            self.verify_rpc_fetch_group_permissions(kp_src)
            self.verify_rpc_fetch_role_permissions(kp_src)

            self.verify_rpc_fetch_user_roles(kp_src)
            self.verify_rpc_fetch_user_groups(kp_src)
            self.verify_rpc_fetch_user_permissions(kp_src)

            # Failure tests
            self.verify_rpc_fail_wrong_id(kp_src)
            self.verify_rpc_fail_disabled_id(kp_src)

        except AssertionError:
            _, _, tb = sys.exc_info()
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[1]
            print(f'🔥 Test/{func}, Failed')
            raise
