import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface
from tools.utils import WS_URL
from tools.block_creation_utils import get_block_creation_times

BLOCK_TRAVERSE = 20
BLOCK_CREATION_MS = 12000
BLOCK_TOLERATE_PERCENTAGE = 10


def block_creation_time_test():
    print('--- Test block creation time ---')
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            ave_time = get_block_creation_times(substrate, BLOCK_TRAVERSE)
            if abs(ave_time - BLOCK_CREATION_MS) / float(BLOCK_CREATION_MS) * 100. > BLOCK_TOLERATE_PERCENTAGE:
                print(f'The average block time {ave_time} is longer than the tolerate rate {BLOCK_TOLERATE_PERCENTAGE} * {BLOCK_CREATION_MS}')
                raise IOError(f'Check the average block creation time {ave_time}')
            print(f'The block creation time {ave_time} (ms) is okay')

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    block_creation_time_test()
