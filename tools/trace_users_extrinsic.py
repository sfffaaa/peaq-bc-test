import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface, Keypair
import argparse


def main():
    parser = argparse.ArgumentParser(description='Trace the extrinsic from some users')
    parser.add_argument('--block', type=int, required=False, help='block number you want to trace')
    parser.add_argument('--number', type=int, required=True, help='number of the extrinsic you want to trace')
    parser.add_argument('--url', type=str, required=True, help='websocket URL')
    parser.add_argument('--user', type=str, required=True, help='Users\' ss58 address')

    args = parser.parse_args()
    substrate = SubstrateInterface(url=args.url)
    key = Keypair(ss58_address=args.user)

    # Get the latest block number
    if args.block:
        latest_block_num = args.block
    else:
        latest_block_num = substrate.get_block_number(None)

    for block_num in range(latest_block_num, 0, -1):
        print(f'block_num: {block_num}')
        block_hash = substrate.get_block_hash(block_num)
        block = substrate.get_block(block_hash)
        for extrinsic in block['extrinsics']:
            if 'address' not in extrinsic:
                continue
            if extrinsic['address'].value != key.ss58_address:
                print(f'{extrinsic["address"].value} != {key.ss58_address}')
                continue
            print(f'block_num: {block_num}, extrinsic: {extrinsic}')
            args.number -= 1
            if args.number == 0:
                print('Done')
                return


if __name__ == '__main__':
    main()
