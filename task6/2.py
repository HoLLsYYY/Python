matrix_1 = [[2, 4, 3, 6], [5, 7, 1, 5]]
matrix_2 = [[2, 9, 0, 2], [3, 4, 7, 6]]
for i1 in range(len(matrix_1)):
    for i2 in range(len(matrix_2[0])):
        answer_matrix = matrix_1[i1][i2] * matrix_2[i1][i2]
        print(answer_matrix ,end=' ')
