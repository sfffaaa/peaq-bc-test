import time
import math
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, TOKEN_NUM_BASE_DEV
from tools.utils import get_account_balance, get_account_balance_locked
from tools.utils import check_and_fund_account

# Assumptions
# 1. Alice is the sudo key
# 2. Parachain block generation time is 12 Secs

# Global Constants
# deinfe a conneciton with a peaq-network node
substrate = SubstrateInterface(
        url=WS_URL
    )

# Global constants
KP_SUDO = Keypair.create_from_uri('//Alice')
KP_SOURCE = Keypair.create_from_uri('//Bob')
KP_TARGET = Keypair.create_from_uri('//Dave')
KP_TARGET_SECOND = Keypair.create_from_uri('//Eve')
TRANSFER_AMOUNT = 100*TOKEN_NUM_BASE_DEV
PER_BLOCK_AMOUNT = 20*TOKEN_NUM_BASE_DEV
NO_OF_BLOCKS_TO_WAIT = math.ceil(TRANSFER_AMOUNT / PER_BLOCK_AMOUNT)


# Schedule transfer of some amount from a souce to target account
def vested_transfer(kp_soucre, kp_target, schedule):

    call = substrate.compose_call(
        call_module='Vesting',
        call_function='vested_transfer',
        call_params={
            'target': kp_target.ss58_address,
            'schedule': schedule
        }
    )
    print(f'call.value: {call.value}')
    print(f'call.data: {str(call.data)}')
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_soucre,
        era={'period': 64},
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'vestedTranser')


# transfer of funds that were previouls scheduled to be released
def vest(kp_source):

    call = substrate.compose_call(
        call_module='Vesting',
        call_function='vest',
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_source,
        era={'period': 64},
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'vest')


# Forced Schedule transfer of some amount from a souce to target account
def force_vested_transfer(kp_source, kp_target, kp_sudo, schedule):

    payload = substrate.compose_call(
        call_module='Vesting',
        call_function='force_vested_transfer',
        call_params={
            'source': kp_source.ss58_address,
            'target': kp_target.ss58_address,
            'schedule': schedule
        }
    )

    call = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo',
        call_params={
            'call': payload.value,
        }
    )
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'forced_vested_transer')


# actual transfer of funds that were previouls scheduled to be released
def vest_other(kp_source, kp_sudo):

    call = substrate.compose_call(
        call_module='Vesting',
        call_function='vest_other',
        call_params={
            'target': kp_source.ss58_address
        }
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_sudo,
        era={'period': 64},
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'vest_other')


# To merge two schedules  into one
def merge_schedules(kp_target,
                    index_of_first_schedule,
                    index_of_second_schedule):

    call = substrate.compose_call(
        call_module='Vesting',
        call_function='merge_schedules',
        call_params={
            'schedule1_index': index_of_first_schedule,
            'schedule2_index': index_of_second_schedule
        }
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_target,
        era={'period': 64},
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'merge_schedule')


def get_schedule_index(kp_target):

    result = substrate.query("Vesting", "Vesting", [kp_target.ss58_address])
    return len((result.value))-1


def vested_transfer_test():

    free_bal_before_transfer = \
        get_account_balance(substrate, KP_TARGET.ss58_address)

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

    vested_transfer(KP_SUDO,
                    KP_TARGET,
                    schedule)

    free_bal_after_transfer = \
        get_account_balance(substrate, KP_TARGET.ss58_address)

    print("Free Balance after vested transfer:",
          free_bal_after_transfer)

    # Free balance after vested transfer should be equal to the sum of
    # free balance before transer and vested amount transfer
    assert free_bal_after_transfer == \
        free_bal_before_transfer+TRANSFER_AMOUNT, \
        "Vested tranfer amount not added to destination account"

    # Vest all the funds
    # Wait till the time ending block number is fianlized
    print("We need to wait till finzlization of block: ",
          starting_block_number+NO_OF_BLOCKS_TO_WAIT)

    while (starting_block_number+NO_OF_BLOCKS_TO_WAIT) >= \
            current_block_number:

        block_header = substrate.get_block_header()
        current_block_number = int(block_header['header']['number'])
        print("Current Block: ", current_block_number)
        time.sleep((starting_block_number + NO_OF_BLOCKS_TO_WAIT
                    - current_block_number+1)*12)

    locked_bal_before_vest = \
        get_account_balance_locked(substrate, KP_TARGET.ss58_address)

    print("Locked balance before vest: ", locked_bal_before_vest)

    vest(KP_TARGET)

    locked_bal_after_vest = \
        get_account_balance_locked(substrate, KP_TARGET.ss58_address)

    print("Locked balance after vest: ", locked_bal_after_vest)

    # All the vested amount is released
    assert locked_bal_before_vest-locked_bal_after_vest == TRANSFER_AMOUNT, \
        "Vested amount still not released"


def forced_vested_transfer_test():

    free_bal_before_transfer = \
        get_account_balance(substrate, KP_TARGET.ss58_address)

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

    force_vested_transfer(KP_SOURCE,
                          KP_TARGET,
                          KP_SUDO,
                          schedule)

    free_bal_after_transfer = \
        get_account_balance(substrate, KP_TARGET.ss58_address)

    print("Free Balance after forced vested transfer:",
          free_bal_after_transfer)

    # Free balance after forced vested transfer should be equal to the sum of
    # free balance before forced vested transer and vested amount transfer
    assert free_bal_after_transfer == \
        free_bal_before_transfer+TRANSFER_AMOUNT, \
        "Vested tranfer amount not added to destination account"

    # Vest all the funds through vest_others
    print("We need to wait till finzlization of block: ",
          starting_block_number+NO_OF_BLOCKS_TO_WAIT)

    while (starting_block_number+NO_OF_BLOCKS_TO_WAIT) >= \
            current_block_number:

        block_header = substrate.get_block_header()
        current_block_number = int(block_header['header']['number'])
        print("Current Block: ", current_block_number)
        time.sleep((starting_block_number + NO_OF_BLOCKS_TO_WAIT
                   - current_block_number+1)*12)

    locked_bal_before_vest = \
        get_account_balance_locked(substrate, KP_TARGET.ss58_address)

    print("Locked balance before vest: ", locked_bal_before_vest)

    vest_other(KP_TARGET,
               KP_SUDO)

    locked_bal_after_vest = \
        get_account_balance_locked(substrate, KP_TARGET.ss58_address)

    print("Locked balance after vest: ", locked_bal_after_vest)

    # All the vested amount is released
    assert locked_bal_before_vest-locked_bal_after_vest == TRANSFER_AMOUNT, \
        "Vested amount still not released"


def merge_schedule_test():

    block_header = substrate.get_block_header()
    current_block_number = int(block_header['header']['number'])

    first_starting_block_number = current_block_number + 10
    second_starting_block_number = current_block_number + 20

    print("Current Block: ", current_block_number)
    print("Starting Block Number of first schedule: ",
          first_starting_block_number)
    print("Starting Block Number of second schedule: ",
          second_starting_block_number)
    print("New schedule should start at block number:",
          max(first_starting_block_number, second_starting_block_number))

    first_schedule = {'locked': 100 * TOKEN_NUM_BASE_DEV,
                      'per_block': 10 * TOKEN_NUM_BASE_DEV,
                      'starting_block': first_starting_block_number}
    second_schedule = {'locked': 200 * TOKEN_NUM_BASE_DEV,
                       'per_block': 20 * TOKEN_NUM_BASE_DEV,
                       'starting_block': second_starting_block_number}

    print("First vested trasnfer")
    vested_transfer(KP_SOURCE, KP_TARGET_SECOND, first_schedule)
    index_of_first_schedule = get_schedule_index(KP_TARGET_SECOND)

    print("Seond vested trasnfer")
    vested_transfer(KP_SOURCE, KP_TARGET_SECOND, second_schedule)
    index_of_second_schedule = get_schedule_index(KP_TARGET_SECOND)

    # First and second schedules will be merged
    print("Merge Schedule for first and second vested transfer")
    merge_schedules(KP_TARGET_SECOND,
                    index_of_first_schedule,
                    index_of_second_schedule)
    index_of_merged_schedule = get_schedule_index(KP_TARGET_SECOND)

    result = substrate.query("Vesting",
                             "Vesting",
                             [KP_TARGET_SECOND.ss58_address])

    merged_locked = int(str(result[index_of_merged_schedule]
                        ['locked']))
    merged_per_block = int(str(result[index_of_merged_schedule]
                           ['per_block']))
    merged_starting_block = int(str(result[index_of_merged_schedule]
                                ['starting_block']))

    assert merged_locked == int(str(first_schedule['locked'])) + \
        int(second_schedule['locked']), \
        "merged schedule locked funds is not eaqul \
          to sum of first and second schedule locked funds"

    assert merged_per_block == int(str(first_schedule['per_block'])) + \
        int(second_schedule['per_block']), \
        "merged schedule per block funds is not eaqul \
          to sum of first and second schedule per block funds"

    print()
    assert merged_starting_block == \
        max(int(str(first_schedule['starting_block'])),
            int(str(second_schedule['starting_block']))), \
        "Starting block of merge schedule is not correct"


def pallet_vesting_test():

    # TODO
    # In current code structure
    # Vest test is dependent on vest_transer
    # vest_other is dependent on forced_vest_transfer
    # In future, the code structure will be improved so that
    # there may be no such dependencies and each test is
    # performed independend of others

    print()
    print('----Start of pallet_vesting_test!! ----')
    print()

    # To fund accounts, if sufficient  funds are not available
    check_and_fund_account(substrate,
                           KP_SUDO,
                           1000 * TOKEN_NUM_BASE_DEV,
                           1000 * TOKEN_NUM_BASE_DEV)

    check_and_fund_account(substrate,
                           KP_SOURCE,
                           1000 * TOKEN_NUM_BASE_DEV,
                           1000 * TOKEN_NUM_BASE_DEV,)

    print("---vested transfer test started---")
    vested_transfer_test()
    print("---vested transfer test completed successfully---")
    print()

    print("---forced vested transfer test started---")
    forced_vested_transfer_test()
    print("---forced vested transfer test completed successfully---")
    print()

    print("---merge schedule test started---")
    merge_schedule_test()
    print("---merge schedule test completed successfully---")
    print()

    print('----End of pallet_vesting_test!! ----')
    print()
