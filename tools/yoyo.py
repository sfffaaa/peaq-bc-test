from web3.auto import w3
from web3 import Web3

SK = '0x777ef29e84150b78f8098873bd99fd40c7b23734f30769335efc53b9d581f984'
PK = w3.toChecksumAddress('0x434db4884fa631c89e57ea04411d6ff73ef0e297')
DST_PK = w3.toChecksumAddress('0xc5bdf22635df81f897c1bb2b24b758deb21f522d')

w3_obj = Web3(Web3.HTTPProvider("http://127.0.0.1:9933"))

signed_txn = w3.eth.account.signTransaction(dict(
    nonce=w3_obj.eth.getTransactionCount(PK),
    gasPrice = 10,
    gas = 100000,
    to=DST_PK,
    value=Web3.toWei(12345,'ether'),
    chainId=9999,
), SK)

w3.eth.sendRawTransaction(signed_txn.rawTransaction)

# Why cannot work??
