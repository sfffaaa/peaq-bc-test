from behave import fixture, use_fixture
from substrateinterface import SubstrateInterface


WS_URL = 'ws://127.0.0.1:9947'


@fixture
def connect_substrate(context):
    context._substrate = SubstrateInterface(url=WS_URL,)
    yield context._substrate
    context._substrate.close()


def before_all(context):
    use_fixture(connect_substrate, context)
