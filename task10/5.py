def minn(detail = int, people = int, car = int, tree = int):
    number = []
    min_detail = 72
    min_people = 4
    min_car = 2
    min_tree = 7   

    if min_detail < detail:
        number.append(detail // min_detail)
        
    if min_people < people:
        number.append(people // min_people)
        
    if min_car < car:
        number.append(car // min_car)
        
    if min_tree < tree:
        number.append(tree // min_tree)
        
    if min_detail > detail:
        number = [0]
        
    if min_people > people:
        number = [0]
        
    if min_car > car:
        number = [0]
        
    if min_tree > tree:
        number = [0]

    print(min(number))
minn(144, 8, 4, 14)
minn(10000, 16, 6, 2)