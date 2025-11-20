bin_sy = ['11011111', '11011101', '11000111', '11011100','11011110']
bin10 = []
min_max = []
for elem in bin_sy:
    elem = int(elem, 2)
    bin10.append(elem)
min_max.append(min(bin10))
min_max.append(max(bin10))
print(f'{bin10}\n{min_max}')
