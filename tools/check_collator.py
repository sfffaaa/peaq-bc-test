import sys
sys.path.append('./')


from substrateinterface import SubstrateInterface
from peaq.utils import get_block_height, get_block_hash
import argparse
from collections import Counter
import pprint
pp = pprint.PrettyPrinter(indent=4)


def get_current_collator(substrate, num=80):
    now_block_height = get_block_height(substrate)
    collators = []
    for i in range(num):
        print(f'get author in block height: {now_block_height - i}')
        block_hash = get_block_hash(substrate, now_block_height - i)
        block_info = substrate.get_block(block_hash, include_author=True)
        collators.append(block_info['author'])
    return Counter(collators)


def get_session_validator(substrate):
    session_info = substrate.query(
        module='Session',
        storage_function='Validators',
        params=[],
    )
    return set(session_info.value)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get storage and constants from a Substrate chain')
    parser.add_argument('-r', '--runtime', type=str, required=True, help='Your runtime websocket endpoint')

    args = parser.parse_args()

    substrate = SubstrateInterface(
        url=args.runtime,
    )
    validators = get_session_validator(substrate)
    collator_set = get_current_collator(substrate, 16 * 4)
    print(f'Validators who didn\'t produce block: {validators - set(collator_set.keys())}')
    print('Block author count:')
    pp.pprint(collator_set)
