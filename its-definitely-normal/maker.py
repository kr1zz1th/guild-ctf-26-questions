with open('source.txt', 'r') as f:
    a = list(f.read())

flag = "exploiitm{00H_SP3C14l_ch4R4cT3R2}"
dist = []
for i in flag:
    dist.append(ord(i))

count = 0
for l in dist:
    count += l
    a.insert(count, "\u200b")
    count += 1

a = ''.join(a)
print(a)

with open('file.txt', 'w', encoding="utf-8") as f:
    f.write(a)

