from slickrpc import Proxy

def get_rpc(rpcuser, rpcpass, rpcport):
    return Proxy(f"http://{rpcuser}:{rpcpass}@127.0.0.1:{rpcport}")