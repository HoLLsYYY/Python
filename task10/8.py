def square(x = int, y = int):
    list = []
    for i in range(y):
        list.append(f'|{i+1}|')
    for i in range(x):
        print(list)
square(2,3)