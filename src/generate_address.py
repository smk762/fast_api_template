import base58
import hashlib
import threading
from random import shuffle

# Set char scan range, then randomise the order
base58_chars = 'abcdefghijkmnopqrstuvwxyz123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
base58_chars = [i for i in base58_chars]
shuffle(base58_chars)

def validate_base58_checksum(address):
    try:
        # Decode the base58 address
        decoded_address = base58.b58decode(address)

        # Extract the checksum from the decoded address
        checksum = decoded_address[-4:]

        # Compute the hash of the address excluding the checksum
        computed_checksum = hashlib.sha256(hashlib.sha256(decoded_address[:-4]).digest()).digest()[:4]

        # Compare the computed checksum with the extracted checksum
        if checksum == computed_checksum:
            return True
        else:
            return False
    except Exception as e:
        print("Error occurred while validating address:", e)
        return False

def get_vote_address(address_prefix):
    for b in base58_chars:
        for c in base58_chars:
            for d in base58_chars:
                for e in base58_chars:
                    for f in base58_chars:
                        address = address_prefix + f"{b}{c}{d}{e}{f}"
                        if validate_base58_checksum(address):            
                            return address
        print(f">>> Processed address prefix: {address_prefix}:{b}{c}")
    print(f"### Processed address prefix: {address_prefix}:{b}")
    
    

def process_address_prefix(address_prefix):
    address = get_vote_address(address_prefix)
    if address is not None:
        with open("valid_addresses.txt", "a") as f: 
            f.write(address + "\n")

def process_prefix(prefix):
    # Create and start threads for each address prefix
    x = 1
    threads = []
    middle = "X" * (34 - len(prefix) - 6)
    for a in base58_chars:
        part_prefix = prefix + middle + f"{a}"
        t = threading.Thread(target=process_address_prefix, args=(part_prefix,))
        threads.append(t)

    # Start threads

    for t in threads:
        print(f"Starting thread {x}/{len(threads)}")
        t.start()
        x += 1

    # Wait for all threads to complete
    for t in threads:
        t.join()

    print("All threads completed.")

if __name__ == '__main__':
    while True:
        prefix = input("Enter the prefix to process: ")
        if not prefix.startswith("R"):
            prefix = "R" + prefix
        process_prefix(prefix)
            
            