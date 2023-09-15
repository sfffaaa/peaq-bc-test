import math
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, TOKEN_NUM_BASE_DEV, KP_GLOBAL_SUDO
from tools.utils import get_account_balance_locked
from peaq.utils import get_account_balance
from peaq.sudo_extrinsic import funds
from peaq.utils import wait_for_n_blocks
from tools.payload import sudo_call_compose, sudo_extrinsic_send, user_extrinsic_send
import unittest

# Assumptions
# 1. Alice is the sudo key
# 2. Parachain block generation time is 12 Secs

# Global Constants
# deinfe a conneciton with a peaq-network node
# Global constants
TRANSFER_AMOUNT = 100 * TOKEN_NUM_BASE_DEV
PER_BLOCK_AMOUNT = 20 * TOKEN_NUM_BASE_DEV
NO_OF_BLOCKS_TO_WAIT = math.ceil(TRANSFER_AMOUNT / PER_BLOCK_AMOUNT) + 1


# Schedule transfer of some amount from a souce to target account
@user_extrinsic_send
def vested_transfer(substrate, kp_soucre, kp_target, schedule):
    return substrate.compose_call(
        call_module='Vesting',
        call_function='vested_transfer',
        call_params={
            'target': kp_target.ss58_address,
            'schedule': schedule
        }
    )


# transfer of funds that were previouls scheduled to be released
@user_extrinsic_send
def vest(substrate, kp_source):
    return substrate.compose_call(
        call_module='Vesting',
        call_function='vest',
    )


# Forced Schedule transfer of some amount from a souce to target account
@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def force_vested_transfer(substrate, kp_source, kp_target, schedule):
    return substrate.compose_call(
        call_module='Vesting',
        call_function='force_vested_transfer',
        call_params={
            'source': kp_source.ss58_address,
            'target': kp_target.ss58_address,
            'schedule': schedule
        }
    )


# actual transfer of funds that were previouls scheduled to be released
@user_extrinsic_send
def vest_other(substrate, kp_user, kp_source):
    return substrate.compose_call(
        call_module='Vesting',
        call_function='vest_other',
        call_params={
            'target': kp_source.ss58_address
        }
    )


# To merge two schedules  into one
@user_extrinsic_send
def merge_schedules(substrate, kp_target,
                    index_of_first_schedule,
                    index_of_second_schedule):
    return substrate.compose_call(
        call_module='Vesting',
        call_function='merge_schedules',
        call_params={
            'schedule1_index': index_of_first_schedule,
            'schedule2_index': index_of_second_schedule
        }
    )


def get_schedule_index(substrate, kp_target):
    result = substrate.query("Vesting", "Vesting", [kp_target.ss58_address])
    return len((result.value)) - 1


class TestPalletVesting(unittest.TestCase):
    def setUp(self):
        self._substrate = SubstrateInterface(url=WS_URL)
        self._kp_user = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        self._kp_source = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        self._kp_target = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        self._kp_target_second = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())

    def vested_transfer_test(self, substrate, kp_user, kp_target):

        free_bal_before_transfer = \
            get_account_balance(substrate, kp_target.ss58_address)

        block_header = substrate.get_block_header()

        current_block_number = int(block_header['header']['number'])
        starting_block_number = current_block_number + 5

        schedule = {
            'locked': TRANSFER_AMOUNT,
            'per_block': PER_BLOCK_AMOUNT,
            'starting_block': starting_block_number
        }

        print("Current Block: ", current_block_number)
        print("Starting Block Number of schedule: ",
              starting_block_number)

        print("Free Balance before vested transfer:",
              free_bal_before_transfer)
        print("Vested transer amount: ", TRANSFER_AMOUNT)

        receipt = vested_transfer(substrate, kp_user, kp_target, schedule)
        self.assertTrue(receipt.is_success, f'vested transfer failed {receipt.error_message}')

        free_bal_after_transfer = get_account_balance(substrate, kp_target.ss58_address)

        print("Free Balance after vested transfer:",
              free_bal_after_transfer)

        # Free balance after vested transfer should be equal to the sum of
        # free balance before transer and vested amount transfer
        self.assertEqual(free_bal_after_transfer,
                         free_bal_before_transfer + TRANSFER_AMOUNT,
                         "Vested tranfer amount not added to destination account")

        # Vest all the funds
        # Wait till the time ending block number is fianlized
        print("We need to wait till finzlization of block: ",
              starting_block_number + NO_OF_BLOCKS_TO_WAIT)

        wait_for_n_blocks(substrate, NO_OF_BLOCKS_TO_WAIT)

        locked_bal_before_vest = \
            get_account_balance_locked(substrate, kp_target.ss58_address)

        print("Locked balance before vest: ", locked_bal_before_vest)

        receipt = vest(substrate, kp_target)
        self.assertTrue(receipt.is_success, f'Vesting failed {receipt.error_message}')

        locked_bal_after_vest = \
            get_account_balance_locked(substrate, kp_target.ss58_address)

        print("Locked balance after vest: ", locked_bal_after_vest)

        # All the vested amount is released
        self.assertEqual(locked_bal_before_vest - locked_bal_after_vest, TRANSFER_AMOUNT,
                         'Versting amount still not released')

    def forced_vested_transfer_test(self, substrate, kp_user, kp_source, kp_target):

        free_bal_before_transfer = get_account_balance(substrate, kp_target.ss58_address)

        block_header = substrate.get_block_header()

        current_block_number = int(block_header['header']['number'])
        starting_block_number = current_block_number + 5

        schedule = {
            'locked': TRANSFER_AMOUNT,
            'per_block': PER_BLOCK_AMOUNT,
            'starting_block': starting_block_number
        }

        print("Current Block: ", current_block_number)
        print("Starting Block Number of schedule: ",
              starting_block_number)

        print("Free Balance before forced vested transfer:",
              free_bal_before_transfer)
        print("Vested transer amount: ", TRANSFER_AMOUNT)

        receipt = force_vested_transfer(substrate, kp_source, kp_target, schedule)
        self.assertTrue(receipt.is_success, f'fail force_vested_transfer {receipt.error_message}')

        free_bal_after_transfer = get_account_balance(substrate, kp_target.ss58_address)

        print("Free Balance after forced vested transfer:", free_bal_after_transfer)

        # Free balance after forced vested transfer should be equal to the sum of
        # free balance before forced vested transer and vested amount transfer
        self.assertEqual(free_bal_after_transfer, free_bal_before_transfer + TRANSFER_AMOUNT,
                         'Vested tranfer amount not added to destination account')

        # Vest all the funds through vest_others
        print("We need to wait till finzlization of block: ", starting_block_number + NO_OF_BLOCKS_TO_WAIT)

        wait_for_n_blocks(substrate, NO_OF_BLOCKS_TO_WAIT)

        locked_bal_before_vest = get_account_balance_locked(substrate, kp_target.ss58_address)

        print("Locked balance before vest: ", locked_bal_before_vest)

        receipt = vest_other(substrate, kp_user, kp_target)
        self.assertTrue(receipt.is_success, f'Vesting failed with error: {receipt.error_message}')

        locked_bal_after_vest = get_account_balance_locked(substrate, kp_target.ss58_address)

        print("Locked balance after vest: ", locked_bal_after_vest)
        # All the vested amount is released
        self.assertEqual(locked_bal_before_vest - locked_bal_after_vest, TRANSFER_AMOUNT,
                         'Vesting amount still not released')

    def merge_schedule_test(self, substrate, kp_source, kp_target_second):

        block_header = substrate.get_block_header()
        current_block_number = int(block_header['header']['number'])

        first_starting_block_number = current_block_number + 10
        second_starting_block_number = current_block_number + 20

        print("Current Block: ", current_block_number)
        print("Starting Block Number of first schedule: ", first_starting_block_number)
        print("Starting Block Number of second schedule: ", second_starting_block_number)
        print("New schedule should start at block number:",
              max(first_starting_block_number, second_starting_block_number))

        first_schedule = {'locked': 100 * TOKEN_NUM_BASE_DEV,
                          'per_block': 10 * TOKEN_NUM_BASE_DEV,
                          'starting_block': first_starting_block_number}
        second_schedule = {'locked': 200 * TOKEN_NUM_BASE_DEV,
                           'per_block': 20 * TOKEN_NUM_BASE_DEV,
                           'starting_block': second_starting_block_number}

        print("First vested trasnfer")
        receipt = vested_transfer(substrate, kp_source, kp_target_second, first_schedule)
        self.assertTrue(receipt.is_success, f'Vested transfer failed with error: {receipt.error_message}')
        index_of_first_schedule = get_schedule_index(substrate, kp_target_second)

        print("Seond vested trasnfer")
        receipt = vested_transfer(substrate, kp_source, kp_target_second, second_schedule)
        self.assertTrue(receipt.is_success, f'Vested transfer failed with error: {receipt.error_message}')
        index_of_second_schedule = get_schedule_index(substrate, kp_target_second)

        # First and second schedules will be merged
        print("Merge Schedule for first and second vested transfer")
        receipt = merge_schedules(substrate, kp_target_second,
                                  index_of_first_schedule, index_of_second_schedule)
        self.assertTrue(receipt.is_success, f'Merge schedule failed with error: {receipt.error_message}')
        index_of_merged_schedule = get_schedule_index(substrate, kp_target_second)

        result = substrate.query("Vesting",
                                 "Vesting",
                                 [kp_target_second.ss58_address])

        merged_locked = int(str(result[index_of_merged_schedule]
                            ['locked']))
        merged_per_block = int(str(result[index_of_merged_schedule]
                               ['per_block']))
        merged_starting_block = int(str(result[index_of_merged_schedule]
                                    ['starting_block']))

        self.assertEqual(merged_locked,
                         int(str(first_schedule['locked'])) + int(second_schedule['locked']),
                         'merged schedule locked funds is not eaqul to ' +
                         'sum of first and second schedule locked funds')

        self.assertEqual(merged_per_block,
                         int(str(first_schedule['per_block'])) + int(second_schedule['per_block']),
                         'merged schedule per block funds is not eaqul to ' +
                         'sum of first and second schedule per block funds')

        self.assertEqual(merged_starting_block,
                         max(int(str(first_schedule['starting_block'])), int(str(second_schedule['starting_block']))),
                         'Starting block of merge schedule is not correct')

    def test_pallet_vesting(self):
        kp_user = self._kp_user
        kp_source = self._kp_source
        kp_target = self._kp_target
        kp_target_second = self._kp_target_second
        substrate = self._substrate

        # TODO
        # In current code structure
        # Vest test is dependent on vest_transer
        # vest_other is dependent on forced_vest_transfer
        # In future, the code structure will be improved so that
        # there may be no such dependencies and each test is
        # performed independend of others

        # To fund accounts, if sufficient  funds are not available
        funds(substrate,
              KP_GLOBAL_SUDO,
              [kp_user.ss58_address, kp_source.ss58_address, kp_target.ss58_address, kp_target_second.ss58_address],
              1000 * TOKEN_NUM_BASE_DEV)

        self.vested_transfer_test(substrate, kp_user, kp_target)
        self.forced_vested_transfer_test(substrate, kp_user, kp_source, kp_target)
        self.merge_schedule_test(substrate, kp_source, kp_target_second)
