import time
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, TOKEN_NUM_BASE_DEV
from tools.utils import check_and_fund_account

# Assumptions
# 1. Alice is the sudo key


# Global Constants

# deinfe a conneciton with a peaq-network node
substrate = SubstrateInterface(
        url=WS_URL
    )

# accounts to carty out diffirent transactions
KP_SUDO = Keypair.create_from_uri('//Alice')
KP_SOURCE = Keypair.create_from_uri('//Bob')
KP_TARGET_FIRST = Keypair.create_from_uri('//Dave')
KP_TARGET_SECOND = Keypair.create_from_uri('//Eve')

def vested_transfer_test(kp_soucre, kp_target, schedule):

    print('--Start of vested_transfer_test--')
    print()

    call = substrate.compose_call(
        call_module = 'Vesting', 
        call_function = 'vested_transfer',
        call_params = {
            'target':kp_target.ss58_address,
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

    print()
    print('--End of vested_transfer_test--')
    print()

def force_vested_transfer_test(kp_source, kp_target, kp_sudo, schedule):

    print('--Start of forced_vested_transfer_test--')
    print()   

    payload= substrate.compose_call(
        call_module = 'Vesting', 
        call_function = 'force_vested_transfer',
        call_params = {
            'source': kp_source.ss58_address,
            'target':kp_target.ss58_address,
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

    print()
    print('--End of forced_vested_transfer_test--')
    print()    


def vest_test(kp_source):

    print('--Start of vest_test--')
    print()

    call = substrate.compose_call(
        call_module = 'Vesting', 
        call_function = 'vest',        
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

    print()
    print('--End of vest_test--')
    print()

def vest_other_test(kp_source, kp_sudo):

    print('--Start of vest_other_test--')
    print()

    call = substrate.compose_call(
        call_module = 'Vesting', 
        call_function = 'vest_other',    
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

    print()
    print('--End of vest_other_test--')
    print()       


def merge_schedule_test():

    print('--Start of merge_schedule_test--')
    print()

    print('--End of merge_schedule_test--')
    print()   

def pallet_vesting_test():
    
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


    block_header=substrate.get_block_header()    
    current_block_number= int(block_header['header']['number'])
    starting_block_number = current_block_number+10
    print("Current Block: ", current_block_number)
    print("Starting Block: ", starting_block_number)        
    
    schedule={'locked':100*TOKEN_NUM_BASE_DEV, 'per_block':10*TOKEN_NUM_BASE_DEV, 'starting_block':starting_block_number}   

    vested_transfer_test(
                            KP_SUDO,
                            KP_TARGET_FIRST, 
                            schedule        
    )

    force_vested_transfer_test(
                                KP_SOURCE,
                                KP_TARGET_SECOND,
                                KP_SUDO,
                                schedule                             
    )

    while starting_block_number>current_block_number:                
        block_header=substrate.get_block_header()    
        current_block_number= int(block_header['header']['number'])    
        print("Current Block: ", current_block_number)           
        time.sleep( (starting_block_number-current_block_number) * 12)    
   
    vest_test(KP_TARGET_FIRST )

    vest_other_test(KP_TARGET_SECOND, KP_SUDO)    
    
    merge_schedule_test()

    print()
    print('----End of pallet_vesting_test!! ----')
    print()
    
