from slickrpc import Proxy

def get_rpc(rpcuser, rpcpass, rpcport, rpcip):
    url = f"http://{rpcuser}:{rpcpass}@{rpcip}:{rpcport}"
    print(url)
    return Proxy(url)