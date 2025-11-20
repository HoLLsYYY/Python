from colorama import init, Fore
all_d = {}
print('Введите количество желаемых элементов вашего словаря: ')
count = int(input())
for i in range(count):
    print(f'Введите элемент номер {i+1}: ')
    elem = int(input())
    print(f'Введите значение для элемента {elem} под номер {i+1}:')
    num = int(input())
    all_d[elem] = num
print(Fore.GREEN + f'Вот ваш словарь из {count} елементов\n{all_d}')
