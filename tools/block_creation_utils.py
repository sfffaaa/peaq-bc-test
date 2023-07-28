def get_block_height(substrate):
    latest_block = substrate.get_block()
    return latest_block['header']['number']


def get_block_timestamp(substrate, height):
    current_block = substrate.get_block(block_number=height)
    create_time = int(str(current_block['extrinsics'][0]['call']['call_args'][0]['value']))
    return create_time


def get_block_creation_times(substrate, block_traverse_num):
    latest_height = get_block_height(substrate)
    if latest_height < block_traverse_num:
        raise IOError(f'Please wait longer, current block height {latest_height} < {block_traverse_num}')
    create_times = [get_block_timestamp(substrate, height)
                    for height in range(latest_height - block_traverse_num, latest_height)]
    diff_times = [x - y for x, y in zip(create_times[1:], create_times)]
    ave_time = sum(diff_times) / len(diff_times)
    return ave_time
