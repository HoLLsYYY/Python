def custom_filter(str):
    number = []
    for i in str:
        if i == int:
            if i % 7 == 0:
                number.append(i)
    if sum(number) < 83:
        print(f'{number}\nTrue')

    else:
        print(f'{number}\nFalse')
custom_filter([7, 10.5, 'txt', 14, 2, 56])