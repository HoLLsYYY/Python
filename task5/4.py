mass = [14, -6, 3, 11, 6, 8.5, 99, -20, -6, 10, 40, 0.25, -4, 5]
remove_mass = [-6, -20, -6, -4]
for i in remove_mass:
    mass.remove(i)
print(mass)
mass.sort()
print(mass)
mass.sort(reverse=True)
print(mass)
