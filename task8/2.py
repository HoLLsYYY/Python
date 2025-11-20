sl = {'</>':13, 'script':1, '__init__':10, 'self':5, 'number_9':6, '#comment':100}
print(f'Изначальный словарь:\n{sl}')
print('Введите элемент который хотите добавить: ')
elem = input()
print('Введите значение для этого элемента: ')
num = int(input())
sl[elem] = num
print(f'Теперь словарь выглядит так:\n{sl}')
