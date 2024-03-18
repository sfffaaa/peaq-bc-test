import unittest
from tests.utils_func import restart_parachain_and_runtime_upgrade
from tools.runtime_upgrade import wait_until_block_height
from substrateinterface import SubstrateInterface
from tools.utils import WS_URL, ETH_URL
from peaq.utils import ExtrinsicBatch
from tools.peaq_eth_utils import get_contract
from tools.peaq_eth_utils import get_eth_chain_id, calculate_evm_default_addr
from tools.peaq_eth_utils import GAS_LIMIT, get_eth_info
from tools.utils import KP_GLOBAL_SUDO, KP_COLLATOR
from peaq.utils import get_block_hash
from web3 import Web3


PARACHAIN_STAKING_ABI_FILE = 'ETH/parachain-staking/abi'
PARACHAIN_STAKING_ADDR = '0x0000000000000000000000000000000000000807'


class bridge_parachain_staking_test(unittest.TestCase):
    def setUp(self):
        restart_parachain_and_runtime_upgrade()
        wait_until_block_height(SubstrateInterface(url=WS_URL), 1)

        self._substrate = SubstrateInterface(url=WS_URL)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._kp_moon = get_eth_info()
        self._kp_mars = get_eth_info()
        self._eth_chain_id = get_eth_chain_id(self._substrate)

    def _fund_users(self):
        # Fund users
        batch = ExtrinsicBatch(self._substrate, KP_GLOBAL_SUDO)
        batch.compose_call(
            'Balances',
            'transfer',
            {
                'dest': self._kp_moon['substrate'],
                'value': 100 * 10 ** 18,
            }
        )
        batch.compose_call(
            'Balances',
            'transfer',
            {
                'dest': self._kp_mars['substrate'],
                'value': 100 * 10 ** 18,
            }
        )
        return batch.execute()

    def evm_join_delegators(self, contract, eth_kp_src, eth_collator_addr, stake):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.joinDelegators(eth_collator_addr, stake).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': 10633039,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self._eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def evm_delegator_stake_more(self, contract, eth_kp_src, eth_collator_addr, stake):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.delegatorStakeMore(eth_collator_addr, stake).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self._eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def evm_delegator_stake_less(self, contract, eth_kp_src, eth_collator_addr, stake):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.delegatorStakeLess(eth_collator_addr, stake).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self._eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def evm_delegator_leave_delegators(self, contract, eth_kp_src):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.leaveDelegators().build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self._eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def evm_delegator_revoke_delegation(self, contract, eth_kp_src, eth_collator_addr):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.revokeDelegation(eth_collator_addr).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self._eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def evm_delegator_unlock_unstaked(self, contract, eth_kp_src, eth_addr):
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(eth_kp_src.ss58_address)
        tx = contract.functions.unlockUnstaked(eth_addr).build_transaction({
            'from': eth_kp_src.ss58_address,
            'gas': GAS_LIMIT,
            'maxFeePerGas': w3.to_wei(250, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
            'nonce': nonce,
            'chainId': self._eth_chain_id})

        signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def get_stake_number(self, sub_addr):
        data = self._substrate.query('ParachainStaking', 'DelegatorState', [sub_addr])
        # {'delegations':
        #       [{'owner': '5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL', 'amount': 262144000}],
        #  'total': 262144000}
        return data.value

    def test_get_collator_list(self):
        contract = get_contract(self._w3, PARACHAIN_STAKING_ADDR, PARACHAIN_STAKING_ABI_FILE)

        out = contract.functions.getCollatorList().call()
        golden_data = self._substrate.query('ParachainStaking', 'TopCandidates')
        golden_data = golden_data.value
        self.assertEqual(len(out), len(golden_data))

        for i in range(len(out)):
            # self.assertEqual(out[i]['addr'], golden_data[i]['collator'])
            pk = bytes.fromhex(self._substrate.ss58_decode(golden_data[i]["owner"]))
            addr = calculate_evm_default_addr(pk)
            self.assertEqual(out[i][0], addr)
            self.assertEqual(out[i][1], golden_data[i]['amount'])

    def collator_claim_default(self, kp):
        batch = ExtrinsicBatch(self._substrate, kp)
        batch.compose_call(
            'AddressUnification',
            'claim_default_account',
            {}
        )
        return batch.execute()

    def test_delegator_not_claim(self):
        contract = get_contract(self._w3, PARACHAIN_STAKING_ADDR, PARACHAIN_STAKING_ABI_FILE)
        out = contract.functions.getCollatorList().call()

        collator_linked = out[0][2]
        self.assertEqual(collator_linked, False, f'collator_linked: {collator_linked}')

    def get_event(self, block_hash, module, event):
        events = self._substrate.get_events(block_hash)
        for e in events:
            if e.value['event']['module_id'] == module and e.value['event']['event_id'] == event:
                return {'attributes': e.value['event']['attributes']}
        return None

    def test_delegator_join_more_less_leave(self):
        receipt = self._fund_users()
        self.assertEqual(receipt.is_success, True, f'fund_users fails, receipt: {receipt}')
        receipt = self.collator_claim_default(KP_COLLATOR)
        self.assertEqual(receipt.is_success, True, f'collator_claim_default fails, receipt: {receipt}')

        contract = get_contract(self._w3, PARACHAIN_STAKING_ADDR, PARACHAIN_STAKING_ABI_FILE)
        out = contract.functions.getCollatorList().call()

        collator_eth_addr = out[0][0]
        collator_eth_addr = Web3.to_checksum_address(collator_eth_addr)
        collator_num = out[0][1]
        collator_linked = out[0][2]
        self.assertEqual(collator_linked, True, f'collator_linked: {collator_linked}')
        evm_receipt = self.evm_join_delegators(contract, self._kp_moon['kp'], collator_eth_addr, collator_num)
        self.assertEqual(evm_receipt['status'], 1, f'join fails, evm_receipt: {evm_receipt}')
        bl_hash = get_block_hash(self._substrate, evm_receipt['blockNumber'])
        event = self.get_event(bl_hash, 'ParachainStaking', 'Delegation')
        self.assertEqual(
            event['attributes'],
            (self._kp_moon['substrate'], collator_num, KP_COLLATOR.ss58_address, 2 * collator_num),
            f'join fails, event: {event}')

        stake = self.get_stake_number(self._kp_moon['substrate'])
        self.assertEqual(stake['total'], collator_num, f'join fails, stake: {stake}, collator_num: {collator_num}')

        # Delegator stake more
        evm_receipt = self.evm_delegator_stake_more(contract, self._kp_moon['kp'], collator_eth_addr, collator_num)
        self.assertEqual(evm_receipt['status'], 1, f'stake more fails, evm_receipt: {evm_receipt}')

        # Check the delegator's stake
        stake = self.get_stake_number(self._kp_moon['substrate'])
        self.assertEqual(stake['total'], collator_num * 2, f'join fails, stake: {stake}, collator_num: {collator_num}')

        # Delegator stake less
        evm_receipt = self.evm_delegator_stake_less(contract, self._kp_moon['kp'], collator_eth_addr, collator_num)
        self.assertEqual(evm_receipt['status'], 1, f'stake more fails, evm_receipt: {evm_receipt}')

        # Check the delegator's stake
        stake = self.get_stake_number(self._kp_moon['substrate'])
        self.assertEqual(stake['total'], collator_num, f'join fails, stake: {stake}, collator_num: {collator_num}')

        # Delegator leave
        evm_receipt = self.evm_delegator_leave_delegators(contract, self._kp_moon['kp'])
        self.assertEqual(evm_receipt['status'], 1, f'leave fails, evm_receipt: {evm_receipt}')
        bl_hash = get_block_hash(self._substrate, evm_receipt['blockNumber'])
        event = self.get_event(bl_hash, 'ParachainStaking', 'DelegatorLeft')
        self.assertEqual(
            event['attributes'],
            (self._kp_moon['substrate'], collator_num),
            f'join fails, event: {event}')

        # Unstake the delegator
        print(f'address {self._kp_moon["eth"]}')
        evm_receipt = self.evm_delegator_unlock_unstaked(contract, self._kp_moon['kp'], self._kp_moon['eth'])
        self.assertEqual(evm_receipt['status'], 1, f'unlock unstaked fails, evm_receipt: {evm_receipt}')
        print(f'receipt block number: {evm_receipt["blockNumber"]}')

        # Note: The unlock unstaked didn't success because we have to wait about 20+ blocks;
        # therefore, we don't test here. Can just test maunally

    def test_delegator_revoke(self):
        receipt = self._fund_users()
        self.assertEqual(receipt.is_success, True, f'fund_users fails, receipt: {receipt}')
        receipt = self.collator_claim_default(KP_COLLATOR)
        self.assertEqual(receipt.is_success, True, f'collator_claim_default fails, receipt: {receipt}')

        contract = get_contract(self._w3, PARACHAIN_STAKING_ADDR, PARACHAIN_STAKING_ABI_FILE)
        out = contract.functions.getCollatorList().call()

        collator_eth_addr = out[0][0]
        collator_eth_addr = Web3.to_checksum_address(collator_eth_addr)
        collator_num = out[0][1]
        collator_linked = out[0][2]
        self.assertEqual(collator_linked, True, f'collator_linked: {collator_linked}')
        evm_receipt = self.evm_join_delegators(contract, self._kp_moon['kp'], collator_eth_addr, collator_num)
        self.assertEqual(evm_receipt['status'], 1, f'join fails, evm_receipt: {evm_receipt}')
        bl_hash = get_block_hash(self._substrate, evm_receipt['blockNumber'])
        event = self.get_event(bl_hash, 'ParachainStaking', 'Delegation')
        self.assertEqual(
            event['attributes'],
            (self._kp_moon['substrate'], collator_num, KP_COLLATOR.ss58_address, 2 * collator_num),
            f'join fails, event: {event}')

        # Check the delegator's stake
        stake = self.get_stake_number(self._kp_moon['substrate'])
        self.assertEqual(stake['total'], collator_num, f'join fails, stake: {stake}, collator_num: {collator_num}')

        # Delegator leave
        evm_receipt = self.evm_delegator_revoke_delegation(contract, self._kp_moon['kp'], collator_eth_addr)
        self.assertEqual(evm_receipt['status'], 1, f'leave fails, evm_receipt: {evm_receipt}')
        bl_hash = get_block_hash(self._substrate, evm_receipt['blockNumber'])
        event = self.get_event(bl_hash, 'ParachainStaking', 'DelegatorLeft')
        self.assertEqual(
            event['attributes'],
            (self._kp_moon['substrate'], collator_num),
            f'join fails, event: {event}')

        # Note: The unlock unstaked didn't success because we have to wait about 20+ blocks;
        # therefore, we don't test here. Can just test maunally
