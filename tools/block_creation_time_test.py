import sys
sys.path.append('./')

from substrateinterface import SubstrateInterface
from tools.utils import WS_URL

BLOCK_TRAVERSE = 20
BLOCK_CREATION_MS = 12000
BLOCK_TOLERATE_PERCENTAGE = 10


def get_block_height(substrate):
    latest_block = substrate.get_block()
    return latest_block['header']['number']


def get_block_timestamp(substrate, height):
    current_block = substrate.get_block(block_number=height)
    create_time = int(str(current_block['extrinsics'][0]['call']['call_args'][0]['value']))
    return create_time


def block_creation_time_test():
    print('--- Test block creation time ---')
    try:
        with SubstrateInterface(url=WS_URL) as substrate:
            latest_height = get_block_height(substrate)
            if latest_height < BLOCK_TRAVERSE:
                raise IOError(f'Please wait longer, current block height {latest_height} < {BLOCK_TRAVERSE}')
            create_times = [get_block_timestamp(substrate, height)
                            for height in range(latest_height - BLOCK_TRAVERSE, latest_height)]
            diff_times = [x - y for x, y in zip(create_times[1:], create_times)]
            ave_time = sum(diff_times) / len(diff_times)
            if abs(ave_time - BLOCK_CREATION_MS) / float(BLOCK_CREATION_MS) * 100. > BLOCK_TOLERATE_PERCENTAGE:
                print(f'The average block time {ave_time} is longer than the tolerate rate {BLOCK_TOLERATE_PERCENTAGE} * {BLOCK_CREATION_MS}')
                raise IOError(f'Check the average block creation time {ave_time}')
            print(f'The block creation time {ave_time} (ms) is okay')

    except ConnectionRefusedError:
        print("⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first")
        sys.exit()


if __name__ == '__main__':
    block_creation_time_test()
