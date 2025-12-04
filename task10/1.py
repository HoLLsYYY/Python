new_letter = []
def upper(t):
    for i in t:
        if i.isupper() == True:
            new_letter.append(i)
    return new_letter
print(upper('Hello World'))