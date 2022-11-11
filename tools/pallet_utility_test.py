import sys
sys.path.append('./')
from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL, TOKEN_NUM_BASE,transfer
from tools.two_address_substrate_with_extrinsic import show_account


#The purpose of these tests is to test utility pallet functionality

substrate = SubstrateInterface (
        url=WS_URL
    )

#source account
kp_src = Keypair.create_from_uri('//Alice')
#destination account
kp_dst=Keypair.create_from_uri('//Charlie')

#One vaid and one invalid transaciton will added to pallet::utility::batch for execution
# The restul of valid transaction will not be reverted due to an invalid transaton int batch      
def pallet_utility_batch_test():
    
    print('---- pallet_utility_batch_test!! ----')
    print('---- ------------------------------- -----')   
    print() 
    

    print("Account balances before transactions:")
    bal_src_before=show_account(substrate, kp_src.ss58_address, "Source")  
    bal_dst_before=show_account(substrate, kp_dst.ss58_address, "Destination")  
        
     
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    amount_to_be_transfered=1
    
    #first valid transaciton
    payload_first = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered *TOKEN_NUM_BASE
        })

    #Second invalid transaciton
    payload_second = substrate.compose_call(
        call_module='Balances',
        call_function='force_transfer',
        call_params={
            'source': kp_src.ss58_address, 
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered  * TOKEN_NUM_BASE
        })

    batch = substrate.compose_call(
        call_module='Utility',
        call_function='batch',
        call_params={
            'calls': [payload_first.value, payload_second.value],
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=batch,
        keypair= kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
            
    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError
    
    print("Account balances after transactions:")
    bal_src_after=show_account(substrate, kp_src.ss58_address, "Source")  
    bal_dst_after=show_account(substrate, kp_dst.ss58_address, "Destination")  

    show_extrinsic(receipt, 'batch')
    assert(bal_dst_before+(amount_to_be_transfered*TOKEN_NUM_BASE)==bal_dst_after)

#One vaid and one invalid transaciton will added to pallet::utility::batch_all for execution
# The restul of valid transaction will be reverted since batch_all execute the transactions atomically      
def pallet_utility_batch_all_test():
    
    print('---- pallet_utility_batch_all_test!! ----')
    print('---- ------------------------------- -----')   
    print()     

    print("Account balances before transactions:")
    bal_src_before=show_account(substrate, kp_src.ss58_address, "Source")  
    bal_dst_before=show_account(substrate, kp_dst.ss58_address, "Destination")  
             
    nonce = substrate.get_account_nonce(kp_src.ss58_address)
    amount_to_be_transfered=1
    
    #first valid transaciton
    payload_first = substrate.compose_call(
        call_module='Balances',
        call_function='transfer',
        call_params={
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered *TOKEN_NUM_BASE
        })

    #Second invalid transaciton
    payload_second = substrate.compose_call(
        call_module='Balances',
        call_function='force_transfer',
        call_params={
            'source': kp_src.ss58_address, 
            'dest': kp_dst.ss58_address,
            'value': amount_to_be_transfered  * TOKEN_NUM_BASE
        })

    batch = substrate.compose_call(
        call_module='Utility',
        call_function='batch_all',
        call_params={
            'calls': [payload_first.value, payload_second.value],
        })

    extrinsic = substrate.create_signed_extrinsic(
        call=batch,
        keypair= kp_src,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
              
    print("Account balances after transactions:")
    bal_src_after=show_account(substrate, kp_src.ss58_address, "Source")  
    bal_dst_after=show_account(substrate, kp_dst.ss58_address, "Destination")  

    show_extrinsic(receipt, 'batch')
    #destination account balance shoud remain same before and after the transaction
    assert(bal_dst_before==bal_dst_after)



