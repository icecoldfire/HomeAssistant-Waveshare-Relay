from pytest_socket import enable_socket, disable_socket, socket_allow_hosts
import pytest


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup():
    print("Setting up test environment...")
    enable_socket()
    socket_allow_hosts(["127.0.0.1", "localhost", "::1"], allow_unix_socket=True)
