import sys
sys.path.append('./')
import time

from substrateinterface import SubstrateInterface, Keypair
from peaq.sudo_extrinsic import funds
from tools.utils import KP_GLOBAL_SUDO, get_collators
import argparse


def fund_delegators(substrate: SubstrateInterface, delegators: list, amount: int, batch_num: int = 500):
    delegators = [kp.ss58_address for kp in delegators]
    for i in range(0, len(delegators), batch_num):
        print(f'Funding {i} / {len(delegators)}')
        funds(substrate, KP_GLOBAL_SUDO, delegators[i:i + batch_num], amount)
        print(f'Funded {i} / {len(delegators)}')


def generate_delegators(number: int):
    return [Keypair.create_from_mnemonic(Keypair.generate_mnemonic()) for _ in range(number)]


def get_collator_stake(substrate: SubstrateInterface, validator: str) -> int:
    key = Keypair(ss58_address=validator)
    collator_info = get_collators(substrate, key)
    return int(collator_info['stake'].value)


def delegate_delegators(substrate: SubstrateInterface, delegators: list, collator_addr: str, collator_stake: int):
    for i, kp in enumerate(delegators):
        call = substrate.compose_call(
            call_module='ParachainStaking',
            call_function='join_delegators',
            call_params={
                'collator': collator_addr,
                'amount': collator_stake
            }
        )
        extrinsic = substrate.create_signed_extrinsic(call, keypair=kp)
        substrate.submit_extrinsic(extrinsic, wait_for_inclusion=False)


def get_validators_info(substrate):
    validators = substrate.query('Session', 'Validators', [])
    return [validator.value for validator in validators]


def main():
    parser = argparse.ArgumentParser(description='Setup the delegator')
    parser.add_argument('--number', type=int, required=True, help='Number of delegators you want to setup')
    parser.add_argument('--url', type=str, required=True, help='websocket URL')
    parser.add_argument('--collator', type=str, help='Collator address')

    args = parser.parse_args()
    substrate = SubstrateInterface(url=args.url)

    if args.collator:
        validators = [args.collator]
    else:
        # Get total valdators length
        validators = get_validators_info(substrate)

    print(f'Number of validators are {len(validators)}')
    # Get default staking number
    collator_stake = get_collator_stake(substrate, validators[0])
    fund_value = collator_stake * 2
    if fund_value < 2 * 10 ** 18:
        fund_value = 2 * 10 ** 18
        print(f'Collator stake {collator_stake} is less than {fund_value}, so we will fund it with {fund_value}')

    # Fund the delegators
    kps = generate_delegators(args.number * len(validators))
    fund_delegators(substrate, kps, fund_value)
    time.sleep(12)

    # Delegate the delegators
    for idx, validator in enumerate(validators):
        print(F'Setup delegators for {validator} start, {idx} / {len(validators)}')
        delegate_delegators(substrate, kps[args.number * idx: args.number * (idx + 1)], validator, collator_stake)
        print(f'Setup delegators for {validator} successfully, {idx} / {len(validators)}')

        while True:
            pending_tx = substrate.retrieve_pending_extrinsics()
            if len(pending_tx) < 5:
                print(f'The pending transactions are {len(pending_tx)}, we can continue')
                break
            else:
                print(f'Waiting for {len(pending_tx)} pending transactions')
            time.sleep(12)


if __name__ == '__main__':
    main()
