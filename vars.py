#!/usr/bin/env python3
import sys
from lib.const import ConfigFastAPI

if __name__ == "__main__":
    config = ConfigFastAPI()
    if len(sys.argv) > 1:
        if sys.argv[1] == "print":
            for key, value in config.as_dict.items():
                print(f"{key} = {value}")
        elif sys.argv[1].upper() in config.as_dict:
            print(config.as_dict[sys.argv[1].upper()])
        else:
            print("Invalid argument.")

