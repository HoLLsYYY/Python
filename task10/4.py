def double(str = str):
    new_str = ''
    for i in str:
        new_str += i*2
    return new_str
print(double('Hello world'))