from functools import wraps


def _show_extrinsic(receipt, info_type):
    if receipt.is_success:
        print(f'✅ {info_type}, Success: {receipt.get_extrinsic_identifier()}')
    else:
        print(f'⚠️  {info_type}, Extrinsic Failed: {receipt.error_message} {receipt.get_extrinsic_identifier()}')


def sudo_call_compose(sudo_keypair):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            substrate = args[0]
            payload = func(*args, **kwargs)
            return substrate.compose_call(
                call_module='Sudo',
                call_function='sudo',
                call_params={
                    'call': payload.value,
                }
            )
        return wrapper
    return decorator


def sudo_extrinsic_send(sudo_keypair):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            substrate = args[0]
            call = func(*args, **kwargs)
            extrinsic = substrate.create_signed_extrinsic(
                call=call,
                keypair=sudo_keypair,
            )
            receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
            _show_extrinsic(receipt, func.__name__)
            return receipt
        return wrapper
    return decorator


def user_extrinsic_send(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        substrate = args[0]
        kp_src = args[1]
        nonce = substrate.get_account_nonce(kp_src.ss58_address)

        call = func(*args, **kwargs)

        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=kp_src,
            era={'period': 64},
            nonce=nonce
        )
        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        _show_extrinsic(receipt, func.__name__)
        return receipt
    return wrapper
