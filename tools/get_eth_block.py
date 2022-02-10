from web3 import Web3
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:9933'))
block = w3.eth.get_block('latest')
print(block)
