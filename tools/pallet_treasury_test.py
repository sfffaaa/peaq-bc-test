from substrateinterface import SubstrateInterface, Keypair
from tools.utils import show_extrinsic, WS_URL

# deinfe a conneciton with a peaq-network node
substrate = SubstrateInterface(
        url=WS_URL
    )

proposal_index = None
proposal_hash = None
weight_bond = 10000000000
length_bond = 1000000
amount = 10

# accounts to carty out diffirent transactions
kp_council_first_member = Keypair.create_from_uri('//Alice')
kp_council_second_member = Keypair.create_from_uri('//Bob')
kp_council_third_member = Keypair.create_from_uri('//Charlie')
kp_beneficiary = Keypair.create_from_uri('//Dave')

council_members = [kp_council_first_member.ss58_address,
                   kp_council_second_member.ss58_address,
                   kp_council_third_member.ss58_address]


# To set members of the council
def set_members():

    print("set_members function called")

    # add council members
    payload = substrate.compose_call(
        call_module='Council',
        call_function='set_members',
        call_params={
            'new_members': council_members,
            'prime': None,
            'old_count': len(council_members)
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
        keypair=kp_council_first_member,
        era={'period': 64},
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'setMembers')


def propose_spend(p_value, p_beneficiary, p_kp_member):

    print("propose spend function called")

    treasury_payload = substrate.compose_call(
        call_module='Treasury',
        call_function='propose_spend',
        call_params={
            'value': p_value,
            'beneficiary': p_beneficiary.ss58_address
        })

    call = substrate.compose_call(
        call_module='Council',
        call_function='propose',
        call_params={
            'threshold': 2,
            'proposal': treasury_payload.value,
            'length_bound': length_bond
        })

    nonce = substrate.get_account_nonce(p_kp_member.ss58_address)
    extrinsic = substrate.create_signed_extrinsic(
        call=call,
        keypair=p_kp_member,
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


def cast_vote(p_proposal_hash, p_proposal_index, p_vote, kp_member):

    print("vote function called")

    call = substrate.compose_call(
        call_module='Council',
        call_function='vote',
        call_params={
            'proposal': p_proposal_hash,
            'index': p_proposal_index,
            'approve': p_vote
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


def close_vote(p_proposal_hash, p_proposal_index, p_weight_bond,
               p_length_bond, kp_member):

    print("close_vote function called")

    call = substrate.compose_call(
        call_module='Council',
        call_function='close',
        call_params={
            'proposal_hash': p_proposal_hash,
            'index': p_proposal_index,
            'proposal_weight_bound': p_weight_bond,
            'length_bound': p_length_bond

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


# To directly spend funds from treasury
def spend(p_value, p_beneficiary, p_kp_member):

    print("spend function called")

    # add a spend extrinsic
    payload = substrate.compose_call(
        call_module='Treasury',
        call_function='spend',
        call_params={
            'amount': p_value,
            'beneficiary': p_beneficiary.ss58_address
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
        keypair=kp_council_first_member,
        era={'period': 64}
    )

    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    if not receipt.is_success:
        print(substrate.get_events(receipt.block_hash))
        raise IOError

    show_extrinsic(receipt, 'spend')


def pallet_treasury_test():

    # To set members of council
    set_members()

    # To submit a proposal
    proposal_index, proposal_hash = propose_spend(amount, kp_beneficiary,
                                                  kp_council_first_member)
    print(proposal_index)
    print(proposal_hash)

    # To submit votes by all council member to APPORVE the motion with majority
    cast_vote(proposal_hash, proposal_index, True, kp_council_first_member)
    cast_vote(proposal_hash, proposal_index, True, kp_council_second_member)
    cast_vote(proposal_hash, proposal_index, False, kp_council_third_member)

    # To close voting processes
    close_vote(proposal_hash, proposal_index, weight_bond,
               length_bond, kp_council_first_member)

    # To submit second proposal
    proposal_index, proposal_hash = propose_spend(amount, kp_beneficiary,
                                                  kp_council_second_member)
    print(proposal_index)
    print(proposal_hash)

    # To submit votes by all council member to REJECT the motion
    cast_vote(proposal_hash, proposal_index, False, kp_council_first_member)
    cast_vote(proposal_hash, proposal_index, False, kp_council_second_member)
    cast_vote(proposal_hash, proposal_index, True, kp_council_third_member)

    # To close voting processes
    close_vote(proposal_hash, proposal_index,
               weight_bond, length_bond, kp_council_first_member)

    # To cal treasury spend from root to spend some amount withput approval
    spend(amount, kp_beneficiary, kp_council_third_member)
