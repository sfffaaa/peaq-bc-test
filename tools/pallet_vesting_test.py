import time
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, TOKEN_NUM_BASE_DEV
from tools.utils import check_and_fund_account

# Assumptions
# 1. Alice is the sudo key
# 2. Parachain block generation time is 12 Secs


# Global Constants

# deinfe a conneciton with a peaq-network node
substrate = SubstrateInterface(
        url=WS_URL
    )

# accounts to carty out diffirent transactions
KP_SUDO = Keypair.create_from_uri('//Alice')
KP_SOURCE = Keypair.create_from_uri('//Bob')
KP_TARGET_FIRST = Keypair.create_from_uri('//Charlie')
KP_TARGET_SECOND = Keypair.create_from_uri('//Dave')
KP_TARGET_THIRD = Keypair.create_from_uri('//Eve')


# Schedule transfer of some amount from a souce to target account
def vested_transfer_test(kp_soucre, kp_target, schedule):

    call = substrate.compose_call(
        call_module='Vesting',
        call_function='vested_transfer',
        call_params={
            'target': kp_target.ss58_address,
            'schedule': schedule
        }
    )

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


# Forced Schedule transfer of some amount from a souce to target account
def force_vested_transfer_test(kp_source, kp_target, kp_sudo, schedule):

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


# Actual transfer of funds that were previouls scheduled to be released
def vest_test(kp_source):

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


# Force actual transfer of funds that were previouls scheduled to be released
def vest_other_test(kp_source, kp_sudo):

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


# To merge two scheduled transfed into one
def merge_schedules_test(kp_source, kp_target, kp_sudo,
                         first_schedule, second_schedule):

    print("First vested trasnfer")
    vested_transfer_test(kp_source, kp_target, first_schedule)

    print("Seond vested trasnfer")
    vested_transfer_test(kp_source, kp_target, second_schedule)

    print("Merge Schedule for first and second vested transfer")

    call = substrate.compose_call(
        call_module='Vesting',
        call_function='merge_schedules',
        call_params={
            'schedule1_index': 0,
            'schedule2_index': 1
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


def pallet_vesting_test():

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

    block_header = substrate.get_block_header()
    current_block_number = int(block_header['header']['number'])

    first_starting_block_number = current_block_number+10
    second_starting_block_number = current_block_number+10

    print("Current Block: ", current_block_number)

    # Starting block numbers of transfer schedules
    print("Starting Block Number of first schedule: ",
          first_starting_block_number)
    print("Starting Block Number of second schedule: ",
          second_starting_block_number)

    first_schedule = {'locked': 100*TOKEN_NUM_BASE_DEV,
                      'per_block': 10*TOKEN_NUM_BASE_DEV,
                      'starting_block': first_starting_block_number}
    second_schedule = {'locked': 200*TOKEN_NUM_BASE_DEV,
                       'per_block': 20*TOKEN_NUM_BASE_DEV,
                       'starting_block': second_starting_block_number}

    vested_transfer_amount = 0
    free_bal_before_vested_transfer = 0
    free_bal_after_vested_transfer = 0
    locked_bal_before_vest = 0
    locked_bal_after_vest = 0

    print()
    print('--Start of vested_transfer_test--')
    print()

    vested_transfe_amount = int(first_schedule['locked'])

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_FIRST.ss58_address])
    free_bal_before_vested_transfer = int(result.value['data']['free'])

    print("Free Balance before vested transfer:",
          free_bal_before_vested_transfer)
    print("Vested transer amount: ", vested_transfe_amount)

    vested_transfer_test(KP_SUDO,
                         KP_TARGET_FIRST,
                         first_schedule)

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_FIRST.ss58_address])
    free_bal_after_vested_transfer = int(result.value['data']['free'])

    print("Free Balance after vested transfer:",
          free_bal_after_vested_transfer)

    # Free balance after vested transfer should be equal to the sum of
    # free balance before transer and vested amount transfer
    assert free_bal_after_vested_transfer == \
        free_bal_before_vested_transfer+vested_transfe_amount, \
        "Vested tranfer amount not added to destination account"

    print()
    print('--End of vested_transfer_test--')
    print()

    print('--Start of forced_vested_transfer_test--')
    print()

    vested_transfe_amount = int(second_schedule['locked'])

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_SECOND.ss58_address])
    free_bal_before_vested_transfer = int(result.value['data']['free'])

    print("Free Balance before vested transfer:",
          free_bal_before_vested_transfer)
    print("Vested transer amount: ", vested_transfe_amount)

    force_vested_transfer_test(
                                KP_SOURCE,
                                KP_TARGET_SECOND,
                                KP_SUDO,
                                second_schedule
    )

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_SECOND.ss58_address])
    free_bal_after_vested_transfer = int(result.value['data']['free'])

    print("Free Balance after vested transfer:",
          free_bal_after_vested_transfer)

    # Free balance after foreced vested transfer should be equal to the sum of
    # free balance before forced vested transer and vested amount transfer
    assert free_bal_after_vested_transfer == \
        free_bal_before_vested_transfer+vested_transfe_amount, \
        "Vested tranfer amount not added to destination account"

    print()
    print('--End of forced_vested_transfer_test--')
    print()

    # Wait till the time staring block number is finalized
    print("We need to wait till finzlization of block: ",
          max(first_starting_block_number, second_starting_block_number))

    while max(first_starting_block_number, second_starting_block_number) \
            > current_block_number:

        block_header = substrate.get_block_header()
        current_block_number = int(block_header['header']['number'])
        print("Current Block: ", current_block_number)
        time.sleep((max(first_starting_block_number,
                        second_starting_block_number)
                   - current_block_number+1)*12)

    print('--Start of vest_test--')
    print()

    vested_transfe_amount = int(first_schedule['locked'])

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_FIRST.ss58_address])
    locked_bal_before_vest = int(result.value['data']['misc_frozen'])

    print("Locked balance before vest: ", locked_bal_before_vest)
    print("Vested transer amount: ", vested_transfe_amount)

    vest_test(KP_TARGET_FIRST)

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_FIRST.ss58_address])
    locked_bal_after_vest = int(result.value['data']['misc_frozen'])

    print("Locked balance after vest: ", locked_bal_after_vest)

    # Lock balance after vest must be less than locked balance before vest
    # We can not make an exact comaparison here, since se do not know if
    # there are some other vested_transfer amount avaiable in the same acccount
    assert locked_bal_before_vest > locked_bal_after_vest, \
        "Vested amount still not released"

    print()
    print('--End of vest_test--')
    print()

    print('--Start of vest_other_test--')
    print()

    vested_transfe_amount = int(second_schedule['locked'])

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_SECOND.ss58_address])
    locked_bal_before_vest = int(result.value['data']['misc_frozen'])

    print("Locked balance before vest: ", locked_bal_before_vest)
    print("Vested transer amount: ", vested_transfe_amount)

    vest_other_test(KP_TARGET_SECOND, KP_SUDO)

    result = substrate.query('System',
                             'Account',
                             [KP_TARGET_SECOND.ss58_address])
    locked_bal_after_vest = int(result.value['data']['misc_frozen'])

    print("Locked balance after vest: ", locked_bal_after_vest)

    # Lock balance after vest must be less than locked balance before vest
    # We can not make an exact comaparison here, since se do not know if
    # there are some other vested_transfer amount avaiable in the same acccount
    assert locked_bal_before_vest > locked_bal_after_vest, \
        "Vested amount still not released"

    print()
    print('--End of vest_other_test--')
    print()

    print('--Start of merge_schedules_test--')
    print()

    block_header = substrate.get_block_header()
    current_block_number = int(block_header['header']['number'])
    first_starting_block_number = current_block_number+10
    second_starting_block_number = current_block_number+20
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

    # First and second schedules will be merged
    # in one schedule
    merge_schedules_test(KP_SOURCE,
                         KP_TARGET_THIRD,
                         KP_SUDO,
                         first_schedule,
                         second_schedule)

    print()
    print('--End of merge_schedules_test--')
    print()

    print('----End of pallet_vesting_test!! ----')
    print()
