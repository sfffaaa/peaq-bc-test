import unittest
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, get_chain, get_collators, fund, get_block_height, get_account_balance, get_block_hash
from tools.utils import KP_GLOBAL_SUDO, exist_pallet
from tools.payload import sudo_call_compose, sudo_extrinsic_send, user_extrinsic_send
from tools.restart import restart_parachain_launch
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
        self.collator = [Keypair.create_from_uri('//Bob')]
        self.delegators = [
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic()),
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        ]

    def tearDown(self):
        restart_parachain_launch()

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

    def test_issue_fixed_precentage(self):
        if not exist_pallet(self.substrate, 'StakingFixedRewardCalculator'):
            warnings.warn('StakingFixedRewardCalculator pallet not exist, skip the test')
            return
        collator_percentage = 80
        delegator_percentage = 20

        # Check it's the peaq-dev parachain
        self.assertEqual(self.chain_name, 'peaq-dev')
        set_reward_rate(self.substrate, collator_percentage, delegator_percentage)

        # setup
        # Get the collator account
        collator = self.get_one_collator_without_delegator(self.collator)
        self.assertNotEqual(collator, None)
        # Transfer token to new key
        fund(self.substrate, self.delegators[0], 10000 * 10 ** 18)
        fund(self.substrate, self.delegators[1], 10000 * 10 ** 18)

        # Add the delegator
        receipt = add_delegator(self.substrate, self.delegators[0], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        receipt = add_delegator(self.substrate, self.delegators[1], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        # Check the delegator is added
        # Wait for two session
        print('Wait for two session')
        sleep_time = 2 * 60
        time.sleep(sleep_time)

        delegators_reward = [self.get_balance_difference(delegator.ss58_address) for delegator in self.delegators]
        collator_reward = self.get_balance_difference(str(collator['id']))
        self.assertEqual(delegators_reward[0], delegators_reward[1], 'The reward is not equal')
        self.assertEqual(collator_percentage / delegators_reward * sum(delegators_reward),
                         collator_reward, 'The reward is not equal')

    def test_issue_coeffective(self):
        if not exist_pallet(self.substrate, 'StakingCoefficientRewardCalculator'):
            warnings.warn('StakingCoefficientRewardCalculator pallet not exist, skip the test')
            return

        # Check it's the peaq-dev parachain
        set_coefficient(self.substrate, 2)
        self.assertEqual(self.chain_name, 'peaq-dev')

        # setup
        # Get the collator account
        collator = self.get_one_collator_without_delegator(self.collator)
        # {'id': '5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty', 'stake': 64000, 'delegators': [], 'total': 64000, 'status': 'Active'}
        self.assertNotEqual(collator, None)
        # Transfer token to new key
        fund(self.substrate, self.delegators[0], 10000 * 10 ** 18)
        fund(self.substrate, self.delegators[1], 10000 * 10 ** 18)

        # Add the delegator
        receipt = add_delegator(self.substrate, self.delegators[0], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        receipt = add_delegator(self.substrate, self.delegators[1], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        # Check the delegator is added
        # Wait for two session
        print('Wait for two session')
        sleep_time = 2 * 60
        time.sleep(sleep_time)

        delegators_reward = [self.get_balance_difference(delegator.ss58_address) for delegator in self.delegators]
        collator_reward = self.get_balance_difference(str(collator['id']))
        self.assertEqual(delegators_reward[0], delegators_reward[1], 'The reward is not equal')
        self.assertEqual(sum(delegators_reward), collator_reward, 'The reward is not equal')
