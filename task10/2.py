def punct(txt = str):
    count = 0
    for i in txt:
        if '!' in txt:
            count += 1
        if '?' in txt:
            count += 1
        if '(' in txt:
            count += 1
        if ')' in txt:
            count += 1
        else:
            count += 0
    return count
print(punct('Hello world!'))