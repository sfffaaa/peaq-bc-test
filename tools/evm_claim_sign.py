from substrateinterface import SubstrateInterface
from peaq.utils import get_block_hash
from eth_account import Account as ETHAccount
from eth_account.messages import encode_structured_data
from peaq.utils import ExtrinsicBatch
import argparse


def gen_eth_signature(sub_pk, eth_sk, chain_id, block_zero_hash):
    message = {
        'types': {
            'EIP712Domain': [
                {'type': 'string', 'name': 'name'},
                {'type': 'string', 'name': 'version'},
                {'type': 'uint256', 'name': 'chainId'},
                {'type': 'bytes32', 'name': 'salt'},
            ],
            'Transaction': [
                {'type': 'bytes', 'name': 'substrateAddress'},
            ]
        },
        'primaryType': 'Transaction',
        'domain': {
            'name': 'Peaq EVM claim',
            'version': '1',
            'chainId': chain_id,
            # Block hash zero
            'salt': bytes.fromhex(block_zero_hash[2:]),
        },
        'message': {
            'substrateAddress': sub_pk,
        }
    }
    signature = ETHAccount.sign_message(encode_structured_data(message), eth_sk)

    return signature.signature.hex()


def calculate_claim_signature(substrate, sub_ss58, eth_sk, eth_chain_id):
    if eth_sk.startswith('0x'):
        eth_sk = eth_sk[2:]
    eth_sk = bytes.fromhex(eth_sk)

    block_hash_zero = get_block_hash(substrate, 0)
    sub_pk = substrate.ss58_decode(sub_ss58)
    sub_pk = bytes.fromhex(sub_pk)

    return gen_eth_signature(sub_pk, eth_sk, eth_chain_id, block_hash_zero)


def claim_account(substrate, kp_sub, kp_eth, eth_signature):
    batch = ExtrinsicBatch(substrate, kp_sub)
    batch_claim_account(batch, kp_eth, eth_signature)
    return batch.execute()


def batch_claim_account(batch, kp_eth, eth_signature):
    batch.compose_call(
        'AddressUnification',
        'claim_account',
        {
            'evm_address': kp_eth.ss58_address,
            'eth_signature': eth_signature,
        }
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upgrade the runtime')
    parser.add_argument('--eth-sk', type=str, required=True, help='Your ETH private key')
    parser.add_argument('--sub-ss58', type=str, required=True, help='Your Substrate SS58 address')
    parser.add_argument('--eth-chain-id', type=int, required=True, help='Your ETH chain ID')
    parser.add_argument('--url', type=str, required=True, help='websocket URL')

    args = parser.parse_args()
    substrate = SubstrateInterface(url=args.url)

    signature = calculate_claim_signature(SubstrateInterface(url=args.url), args.sub_ss58, args.eth_sk, args.eth_chain_id)
    print('Signature: {}'.format(signature))
