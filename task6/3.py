fruits = [['Banana', 'apple'], ['apricot', 'Avocado'],['lime', 'lemon'], ['Mango', 'grapes']]
fruits1 = []
list = [item for sublist in fruits for item in sublist]
for element in list:
    if element[0].isupper() == True:
        fruits1.append(element)
print(fruits1)
