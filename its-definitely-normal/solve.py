with open('transcript.txt', 'r') as f:
    a = f.read()

b = a.split("\u200b")

c = []
for i in b:
    c.append(chr(len(i)))

print(''.join(c))

