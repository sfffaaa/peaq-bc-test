from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL
from tools.utils import TOKEN_NUM_BASE

# Global Constants

# deinfe a conneciton with a peaq-network node
substrate = SubstrateInterface(
        url=WS_URL
    )

# accounts to carty out diffirent transactions
KP_SUDO = Keypair.create_from_uri('//Alice')
KP_COUNCIL_FIRST_MEMBER = Keypair.create_from_uri('//Bob')
KP_COUNCIL_SECOND_MEMBER = Keypair.create_from_uri('//Charlie')
KP_BENEFICIARY = Keypair.create_from_uri('//Dave')

WEIGHT_BOND = 10000000000
LENGTH_BOND = 1000000
AMOUNT = 1000

# To set members of the council
def set_members_test(members, kp_prime_member, old_count, kp_sudo):

    # add council members
    payload = substrate.compose_call(
        call_module='Council',
        call_function='set_members',
        call_params={
            'new_members': members,
            'prime': kp_sudo,
            'old_count': len(members)
        })

    call = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo',
        call_params={
            'call': payload.value,
        }
    )

    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=KP_SUDO,
        era={'period': 64},
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'setMembers')


def propose_spend(value, beneficiary, kp_member):

    treasury_payload = substrate.compose_call(
        call_module='Treasury',
        call_function='propose_spend',
        call_params={
            'value': value*TOKEN_NUM_BASE,
            'beneficiary': beneficiary.ss58_address
        })

    call = substrate.compose_call(
        call_module='Council',
        call_function='propose',
        call_params={
            'threshold': 2,
            'proposal': treasury_payload.value,
            'length_bound': LENGTH_BOND
        })

    nonce = substrate.get_account_nonce(kp_member.ss58_address)
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_member,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    for event in substrate.get_events(receipt.block_hash):
        if event.value['event_id'] == 'Proposed':
            pi = event.value['attributes'][1]
            ph = event.value['attributes'][2]

    show_extrinsic(receipt, 'propose_spend')
    return (pi, ph)


def cast_vote(proposal_hash, proposal_index, vote, kp_member):

    call = substrate.compose_call(
        call_module='Council',
        call_function='vote',
        call_params={
            'proposal': proposal_hash,
            'index': proposal_index,
            'approve': vote
        })

    nonce = substrate.get_account_nonce(kp_member.ss58_address)
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_member,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'vote casted')


def close_vote(proposal_hash, proposal_index, weight_bond,
               length_bond, kp_member):

    call = substrate.compose_call(
        call_module='Council',
        call_function='close',
        call_params={
            'proposal_hash': proposal_hash,
            'index': proposal_index,
            'proposal_weight_bound': weight_bond,
            'length_bound': length_bond

        })

    nonce = substrate.get_account_nonce(kp_member.ss58_address)
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=kp_member,
        era={'period': 64},
        nonce=nonce
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'closed voting processes')

def approve_proposal_test():

        proposal_index = None
        proposal_hash = None

        # submit a proposal
        proposal_index, proposal_hash = propose_spend(AMOUNT,
                                                      KP_BENEFICIARY,
                                                      KP_SUDO)

        # To submit votes by all council member to APPORVE the motion
        cast_vote(proposal_hash, 
                  proposal_index, 
                  True, 
                  KP_SUDO)

        cast_vote(proposal_hash,
                  proposal_index,
                  True,
                  KP_COUNCIL_FIRST_MEMBER)

        cast_vote(proposal_hash,
                  proposal_index,
                  False,
                  KP_COUNCIL_SECOND_MEMBER)

        # To close voting processes
        close_vote(proposal_hash,
                   proposal_index,
                   WEIGHT_BOND,
                   LENGTH_BOND,
                   KP_COUNCIL_FIRST_MEMBER)

def reject_proposal_test():

        proposal_index = None
        proposal_hash = None

        # submit a proposal
        proposal_index, proposal_hash = propose_spend(AMOUNT,
                                                      KP_BENEFICIARY,
                                                      KP_SUDO)

        # To submit votes by all council member to REJECT the proposal
        cast_vote(proposal_hash,
                  proposal_index,
                  True,
                  KP_SUDO)

        cast_vote(proposal_hash,
                  proposal_index,
                  False,
                  KP_COUNCIL_FIRST_MEMBER)

        cast_vote(proposal_hash,
                  proposal_index,
                  False,
                  KP_COUNCIL_SECOND_MEMBER)

        # To close voting processes
        close_vote(proposal_hash,
                   proposal_index,
                   WEIGHT_BOND,
                   LENGTH_BOND,
                   KP_COUNCIL_SECOND_MEMBER)


# To directly spend funds from treasury
def spend_test(value, beneficiary, kp_sudo):

    # add a spend extrinsic
    payload = substrate.compose_call(
        call_module='Treasury',
        call_function='spend',
        call_params={
            'amount': value*TOKEN_NUM_BASE,
            'beneficiary': beneficiary.ss58_address
        })

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
        era={'period': 64}
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'spend')


def pallet_treasury_test():

    print("---set members test started---")

    council_members = [KP_SUDO.ss58_address,
                       KP_COUNCIL_FIRST_MEMBER.ss58_address,
                       KP_COUNCIL_SECOND_MEMBER.ss58_address]   

    set_members_test(council_members,
                     KP_SUDO.ss58_address,
                     0,
                     KP_SUDO.ss58_address)
    print("--set member test completed successfully!---")
    print()

    print("---proposal approval test started---")
    approve_proposal_test()
    print("---proposal approval test completed successfully---")
    print()

    print("---proposal rejection test started---")
    reject_proposal_test()
    print("---proposal rejection test completed successfully---")
    print()
    
    print("---Spend test started---")
    spend_test(AMOUNT, KP_BENEFICIARY, KP_SUDO)
    print("Spend test completed successfully")
