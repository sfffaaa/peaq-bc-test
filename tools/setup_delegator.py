import sys
sys.path.append('./')
import time

from substrateinterface import SubstrateInterface, Keypair
from peaq.sudo_extrinsic import funds
from tools.utils import KP_GLOBAL_SUDO, get_collators
import argparse


KP_COLLATOR = Keypair.create_from_uri('//Dave')


def fund_delegators(substrate: SubstrateInterface, delegators: list, amount: int, batch_num: int = 250):
    delegators = [kp.ss58_address for kp in delegators]
    for i in range(0, len(delegators), batch_num):
        funds(substrate, KP_GLOBAL_SUDO, delegators[i:i + batch_num], amount)


def generate_delegators(number: int):
    return [Keypair.create_from_mnemonic(Keypair.generate_mnemonic()) for _ in range(number)]


def get_default_collators_info(substrate: SubstrateInterface):
    collator_info = get_collators(substrate, KP_COLLATOR)
    return (KP_COLLATOR.ss58_address, int(collator_info['stake'].value))


def delegate_delegators(substrate: SubstrateInterface, delegators: list, collator_addr: str, collator_stake: int):
    for i, kp in enumerate(delegators):
        print(f'run: {i}/{len(delegators)}')
        call = substrate.compose_call(
            call_module='ParachainStaking',
            call_function='join_delegators',
            call_params={
                'collator': collator_addr,
                'amount': collator_stake
            }
        )
        print(call)
        extrinsic = substrate.create_signed_extrinsic(call, keypair=kp)
        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=False)
        print(f'run: {i}/{len(delegators)}: {receipt.extrinsic_hash}')


def main():
    parser = argparse.ArgumentParser(description='Setup the delegator')
    parser.add_argument('--number', type=int, required=True, help='Number of delegators you want to setup')
    parser.add_argument('--url', type=str, required=True, help='websocket URL')

    args = parser.parse_args()
    substrate = SubstrateInterface(url=args.url)

    kps = generate_delegators(args.number)
    collator_addr, collator_stake = get_default_collators_info(substrate)
    fund_delegators(substrate, kps, 1 * 10 ** 18)
    time.sleep(12)
    delegate_delegators(substrate, kps, collator_addr, collator_stake)


if __name__ == '__main__':
    main()
