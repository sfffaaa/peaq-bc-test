"""
Currency related tools.
"""

from tools.utils import TOKEN_NUM_BASE_DEV


TOKEN_NUM_BASE_DEV_DOT = pow(10, 10)
TOKEN_NUM_BASE_DEV_KSM = pow(10, 12)
TOKEN_NUM_BASE_DEV_ACA = pow(10, 12)


# Returns the value for x PEAQ
def peaq(x) -> int:
    return int(x * TOKEN_NUM_BASE_DEV)


# Returns the value for x milli-PEAQ (mPEAQ)
def mpeaq(x) -> int:
    return int(peaq(x) / 1000)


# Returns the value for x nano-PEAQ (nPEAQ)
def npeaq(x) -> int:
    return int(peaq(x) / 1000000000)


def dot(x) -> int:
    return int(x * TOKEN_NUM_BASE_DEV_DOT)


def mdot(x) -> int:
    return int(dot(x) / 1000)


def ksm(x) -> int:
    return int(x * TOKEN_NUM_BASE_DEV_KSM)


def mksm(x) -> int:
    return int(ksm(x) / 1000)


def aca(x) -> int:
    return int(x * TOKEN_NUM_BASE_DEV_ACA)
