
def enforce_input(q, is_int=False):
    if is_int:
        while True:
            try:
                a = int(input(q))
                if not isinstance(a, int):
                    print("Try again, must be integer!")
                else:
                    return int(a)
            except:
                print("Try again, must be integer!")
    else:
        while True:
            a = input(q)
            if a == "":
                print("Try again, no input!")
            else:
                return a
