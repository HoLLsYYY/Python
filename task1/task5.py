a = []
b = []
c = []
print('Введите количество чисел: ')
numbers = int(input())
for i in range(numbers):
    print('Введите числа:')
    number = int(input())
    if number > 0:
        a.append(number)
    if number < 0:
        b.append(number)
    else:
        c.append(number)
for_a = sum(a)/len(a)
for_b = sum(b)
for_c = "*" * len(c)
print(f'{for_a}\n{for_b}\n{for_c}')
