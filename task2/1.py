matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
a = []
b = []
for row in matrix:
    for element in row:
        if element % 2 != 0:
            a.append(element)
        else:
            b.append(element)
print(a)
print(len(b))
