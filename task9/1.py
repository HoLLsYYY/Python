all = {}
all_keys = all.keys()
while True:
    print('[1] - Create a new note. [2] - Read all notes. [3] - Delete entry. [4] - Exit. ')
    answer = int(input())
    if answer == 1:
        name = input('Заголовок: ')
        text = input('Текст: ')
        all[name] = text
    if answer == 2:
        print(f'{all_keys}\nWitch note to read?')
        read_answer = input()
        if read_answer in all_keys:
            print(all[read_answer])
        else:
            print(f'{read_answer} не был найден в списке заметок\nПопробуйте еще раз')
    if answer == 3:
        print(f'{all_keys}\nКакой из перечисленных заголовков вы хотите удалить?')
        del_answer = input()
        if del_answer in all_keys:
            del all[del_answer]
            print(f'Теперь ваш список выглядит так:\n{all_keys}')
    if answer == 4:
        break
