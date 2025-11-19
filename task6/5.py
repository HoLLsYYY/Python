print('Введите количество строк:')
numbers = int(input())
print('Введите количество столбцов:')
numbers1 = int(input())
count = 0
list = []
list1 = []
for i in range(numbers1*numbers):
    str = f'{[i//numbers1]}{[count]}'
    count +=1
    print(f'Введите значение элемента {str}:')
    num = int(input())
    list.append(num)
    while count % numbers1 == 0:
        list1.extend(list)
        list = []
        break
matrix = [list1[i * numbers1:(i + 1) * numbers1] for i in range(numbers)]
print(matrix)
