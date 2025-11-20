matrix = [[-446, 281, -80],[465, 432, -122],[13,'error', 8]]
for elem1 in matrix:
    for i in elem1:
        if isinstance(i, str) == True:
            i = len(i)
print(matrix)
