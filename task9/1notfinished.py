all = {}
all_keys = all.keys()
while True:
    print('[1] - Create a new note. [2] - Read all notes. [3] - Delete entry. [4] - Exit. ')
    answer = int(input())
    if answer == 1:
        name = input('Заголовок: ')
        text = input('Текст: ')
        all[name] = text
        break
    if answer == 2:
        print(all_keys)
