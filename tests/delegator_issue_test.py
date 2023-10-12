import unittest
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, get_collators, batch_fund
from tools.utils import KP_GLOBAL_SUDO, exist_pallet, KP_COLLATOR
from tools.payload import sudo_call_compose, sudo_extrinsic_send, user_extrinsic_send
from peaq.utils import get_block_height, get_block_hash, get_chain
from peaq.utils import ExtrinsicBatch, get_account_balance
from tests.utils_func import restart_parachain_and_runtime_upgrade
import warnings


@user_extrinsic_send
def add_delegator(substrate, kp_delegator, addr_collator, stake_number):
    return substrate.compose_call(
        call_module='ParachainStaking',
        call_function='join_delegators',
        call_params={
            'collator': addr_collator,
            'amount': stake_number,
        })


@user_extrinsic_send
def collator_stake_more(substrate, kp_collator, stake_number):
    return substrate.compose_call(
        call_module='ParachainStaking',
        call_function='candidate_stake_more',
        call_params={
            'more': stake_number,
        })


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_coefficient(substrate, coefficient):
    return substrate.compose_call(
        call_module='StakingCoefficientRewardCalculator',
        call_function='set_coefficient',
        call_params={
            'coefficient': coefficient,
        }
    )


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_max_candidate_stake(substrate, stake):
    return substrate.compose_call(
        call_module='ParachainStaking',
        call_function='set_max_candidate_stake',
        call_params={
            'new': stake,
        }
    )


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_reward_rate(substrate, collator, delegator):
    return substrate.compose_call(
        call_module='StakingFixedRewardCalculator',
        call_function='set_reward_rate',
        call_params={
            'collator_rate': collator,
            'delegator_rate': delegator,
        }
    )


class TestDelegator(unittest.TestCase):
    def setUp(self):
        self.substrate = SubstrateInterface(
            url=WS_URL,
        )
        self.chain_name = get_chain(self.substrate)
        self.collator = [KP_COLLATOR]
        self.delegators = [
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic()),
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        ]

    def tearDown(self):
        restart_parachain_and_runtime_upgrade()

    def get_balance_difference(self, addr):
        current_height = get_block_height(self.substrate)
        current_block_hash = get_block_hash(self.substrate, current_height)
        now_balance = get_account_balance(self.substrate, addr, current_block_hash)

        previous_height = current_height - 1
        previous_block_hash = get_block_hash(self.substrate, previous_height)
        pre_balance = get_account_balance(self.substrate, addr, previous_block_hash)
        return now_balance - pre_balance

    def get_one_collator_without_delegator(self, keys):
        for key in keys:
            collator = get_collators(self.substrate, key)
            if str(collator['delegators']) == '[]':
                return collator
        return None

    def wait_get_reward(self, addr):
        time.sleep(12 * 2)
        count_down = 0
        wait_time = 120
        prev_balance = get_account_balance(self.substrate, addr)
        while count_down < wait_time:
            if prev_balance != get_account_balance(self.substrate, addr):
                return True
            print(f'already wait about {count_down} seconds')
            count_down += 12
            time.sleep(12)
        return False

    def test_issue_fixed_precentage(self):
        if not exist_pallet(self.substrate, 'StakingFixedRewardCalculator'):
            warnings.warn('StakingFixedRewardCalculator pallet not exist, skip the test')
            return

        collator_percentage = 80
        delegator_percentage = 20

        # Check it's the peaq-dev parachain
        self.assertTrue(self.chain_name in ['peaq-dev', 'peaq-dev-fork'])
        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        batch.compose_sudo_call('StakingFixedRewardCalculator', 'set_reward_rate', {
            'collator_rate': collator_percentage,
            'delegator_rate': delegator_percentage,
        })
        batch_fund(batch, self.delegators[0], 10000 * 10 ** 18)
        batch_fund(batch, self.delegators[1], 10000 * 10 ** 18)
        receipt = batch.execute_n_clear()
        self.assertTrue(receipt.is_success, f'batch execute failed, error: {receipt.error_message}')

        # setup
        # Get the collator account
        collator = self.get_one_collator_without_delegator(self.collator)
        self.assertNotEqual(collator, None)

        # Add the delegator
        receipt = add_delegator(self.substrate, self.delegators[0], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        receipt = add_delegator(self.substrate, self.delegators[1], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')

        print('Wait for delegator get reward')
        self.assertTrue(self.wait_get_reward(self.delegators[0].ss58_address))

        delegators_reward = [self.get_balance_difference(delegator.ss58_address) for delegator in self.delegators]
        collator_reward = self.get_balance_difference(str(collator['id']))
        self.assertEqual(delegators_reward[0], delegators_reward[1], 'The reward is not equal')
        self.assertEqual(collator_percentage / delegators_reward * sum(delegators_reward),
                         collator_reward, 'The reward is not equal')

    def internal_test_issue_coefficient(self, mega_tokens):
        if not exist_pallet(self.substrate, 'StakingCoefficientRewardCalculator'):
            warnings.warn('StakingCoefficientRewardCalculator pallet not exist, skip the test')
            return

        # Check it's the peaq-dev parachain
        self.assertTrue(self.chain_name in ['peaq-dev', 'peaq-dev-fork', 'krest', 'krest-network-fork'])

        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        batch.compose_sudo_call('BlockReward', 'set_max_currency_supply', {
            'limit': 10 ** 5 * mega_tokens
        })
        batch.compose_sudo_call('ParachainStaking', 'set_max_candidate_stake', {
            'new': 10 ** 5 * mega_tokens
        })
        batch.compose_sudo_call('StakingCoefficientRewardCalculator', 'set_coefficient', {
            'coefficient': 2,
        })
        batch_fund(batch, KP_COLLATOR, 20 * mega_tokens)
        batch_fund(batch, self.delegators[0], 10 * mega_tokens)
        batch_fund(batch, self.delegators[1], 10 * mega_tokens)
        receipt = batch.execute()
        self.assertTrue(receipt.is_success, f'batch execute failed, error: {receipt.error_message}')

        # Get the collator account
        receipt = collator_stake_more(self.substrate, KP_COLLATOR, 5 * mega_tokens)
        self.assertTrue(receipt.is_success, 'Stake failed')

        collator = self.get_one_collator_without_delegator(self.collator)
        self.assertGreaterEqual(int(str(collator['stake'])), 5 * mega_tokens)
        self.assertNotEqual(collator, None)

        # Add the delegator
        receipt = add_delegator(self.substrate, self.delegators[0], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        receipt = add_delegator(self.substrate, self.delegators[1], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')

        print('Wait for delegator get reward')
        self.assertTrue(self.wait_get_reward(self.delegators[0].ss58_address))

        delegators_reward = [self.get_balance_difference(delegator.ss58_address) for delegator in self.delegators]
        collator_reward = self.get_balance_difference(str(collator['id']))
        self.assertEqual(delegators_reward[0], delegators_reward[1], 'The reward is not equal')
        self.assertAlmostEqual(
            sum(delegators_reward) / collator_reward,
            1, 7,
            f'{sum(delegators_reward)} v.s. {collator_reward} is not equal')

    def test_issue_coeffective(self):
        self.internal_test_issue_coefficient(500000 * 10 ** 18)

    def test_issue_coeffective_large(self):
        self.internal_test_issue_coefficient(10 ** 15 * 10 ** 18)
