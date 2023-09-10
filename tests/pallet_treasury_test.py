from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, TOKEN_NUM_BASE_DEV, KP_GLOBAL_SUDO
from tools.utils import ExtrinsicBatch
from tools.payload import sudo_call_compose, sudo_extrinsic_send, user_extrinsic_send
import unittest

# Assumptions
# 1. Treasury address is:'5EYCAe5ijiYfyeZ2JJCGq56LmPyNRAKzpG4QkoQkkQNB5e6Z'

# Global Constants

# accounts to carty out diffirent transactions
KP_USER = Keypair.create_from_uri('//Alice')
KP_COUNCIL_FIRST_MEMBER = Keypair.create_from_uri('//Bob')
KP_COUNCIL_SECOND_MEMBER = Keypair.create_from_uri('//Charlie')
KP_BENEFICIARY = Keypair.create_from_uri('//Dave')
KP_TREASURY = '5EYCAe5ijiYfyeZ2JJCGq56LmPyNRAKzpG4QkoQkkQNB5e6Z'

WEIGHT_BOND = {
    'ref_time': 1000000000,
    'proof_size': 1000000
}
LENGTH_BOND = 100
AMOUNT = 10
TOTAL_AMOUNT = 10 ** 9 * 10 ** 18

DIVISION_FACTOR = pow(10, 7)


@user_extrinsic_send
def cast_vote(substrate, kp_member, proposal_hash, proposal_index, vote):
    return substrate.compose_call(
        call_module='Council',
        call_function='vote',
        call_params={
            'proposal': proposal_hash,
            'index': proposal_index,
            'approve': vote
        })


def set_member_by_sudo(batch, members, kp_prime_member, old_count, kp_prime):
    batch.compose_sudo_call(
        'Council',
        'set_members',
        {
            'new_members': members,
            'prime': kp_prime,
            'old_count': len(members)
        })


@user_extrinsic_send
def close_vote(substrate, kp_member, proposal_hash, proposal_index, weight_bond,
               length_bond):
    return substrate.compose_call(
        call_module='Council',
        call_function='close',
        call_params={
            'proposal_hash': proposal_hash,
            'index': proposal_index,
            'proposal_weight_bound': weight_bond,
            'length_bound': length_bond
        })


# To directly spend funds from treasury
@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def spend(substrate, value, beneficiary):
    return substrate.compose_call(
        call_module='Treasury',
        call_function='spend',
        call_params={
            'amount': value * TOKEN_NUM_BASE_DEV,
            'beneficiary': beneficiary.ss58_address
        })


class TestTreasury(unittest.TestCase):
    def setUp(self):
        self.substrate = SubstrateInterface(url=WS_URL)

    # To submit a spend proposal
    def propose_spend(self, value, beneficiary, kp_member):

        treasury_payload = self.substrate.compose_call(
            call_module='Treasury',
            call_function='propose_spend',
            call_params={
                'value': value*TOKEN_NUM_BASE_DEV,
                'beneficiary': beneficiary.ss58_address
            })

        call = self.substrate.compose_call(
            call_module='Council',
            call_function='propose',
            call_params={
                'threshold': 2,
                'proposal': treasury_payload.value,
                'length_bound': LENGTH_BOND
            })

        nonce = self.substrate.get_account_nonce(kp_member.ss58_address)
        extrinsic = self.substrate.create_signed_extrinsic(
            call=call,
            keypair=kp_member,
            era={'period': 64},
            nonce=nonce
        )

        receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        for event in self.substrate.get_events(receipt.block_hash):
            if event.value['event_id'] == 'Proposed':
                print(event.value['attributes'])
                pi = event.value['attributes']['proposal_index']
                ph = event.value['attributes']['proposal_hash']

        show_extrinsic(receipt, 'propose_spend')
        return (pi, ph)

    def approve_proposal_test(self):

        proposal_index = None
        proposal_hash = None

        # submit a proposal
        proposal_index, proposal_hash = self.propose_spend(AMOUNT,
                                                           KP_BENEFICIARY,
                                                           KP_USER)

        # To submit votes by all council member to APPORVE the motion
        receipt = cast_vote(self.substrate, KP_USER, proposal_hash, proposal_index, True)
        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        receipt = cast_vote(self.substrate, KP_COUNCIL_FIRST_MEMBER, proposal_hash,
                            proposal_index,
                            True)
        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        receipt = cast_vote(self.substrate, KP_COUNCIL_SECOND_MEMBER, proposal_hash,
                            proposal_index,
                            False)
        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        # To close voting processes
        receipt = close_vote(self.substrate, KP_COUNCIL_FIRST_MEMBER, proposal_hash,
                             proposal_index,
                             WEIGHT_BOND,
                             LENGTH_BOND)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')

    def reject_proposal_test(self):
        proposal_index = None
        proposal_hash = None

        # submit a proposal
        proposal_index, proposal_hash = self.propose_spend(AMOUNT,
                                                           KP_BENEFICIARY,
                                                           KP_USER)

        # To submit votes by all council member to REJECT the proposal
        receipt = cast_vote(self.substrate, KP_USER, proposal_hash,
                            proposal_index,
                            True)
        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        receipt = cast_vote(self.substrate, KP_COUNCIL_FIRST_MEMBER, proposal_hash,
                            proposal_index,
                            False)
        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        receipt = cast_vote(self.substrate, KP_COUNCIL_SECOND_MEMBER, proposal_hash,
                            proposal_index,
                            False)
        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')

        # To close voting processes
        receipt = close_vote(self.substrate, KP_COUNCIL_SECOND_MEMBER, proposal_hash,
                             proposal_index,
                             WEIGHT_BOND,
                             LENGTH_BOND)
        self.assertTrue(receipt.is_success, f'Extrinsic Failed: {receipt.error_message}')

    def treasury_rewards_test(self):

        # To get current block reward as configured in BlockReward.BlockIssueReward
        result = self.substrate.query('BlockReward', 'BlockIssueReward')
        block_reward = result.decode()
        print("Block reward:", block_reward)

        # To get treasury percentage in block reward
        # as configured in BlockReward.RewardDistributionConfigStorage
        result = self.substrate.query('BlockReward', 'RewardDistributionConfigStorage')
        treasury_percentage = ((result['treasury_percent']).decode()) / DIVISION_FACTOR
        print("Treasury percentage: ", '{:.2f}%'.format(treasury_percentage))

        # To get expected reward to be distributd to treasury
        expected_reward_dist_to_treasury = int(
                                        (treasury_percentage/100)*block_reward)
        print("Treasury expected reward:", expected_reward_dist_to_treasury)

        actual_reward_dist_to_treasury = 0

        # Examine events for most recent block
        for event in self.substrate.get_events():
            if event.value['event_id'] != 'Deposit':
                continue
            if event.value['attributes']['who'] != KP_TREASURY:
                continue
            actual_reward_dist_to_treasury = event.value['attributes']['amount']

        print("Treasury actual reward: ", actual_reward_dist_to_treasury)

        # In future, after we introduce the transaction fee
        # into the reward system, this equation will not works
        # and hence this test needs to be updated accordingly
        self.assertEqual(expected_reward_dist_to_treasury,
                         actual_reward_dist_to_treasury,
                         "Actual and expected reward distribution are not equal")

        print('✅ Reward distributed to treasury as expected')

    def batch_fund(self, batch, kp, amount):
        batch.compose_sudo_call('Balances', 'set_balance', {
            'who': kp.ss58_address,
            'new_free': amount,
            'new_reserved': 0
        })

    def test_tresury_approve(self):
        print('----Start of pallet_treasury_test!! ----')
        print()

        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        self.batch_fund(batch, KP_USER, TOTAL_AMOUNT)
        self.batch_fund(batch, KP_COUNCIL_FIRST_MEMBER, TOTAL_AMOUNT)
        self.batch_fund(batch, KP_COUNCIL_SECOND_MEMBER, TOTAL_AMOUNT)

        print("--set member test started---")
        council_members = [KP_USER.ss58_address,
                           KP_COUNCIL_FIRST_MEMBER.ss58_address,
                           KP_COUNCIL_SECOND_MEMBER.ss58_address]

        set_member_by_sudo(batch,
                           council_members,
                           KP_USER.ss58_address,
                           0,
                           KP_USER.ss58_address)
        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash, f'Extrinsic Failed: {bl_hash}')

        print("--set member test completed successfully!---")
        print()

        print("---proposal approval test started---")
        self.approve_proposal_test()
        print("---proposal approval test completed successfully---")
        print()

    def test_tresury_reject(self):
        print('----Start of pallet_treasury_test!! ----')
        print()

        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        self.batch_fund(batch, KP_USER, TOTAL_AMOUNT)
        self.batch_fund(batch, KP_COUNCIL_FIRST_MEMBER, TOTAL_AMOUNT)
        self.batch_fund(batch, KP_COUNCIL_SECOND_MEMBER, TOTAL_AMOUNT)

        print("--set member test started---")
        council_members = [KP_USER.ss58_address,
                           KP_COUNCIL_FIRST_MEMBER.ss58_address,
                           KP_COUNCIL_SECOND_MEMBER.ss58_address]

        set_member_by_sudo(batch,
                           council_members,
                           KP_USER.ss58_address,
                           0,
                           KP_USER.ss58_address)
        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash, f'Extrinsic Failed: {bl_hash}')

        print("---proposal rejection test started---")
        self.reject_proposal_test()
        print("---proposal rejection test completed successfully---")
        print()

    def test_treasury_others(self):
        print('----Start of pallet_treasury_test!! ----')
        print()

        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        self.batch_fund(batch, KP_USER, TOTAL_AMOUNT)
        self.batch_fund(batch, KP_COUNCIL_FIRST_MEMBER, TOTAL_AMOUNT)
        self.batch_fund(batch, KP_COUNCIL_SECOND_MEMBER, TOTAL_AMOUNT)

        print("--set member test started---")
        council_members = [KP_USER.ss58_address,
                           KP_COUNCIL_FIRST_MEMBER.ss58_address,
                           KP_COUNCIL_SECOND_MEMBER.ss58_address]

        set_member_by_sudo(batch,
                           council_members,
                           KP_USER.ss58_address,
                           0,
                           KP_USER.ss58_address)
        bl_hash = batch.execute_n_clear()
        self.assertTrue(bl_hash, f'Extrinsic Failed: {bl_hash}')

        print("---Spend test started---")
        receipt = spend(self.substrate, AMOUNT, KP_BENEFICIARY)
        self.assertTrue(receipt.is_success,
                        f'Extrinsic Failed: {receipt.error_message}' +
                        f'{self.substrate.get_events(receipt.block_hash)}')
        print("Spend test completed successfully")
        print()

        print("---Treasury reward distribution test started---")
        self.treasury_rewards_test()
        print("---Treasury reward distribution test completed successfully---")
        print()

        print('---- End of pallet_treasury_test!! ----')
