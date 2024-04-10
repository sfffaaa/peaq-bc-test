import unittest

from substrateinterface import SubstrateInterface
from tools.utils import WS_URL
from peaq.utils import wait_for_n_blocks, get_block_height
from tools.block_creation_utils import get_block_creation_times

BLOCK_TRAVERSE = 10
BLOCK_CREATION_MS = 12000
BLOCK_TOLERATE_PERCENTAGE = 10


class TestBlockCreationTime(unittest.TestCase):
    def wait_block(self, substrate, block_number):
        now_block = get_block_height(substrate)
        if now_block >= block_number:
            return
        wait_for_n_blocks(substrate, block_number - now_block + 1)

    def test_block_creation_time(self):
        substrate = SubstrateInterface(url=WS_URL)

        self.wait_block(substrate, BLOCK_TRAVERSE)

        ave_time = get_block_creation_times(substrate, BLOCK_TRAVERSE)
        self.assertLess(abs(ave_time - BLOCK_CREATION_MS) / float(BLOCK_CREATION_MS) * 100.,
                        BLOCK_TOLERATE_PERCENTAGE)
