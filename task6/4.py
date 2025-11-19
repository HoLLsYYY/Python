random_elements = [['toy', 'bee', 'cheese', 'ear'],[False, 'word', '0110110', 10],['happiness', '(」°ロ°)」', 'luck', None],['car', '<- code ->', 4.7, True]]
list = [item for sublist in random_elements for item in sublist]
for index , element in enumerate(list):
    if index % 2 == 0:
        print(element)
