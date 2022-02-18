from web3 import Web3
from tools.utils import ETH_URL

w3 = Web3(Web3.HTTPProvider(ETH_URL))
block = w3.eth.get_block('latest')
print(block)
