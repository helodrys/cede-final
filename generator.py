import random

numbers = []
x = 2
for x in range(30):
    num = random.randint(1, 960)
    while num in numbers:
        num = random.randint(1, 1000)
    numbers.append(num)

print(numbers)