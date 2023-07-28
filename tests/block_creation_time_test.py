import unittest

from substrateinterface import SubstrateInterface
from tools.utils import WS_URL
from tools.block_creation_utils import get_block_creation_times

BLOCK_TRAVERSE = 20
BLOCK_CREATION_MS = 12000
BLOCK_TOLERATE_PERCENTAGE = 10


class TestBlockCreationTime(unittest.TestCase):
    def test_block_creation_time(self):
        with SubstrateInterface(url=WS_URL) as substrate:
            ave_time = get_block_creation_times(substrate, BLOCK_TRAVERSE)
            self.assertLess(abs(ave_time - BLOCK_CREATION_MS) / float(BLOCK_CREATION_MS) * 100.,
                            BLOCK_TOLERATE_PERCENTAGE)
