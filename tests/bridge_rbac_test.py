from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import calculate_evm_addr
from tools.utils import WS_URL, ETH_URL
from peaq.eth import calculate_evm_account
from tools.peaq_eth_utils import get_eth_chain_id
from tools.peaq_eth_utils import call_eth_transfer_a_lot, get_contract, generate_random_hex, GAS_LIMIT, TX_SUCCESS_STATUS
from web3 import Web3
import enum
import unittest
from peaq.extrinsic import transfer

import pprint
pp = pprint.PrettyPrinter(indent=4)


# Keypair to use for dispatches
KP_SRC = Keypair.create_from_uri('//Alice')
# Address of RBAC precompile contract
RBAC_ADDRESS = '0x0000000000000000000000000000000000000802'
# H160 Address to use for EVM transactions
ETH_PRIVATE_KEY = generate_random_hex(15).encode("utf-8")
# RBAC Precompile ABI
ABI_FILE = 'ETH/rbac/rbac.sol.json'
# Number of tokens with decimals
TOKEN_NUM = 10000 * pow(10, 15)


def generate_random_id():
    return generate_random_hex(15).encode("utf-8")


# generates a tuple of (id, name) for a role, permission, or group
def generate_random_tuple():
    id = generate_random_id()
    name = f'NAME{id[:4]}'.encode("utf-8")
    return (id, name)


##############################################################################
# RbacErrorType as Enum for convenience
##############################################################################
class RbacErrorType(enum.Enum):
    # Returned if the Entity already exists
    EntityAlreadyExist = "EntityAlreadyExist"
    # Returned if the Entity does not exists
    EntityDoesNotExist = "EntityDoesNotExist"
    # Returned if the Entity does not belong to the caller
    EntityAuthorizationFailed = "EntityAuthorizationFailed"
    # Returned if the Entity is not enabled
    EntityDisabled = "EntityDisabled"
    # Returned if an assignment does already exist
    AssignmentAlreadyExist = "AssignmentAlreadyExist"
    # Returned if an assignment does not exist
    AssignmentDoesNotExist = "AssignmentDoesNotExist"
    # Exceeds max characters
    NameExceedMaxChar = "NameExceedMaxChar"

##############################################################################
# Helper functions for submitting transactions
##############################################################################


def _calcualte_evm_basic_req(substrate, w3, addr):
    return {
        'from': addr,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': w3.eth.get_transaction_count(addr),
        'chainId': get_eth_chain_id(substrate)
    }


def _sign_and_submit_transaction(tx, w3, signer):
    signed_txn = w3.eth.account.sign_transaction(tx, private_key=signer.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)


# NOTE: fetch_user_roles will return an error if the user has no roles
class TestBridgeRbac(unittest.TestCase):

    ##############################################################################
    # Wrapper functions for state chainging extrinsics
    ##############################################################################

    def _add_role(self, role_id, name):
        tx = self._contract.functions.addRole(role_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _update_role(self, role_id, name):
        tx = self._contract.functions.updateRole(role_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _disable_role(self, role_id):
        tx = self._contract.functions.disableRole(role_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_role_to_user(self, role_id, user_id):
        tx = self._contract.functions.assignRoleToUser(role_id, user_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_role_to_user(self, role_id, user_id):
        tx = self._contract.functions.unassignRoleToUser(role_id, user_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _add_permission(self, permission_id, name):
        tx = self._contract.functions.addPermission(permission_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _update_permission(self, permission_id, name):
        tx = self._contract.functions.updatePermission(permission_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _disable_permission(self, permission_id):
        tx = self._contract.functions.disablePermission(permission_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_permission_to_role(self, permission_id, role_id):
        tx = self._contract.functions.assignPermissionToRole(permission_id, role_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_permission_to_role(self, permission_id, role_id):
        tx = self._contract.functions.unassignPermissionToRole(permission_id, role_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _add_group(self, group_id, name):
        tx = self._contract.functions.addGroup(group_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _update_group(self, group_id, name):
        tx = self._contract.functions.updateGroup(group_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _disable_group(self, group_id):
        tx = self._contract.functions.disableGroup(group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_role_to_group(self, role_id, group_id):
        tx = self._contract.functions.assignRoleToGroup(role_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_role_to_group(self, role_id, group_id):
        tx = self._contract.functions.unassignRoleToGroup(role_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_user_to_group(self, user_id, group_id):
        tx = self._contract.functions.assignUserToGroup(user_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_user_to_group(self, user_id, group_id):
        tx = self._contract.functions.unassignUserToGroup(user_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    ##############################################################################
    # Functions that verify events
    ##############################################################################

    # verify add/update role
    def _verify_role_add_update_event(self, events, account, role_id, name):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)
        self.assertEqual(events[0]['args']['name'], name)

    def _verify_role_disabled_event(self, events, account, role_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)

    # verify assign/unassign role to user
    def _verify_role_assign_or_unassign_event(self, events, account, role_id, user_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)
        self.assertEqual(events[0]['args']['user_id'], user_id)

    def _verify_permission_add_or_update_event(self, events, account, permission_id, name):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['permission_id'], permission_id)
        self.assertEqual(events[0]['args']['name'], name)

    def _verify_permission_disabled_event(self, events, account, permission_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['permission_id'], permission_id)

    def _verify_permission_assigned_or_unassigned_to_role_event(self, events, account, permission_id, role_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['permission_id'], permission_id)
        self.assertEqual(events[0]['args']['role_id'], role_id)

    def _verify_group_add_or_update_event(self, events, account, group_id, name):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['group_id'], group_id)
        self.assertEqual(events[0]['args']['name'], name)

    def _verify_group_disabled_event(self, events, account, group_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['group_id'], group_id)

    def _verify_role_assigned_or_unassigned_to_group_event(self, events, account, role_id, group_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)
        self.assertEqual(events[0]['args']['group_id'], group_id)

    def _verify_user_assigned_or_unassigned_to_group_event(self, events, account, user_id, group_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['user_id'], user_id)
        self.assertEqual(events[0]['args']['group_id'], group_id)

    ##############################################################################
    # Functions that verify mutations
    ##############################################################################

    def _verify_add_role(self, tx, role_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleAdded.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_add_update_event(events, self._eth_kp_src.ss58_address, role_id, name)

        # fetch role and verify
        data = self._contract.functions.fetchRole(self._eth_kp_src.ss58_address, role_id).call()
        self.assertEqual(data[0], role_id)
        self.assertEqual(data[1], name)

        return tx

    def _verify_update_role(self, tx, role_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_add_update_event(events, self._eth_kp_src.ss58_address, role_id, name)

        # fetch role and verify
        data = self._contract.functions.fetchRole(self._eth_kp_src.ss58_address, role_id).call()
        self.assertEqual(data[0], role_id)
        self.assertEqual(data[1], name)

        return tx

    # fetch_role will return an exception if the role is disabled
    # exception is caught and verified
    def _verify_disable_role(self, tx, role_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleRemoved.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_disabled_event(events, self._eth_kp_src.ss58_address, role_id)

        # fetch role and verify
        with self.assertRaises(ValueError) as tx_info:
            self._contract.functions.fetchRole(self._eth_kp_src.ss58_address, role_id).call()

        self.assertIn(RbacErrorType.EntityDisabled.value, tx_info.exception.args[0]['message'])

        return tx

    def _verify_assign_role_to_user(self, tx, role_id, user_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleAssignedToUser.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assign_or_unassign_event(events, self._eth_kp_src.ss58_address, role_id, user_id)

        # verify fetch_user_roles returns correct data
        data = self._contract.functions.fetchUserRoles(self._eth_kp_src.ss58_address, user_id).call()
        if not any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} not assigned to user {user_id}')

        return tx

    def _verify_unassign_role_to_user(self, tx, role_id, user_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleUnassignedToUser.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assign_or_unassign_event(events, self._eth_kp_src.ss58_address, role_id, user_id)

        # verify fetch_user_roles returns correct data
        data = self._contract.functions.fetchUserRoles(self._eth_kp_src.ss58_address, user_id).call()
        if any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} still assigned to user {user_id}')

    def _verify_add_permission(self, tx, permission_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionAdded.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_add_or_update_event(events, self._eth_kp_src.ss58_address, permission_id, name)

        # fetch permission and verify
        data = self._contract.functions.fetchPermission(self._eth_kp_src.ss58_address, permission_id).call()
        self.assertEqual(data[0], permission_id)
        self.assertEqual(data[1], name)

        return tx

    def _verify_update_permission(self, tx, permission_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_add_or_update_event(events, self._eth_kp_src.ss58_address, permission_id, name)

        # fetch permission and verify
        data = self._contract.functions.fetchPermission(self._eth_kp_src.ss58_address, permission_id).call()
        self.assertEqual(data[0], permission_id)
        self.assertEqual(data[1], name)

        return tx

    def _verify_disable_permission(self, tx, permission_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionDisabled.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_disabled_event(events, self._eth_kp_src.ss58_address, permission_id)

        # fetch role and verify
        with self.assertRaises(ValueError) as tx_info:
            self._contract.functions.fetchPermission(self._eth_kp_src.ss58_address, permission_id).call()

        self.assertIn(RbacErrorType.EntityDisabled.value, tx_info.exception.args[0]['message'])

        return tx

    def _verify_assign_permission_to_role(self, tx, permission_id, role_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionAssigned.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_assigned_or_unassigned_to_role_event(events, self._eth_kp_src.ss58_address, permission_id, role_id)

        # verify fetch_role_permissions returns correct data
        data = self._contract.functions.fetchRolePermissions(self._eth_kp_src.ss58_address, role_id).call()
        if not any(permission_id in permissions for permissions in data):
            self.fail(f'Permission {permission_id} not assigned to role {role_id}')

        return tx

    def _verify_unassign_permission_to_role(self, tx, permission_id, role_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionUnassignedToRole.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_assigned_or_unassigned_to_role_event(events, self._eth_kp_src.ss58_address, permission_id, role_id)

        # verify fetch_role_permissions returns correct data
        data = self._contract.functions.fetchRolePermissions(self._eth_kp_src.ss58_address, role_id).call()
        if any(permission_id in permissions for permissions in data):
            self.fail(f'Permission {permission_id} still assigned to role {role_id}')

        return tx

    def _verify_add_group(self, tx, group_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.GroupAdded.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_group_add_or_update_event(events, self._eth_kp_src.ss58_address, group_id, name)

        # fetch group and verify
        data = self._contract.functions.fetchGroup(self._eth_kp_src.ss58_address, group_id).call()
        self.assertEqual(data[0], group_id)
        self.assertEqual(data[1], name)

        return tx

    def _verify_update_group(self, tx, group_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.GroupUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_group_add_or_update_event(events, self._eth_kp_src.ss58_address, group_id, name)

        # fetch group and verify
        data = self._contract.functions.fetchGroup(self._eth_kp_src.ss58_address, group_id).call()
        self.assertEqual(data[0], group_id)
        self.assertEqual(data[1], name)

    def _verify_disable_group(self, tx, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.GroupDisabled.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_group_disabled_event(events, self._eth_kp_src.ss58_address, group_id)

        # fetch role and verify
        with self.assertRaises(ValueError) as tx_info:
            self._contract.functions.fetchGroup(self._eth_kp_src.ss58_address, group_id).call()

        self.assertIn(RbacErrorType.EntityDisabled.value, tx_info.exception.args[0]['message'])

    def _verify_assign_role_to_group(self, tx, role_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleAssignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, role_id, group_id)

        # verify fetch_group_roles returns correct data
        data = self._contract.functions.fetchGroupRoles(self._eth_kp_src.ss58_address, group_id).call()
        if not any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} not assigned to group {group_id}')

    def _verify_unassign_role_to_group(self, tx, role_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleUnassignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, role_id, group_id)

        # verify fetch_group_roles returns correct data
        data = self._contract.functions.fetchGroupRoles(self._eth_kp_src.ss58_address, group_id).call()
        if any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} still assigned to group {group_id}')

    def _verify_assign_user_to_group(self, tx, user_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.UserAssignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_user_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, user_id, group_id)

        # verify fetch_group_users returns correct data
        data = self._contract.functions.fetchUserGroups(self._eth_kp_src.ss58_address, user_id).call()
        if not any(group_id in groups for groups in data):
            self.fail(f'User {user_id} not assigned to group {group_id}')

    def _verify_unassign_user_to_group(self, tx, user_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS, tx)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.UserUnAssignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_user_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, user_id, group_id)

        # verify fetch_group_users returns correct data
        data = self._contract.functions.fetchUserGroups(self._eth_kp_src.ss58_address, user_id).call()
        if any(group_id in groups for groups in data):
            self.fail(f'User {user_id} still assigned to group {group_id}')

    def fund_account(self):
        # Setup eth_ko_src with some tokens
        transfer(self._substrate, KP_SRC, calculate_evm_account(self._eth_src), TOKEN_NUM)
        bl_hash = call_eth_transfer_a_lot(self._substrate, KP_SRC, self._eth_src, self._eth_kp_src.ss58_address.lower())
        # verify tokens have been transferred
        self.assertTrue(bl_hash, f'Failed to transfer token to {self._eth_kp_src.ss58_address}')

    def setUp(self):
        self._eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._substrate = SubstrateInterface(url=WS_URL)
        self._eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        self._contract = get_contract(self._w3, RBAC_ADDRESS, ABI_FILE)

    # *************************************************************************
    # Test RBAC Bridge
    # There is no testing scenarion and each test call is atomic.
    # Every _verify_add_*, _verify_update_*, _verify_assign_* has a corresponding _verify_disable_*, _verify_unassign_* call.
    # Each call is verified by checking the tx status, events, and data fetched by a fetch_* rpc call.
    # All state modifying extrinsics and fetch RPC calls are covered by these tests.
    # Accounting for the considerable amount of extrinsics and RPC calls, please invoke a PR if coverage can be improved.
    # *************************************************************************
    def test_rbac_bridge(self):

        users = [generate_random_tuple() for _ in range(3)]
        roles = [generate_random_tuple() for _ in range(3)]
        permissions = [generate_random_tuple() for _ in range(3)]
        groups = [generate_random_tuple() for _ in range(3)]

        # fund test account
        self.fund_account()

        # add roles, permissions and groups
        self._verify_add_role(self._add_role(*roles[0]), *roles[0])
        self._add_role(*roles[1])
        self._add_role(*roles[2])

        self._verify_add_permission(self._add_permission(*permissions[0]), *permissions[0])
        self._add_permission(*permissions[1])
        self._add_permission(*permissions[2])

        self._verify_add_group(self._add_group(*groups[0]), *groups[0])
        self._add_group(*groups[1])
        self._add_group(*groups[2])

        # update roles, permissions and groups
        self._verify_update_role(self._update_role(*roles[1]), *roles[1])
        self._verify_update_permission(self._update_permission(*permissions[1]), *permissions[1])
        self._verify_update_group(self._update_group(*groups[1]), *groups[1])

        # disable roles, permissions and groups
        self._verify_disable_role(self._disable_role(roles[2][0]), roles[2][0])
        self._verify_disable_permission(self._disable_permission(permissions[2][0]), permissions[2][0])
        self._verify_disable_group(self._disable_group(groups[2][0]), groups[2][0])

        # assign role to user
        self._verify_assign_role_to_user(self._assign_role_to_user(roles[0][0], users[0][0]), roles[0][0], users[0][0])
        self._assign_role_to_user(roles[1][0], users[0][0])
        self._assign_role_to_user(roles[2][0], users[0][0])

        # unassign role to user
        self._verify_unassign_role_to_user(self._unassign_role_to_user(roles[0][0], users[0][0]), roles[0][0], users[0][0])

        # assign permission to role
        self._verify_assign_permission_to_role(self._assign_permission_to_role(permissions[0][0], roles[0][0]), permissions[0][0], roles[0][0])
        self._assign_permission_to_role(permissions[1][0], roles[0][0])
        self._assign_permission_to_role(permissions[2][0], roles[0][0])

        # unassign permission to role
        self._verify_unassign_permission_to_role(self._unassign_permission_to_role(permissions[0][0], roles[0][0]), permissions[0][0], roles[0][0])

        # assign role to group
        self._verify_assign_role_to_group(self._assign_role_to_group(roles[0][0], groups[0][0]), roles[0][0], groups[0][0])
        self._assign_role_to_group(roles[1][0], groups[0][0])
        self._assign_role_to_group(roles[2][0], groups[0][0])

        # unassign role to group
        self._verify_unassign_role_to_group(self._unassign_role_to_group(roles[0][0], groups[0][0]), roles[0][0], groups[0][0])

        # assign user to group
        self._verify_assign_user_to_group(self._assign_user_to_group(users[0][0], groups[0][0]), users[0][0], groups[0][0])
        self._assign_user_to_group(users[0][0], groups[1][0])
        self._assign_user_to_group(users[0][0], groups[2][0])
        self._assign_user_to_group(users[1][0], groups[1][0])

        # unassign user to group
        self._verify_unassign_user_to_group(self._unassign_user_to_group(users[0][0], groups[0][0]), users[0][0], groups[0][0])
