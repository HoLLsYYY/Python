matrix = [[1, 2, 3],[4, 5, 6],[7, 8, 9]]
summ = []
count = -1
for elem in matrix:
    count += 1
    summ.append(elem[count])
print(sum(summ))
