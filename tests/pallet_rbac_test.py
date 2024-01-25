import traceback
import sys

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL
from peaq.sudo_extrinsic import fund
from peaq.utils import ExtrinsicBatch
from peaq.rbac import rbac_add_role_payload, rbac_add_group_payload, rbac_add_permission_payload
from peaq.rbac import rbac_permission2role_payload, rbac_role2group_payload
from peaq.rbac import rbac_disable_group_payload, rbac_user2group_payload
from peaq.rbac import rbac_role2user_payload
from peaq.rbac import rbac_rpc_fetch_role, rbac_rpc_fetch_permission, rbac_rpc_fetch_group
from peaq.rbac import rbac_rpc_fetch_group_roles, rbac_rpc_fetch_group_permissions
from peaq.rbac import rbac_rpc_fetch_user_roles, rbac_rpc_fetch_user_groups
from peaq.rbac import rbac_rpc_fetch_role_permissions, rbac_rpc_fetch_user_permissions
from peaq.rbac import rbac_rpc_fetch_roles
from peaq.rbac import rbac_rpc_fetch_permissions
from peaq.rbac import rbac_rpc_fetch_groups
from tools.utils import KP_GLOBAL_SUDO
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
def show_success_msg(msg):
    print(f'✅ Test/{msg}, Success')


##############################################################################
# Entry function to do all RBAC-RPC tests
# Check before:
# type_registry_preset_dict = load_type_registry_preset(type_registry_name)
# ~/venv.substrate/lib/python3.6/site-packages/substrateinterface/base.py
class TestPalletRBAC(unittest.TestCase):

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

        batch = ExtrinsicBatch(self.substrate, kp_src)
        # Add some roles
        rbac_add_role_payload(batch, f'0x{ROLE_ID1}', ROLE_NM1)
        rbac_add_role_payload(batch, f'0x{ROLE_ID2}', ROLE_NM2)
        rbac_add_role_payload(batch, f'0x{ROLE_ID3}', ROLE_NM3)

        # Add some groups
        rbac_add_group_payload(batch, f'0x{GROUP_ID1}', GROUP_NM1)
        rbac_add_group_payload(batch, f'0x{GROUP_ID2}', GROUP_NM2)
        rbac_add_group_payload(batch, f'0x{GROUP_ID3}', GROUP_NM3)
        rbac_disable_group_payload(batch, f'0x{GROUP_ID3}')

        # Add some permissions
        rbac_add_permission_payload(batch, f'0x{PERM_ID1}', PERM_NM1)
        rbac_add_permission_payload(batch, f'0x{PERM_ID2}', PERM_NM2)
        rbac_add_permission_payload(batch, f'0x{PERM_ID3}', PERM_NM3)
        rbac_add_permission_payload(batch, f'0x{PERM_ID4}', PERM_NM4)

        # Assign permissions to roles
        rbac_permission2role_payload(batch, f'0x{PERM_ID1}', f'0x{ROLE_ID1}')
        rbac_permission2role_payload(batch, f'0x{PERM_ID2}', f'0x{ROLE_ID1}')
        rbac_permission2role_payload(batch, f'0x{PERM_ID3}', f'0x{ROLE_ID2}')
        rbac_permission2role_payload(batch, f'0x{PERM_ID4}', f'0x{ROLE_ID3}')

        # Assign roles to groups
        rbac_role2group_payload(batch, f'0x{ROLE_ID1}', f'0x{GROUP_ID1}')
        rbac_role2group_payload(batch, f'0x{ROLE_ID2}', f'0x{GROUP_ID1}')
        rbac_role2group_payload(batch, f'0x{ROLE_ID3}', f'0x{GROUP_ID2}')

        # Assign users to groups
        rbac_user2group_payload(batch, f'0x{USER_ID1}', f'0x{GROUP_ID1}')
        rbac_user2group_payload(batch, f'0x{USER_ID2}', f'0x{GROUP_ID2}')

        # Assign roles to users
        rbac_role2user_payload(batch, f'0x{ROLE_ID2}', f'0x{USER_ID3}')
        rbac_role2user_payload(batch, f'0x{ROLE_ID3}', f'0x{USER_ID3}')

        # Execute extrinsic-call-stack
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'Extrinsic-call-stack failed: {receipt.error_message}')

    def check_ok_wo_enable_and_return(self, data, cnt=1):
        self.assertIn('Ok', data)
        if isinstance(data['Ok'], list):
            self.assertEqual(
                len([e for e in data['Ok'] if 'enabled' in e and e['enabled']]),
                cnt,
                f'Expected {cnt} enabled entities {data["Ok"]}')
        return data['Ok']

    def check_all_ok_and_return_all(self, data, cnt=1):
        self.assertIn('Ok', data)
        if isinstance(data['Ok'], list):
            self.assertEqual(len(data['Ok']), cnt, f'Expected {cnt} enabled entities {data["Ok"]}')
        return data['Ok']

    def check_err_and_return(self, data):
        self.assertIn('Err', data)
        return data['Err']

    ##############################################################################
    def rbac_rpc_fetch_entity(self, kp_src, entity, entity_id, name):
        if 'Role' == entity:
            data = rbac_rpc_fetch_role(self.substrate, kp_src.ss58_address, entity_id)
        elif 'Permission' == entity:
            data = rbac_rpc_fetch_permission(self.substrate, kp_src.ss58_address, entity_id)
        elif 'Group' == entity:
            data = rbac_rpc_fetch_group(self.substrate, kp_src.ss58_address, entity_id)
        else:
            raise IOError(f'Unknown entity: {entity}')
        data = self.check_ok_wo_enable_and_return(data)
        self.assertEqual(data['id'], entity_id)
        # assert(binascii.unhexlify(data['name'][2:]) == bytes(name, 'utf-8'))
        self.assertEqual(data['name'], name)

    def rbac_rpc_fetch_entities(self, kp_src, entity, entity_ids, names):
        if 'Role' == entity:
            data = rbac_rpc_fetch_roles(self.substrate, kp_src.ss58_address)
        elif 'Permission' == entity:
            data = rbac_rpc_fetch_permissions(self.substrate, kp_src.ss58_address)
        elif 'Group' == entity:
            data = rbac_rpc_fetch_groups(self.substrate, kp_src.ss58_address)
        else:
            raise IOError(f'Unknown entity: {entity}')
        data = self.check_ok_wo_enable_and_return(data, len(entity_ids))
        for i in range(0, len(names)):
            self.assertIn({
                'id': entity_ids[i],
                'name': names[i],
                'enabled': True
            }, data)

    def rbac_rpc_fetch_group_roles(self, kp_src, group_id, role_ids):
        data = rbac_rpc_fetch_group_roles(self.substrate, kp_src.ss58_address, group_id)
        data = self.check_all_ok_and_return_all(data, len(role_ids))
        for i in range(0, len(role_ids)):
            self.assertIn({
                'role': role_ids[i],
                'group': group_id
            }, data)

    def rbac_rpc_fetch_group_permissions(
            self, kp_src, group_id, perm_ids, names):
        data = rbac_rpc_fetch_group_permissions(self.substrate, kp_src.ss58_address, group_id)
        data = self.check_ok_wo_enable_and_return(data, len(perm_ids))
        for i in range(0, len(perm_ids)):
            self.assertIn({
                'id': perm_ids[i],
                'name': names[i],
                'enabled': True
            }, data)

    def rbac_rpc_fetch_role_permissions(self, kp_src, role_id, perm_ids):
        data = rbac_rpc_fetch_role_permissions(self.substrate, kp_src.ss58_address, role_id)
        data = self.check_all_ok_and_return_all(data, len(perm_ids))
        for i in range(0, len(perm_ids)):
            self.assertIn({
                'permission': perm_ids[i],
                'role': role_id
            }, data)

    def rbac_rpc_fetch_user_roles(self, kp_src, user_id, role_ids):
        data = rbac_rpc_fetch_user_roles(self.substrate, kp_src.ss58_address, user_id)
        data = self.check_all_ok_and_return_all(data, len(role_ids))
        for i in range(0, len(role_ids)):
            self.assertIn({
                'role': role_ids[i],
                'user': user_id
            }, data)

    def rbac_rpc_fetch_user_groups(self, kp_src, user_id, group_ids):
        data = rbac_rpc_fetch_user_groups(self.substrate, kp_src.ss58_address, user_id)
        data = self.check_all_ok_and_return_all(data, len(group_ids))
        for i in range(0, len(group_ids)):
            self.assertIn({
                'group': group_ids[i],
                'user': user_id
            }, data)

    def rbac_rpc_fetch_user_permissions(
            self, kp_src, user_id, perm_ids, names):
        data = rbac_rpc_fetch_user_permissions(self.substrate, kp_src.ss58_address, user_id)
        data = self.check_ok_wo_enable_and_return(data, len(perm_ids))
        for i in range(0, len(perm_ids)):
            self.assertIn({
                'id': perm_ids[i],
                'name': names[i],
                'enabled': True
            }, data)

    ##############################################################################
    # Single, simple test for RPC fetchRole
    def verify_rpc_fetch_role(self, kp_src):
        self.rbac_rpc_fetch_entity(
            kp_src, 'Role', ROLE_ID1, ROLE_NM1)
        self.rbac_rpc_fetch_entity(
            kp_src, 'Role', ROLE_ID3, ROLE_NM3)
        show_success_msg('rpc_fetch_role')

    # Single, simple test for RPC fetchRoles
    def verify_rpc_fetch_roles(self, kp_src):
        self.rbac_rpc_fetch_entities(
            kp_src, 'Role',
            [ROLE_ID1, ROLE_ID2, ROLE_ID3],
            [ROLE_NM1, ROLE_NM2, ROLE_NM3]
        )
        show_success_msg('rpc_fetch_roles')

    # Single, simple test for RPC fetchPermission
    def verify_rpc_fetch_permission(self, kp_src):
        self.rbac_rpc_fetch_entity(
            kp_src, 'Permission', PERM_ID2, PERM_NM2)
        self.rbac_rpc_fetch_entity(
            kp_src, 'Permission', PERM_ID4, PERM_NM4)
        show_success_msg('rpc_fetch_permission')

    # Single, simple test for RPC fetchRoles
    def verify_rpc_fetch_permissions(self, kp_src):
        self.rbac_rpc_fetch_entities(
            kp_src, 'Permission',
            [PERM_ID1, PERM_ID2, PERM_ID3, PERM_ID4],
            [PERM_NM1, PERM_NM2, PERM_NM3, PERM_NM4]
        )
        show_success_msg('verify_rpc_fetch_permissions')

    # Single, simple test for RPC fetchGroup
    def verify_rpc_fetch_group(self, kp_src):
        self.rbac_rpc_fetch_entity(
            kp_src, 'Group', GROUP_ID2, GROUP_NM2)
        show_success_msg('rpc_fetch_group')

    # Single, simple test for RPC fetchRoles
    def verify_rpc_fetch_groups(self, kp_src):
        self.rbac_rpc_fetch_entities(
            kp_src, 'Group',
            [GROUP_ID1, GROUP_ID2],
            [GROUP_NM1, GROUP_NM2])
        show_success_msg('verify_rpc_fetch_groups')

    # Single test for RPC fetchGroupRoles
    def verify_rpc_fetch_group_roles(self, kp_src):
        self.rbac_rpc_fetch_group_roles(
            kp_src,
            GROUP_ID1,
            [ROLE_ID1, ROLE_ID2])
        self.rbac_rpc_fetch_group_roles(
            kp_src,
            GROUP_ID2,
            [ROLE_ID3])
        show_success_msg('verify_rpc_fetch_group_roles')

    # Single test for RPC fetchRolePermissions
    def verify_rpc_fetch_role_permissions(self, kp_src):
        self.rbac_rpc_fetch_role_permissions(
            kp_src,
            ROLE_ID1,
            [PERM_ID1, PERM_ID2])
        self.rbac_rpc_fetch_role_permissions(
            kp_src,
            ROLE_ID2,
            [PERM_ID3])
        self.rbac_rpc_fetch_role_permissions(
            kp_src,
            ROLE_ID3,
            [PERM_ID4])
        show_success_msg('verify_rpc_fetch_role_permissions')

    # Single, simple test for RPC fetchGroupPermissions
    def verify_rpc_fetch_group_permissions(self, kp_src):
        self.rbac_rpc_fetch_group_permissions(
            kp_src,
            GROUP_ID1,
            [PERM_ID1, PERM_ID2, PERM_ID3],
            [PERM_NM1, PERM_NM2, PERM_NM3])
        self.rbac_rpc_fetch_group_permissions(
            kp_src,
            GROUP_ID2,
            [PERM_ID4],
            [PERM_NM4])
        show_success_msg('verify_rpc_fetch_group_permissions')

    # Single test for RPC fetchUserGroups
    def verify_rpc_fetch_user_roles(self, kp_src):
        self.rbac_rpc_fetch_user_roles(
            kp_src,
            USER_ID3,
            [ROLE_ID2, ROLE_ID3])
        show_success_msg('verify_rpc_fetch_user_roles')

    # Single test for RPC fetchUserGroups
    def verify_rpc_fetch_user_groups(self, kp_src):
        self.rbac_rpc_fetch_user_groups(
            kp_src,
            USER_ID1,
            [GROUP_ID1])
        self.rbac_rpc_fetch_user_groups(
            kp_src,
            USER_ID2,
            [GROUP_ID2])
        show_success_msg('verify_rpc_fetch_user_groups')

    # Single test for RPC fetchUserPermissions
    def verify_rpc_fetch_user_permissions(self, kp_src):
        self.rbac_rpc_fetch_user_permissions(
            kp_src,
            USER_ID1,
            [PERM_ID1, PERM_ID2, PERM_ID3],
            [PERM_NM1, PERM_NM2, PERM_NM3])
        show_success_msg('verify_rpc_fetch_user_permissions')

    # Simple test for RBAC-fail (request entity, which does not exist)
    def verify_rpc_fail_wrong_id(self, kp_src):
        user_id = USER_IDE
        data = rbac_rpc_fetch_user_groups(
            self.substrate, kp_src.ss58_address, user_id)
        data = self.check_err_and_return(data)
        self.assertEqual(data['typ'], 'AssignmentDoesNotExist')
        self.assertEqual(data['param'], user_id)
        show_success_msg('verify_rpc_fail_wrong_id')

    # Simple test for RBAC-fail (request entity, which is disabled)
    def verify_rpc_fail_disabled_id(self, kp_src):
        group_id = GROUP_ID3
        data = rbac_rpc_fetch_group(
            self.substrate, kp_src.ss58_address, group_id)
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
            fund(self.substrate, KP_GLOBAL_SUDO, KP_TEST, 1000 * 10 ** 18)
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
