#!/usr/bin/python3
import sys, re, functools

lineRe = re.compile(r'^\((\d+), (\d+), (\d+), \((\d+), (\d+), (\d+)\), (-?\d+)\): \((\d+), (\d+)\)')
def main(fileName):
    f = open(fileName, 'r')
    linesToWrite = []
    for line in f.readlines():
        lineMatch = lineRe.match(line)
        if lineMatch:
            if (lineMatch.group(2) == '1'):
                stringToPrint = '"H",'
            else:
                stringToPrint = '"V",'
            # Starting at one to make compliant with other file
            baseSum = 1
            if (lineMatch.group(4) == '1'):
                baseSum = baseSum + 1
            if (lineMatch.group(5) == '1'):
                baseSum = baseSum + 2
            if (lineMatch.group(6) == '1'):
                baseSum = baseSum + 4
            stringToPrint = stringToPrint + "%s,%s,%s,%s,%s,%s" % (lineMatch.group(1), lineMatch.group(3), baseSum, lineMatch.group(7), lineMatch.group(9), lineMatch.group(8))
            linesToWrite.append(stringToPrint)
        else:
            print("ERROR - couldn't parse line %s" %line)
    linesToWrite.sort(key=functools.cmp_to_key(cmpWithCommaFirst))
    for line in linesToWrite:
        print(line)
    f.close()

def cmpWithCommaFirst(x, y):
    if x[:3] < y[:3]:
        return -1
    if x[:3] > y[:3]:
        return 1
    xIsComma = (x[5] == ',')
    yIsComma = (y[5] == ',')
    if (x < y and yIsComma and not xIsComma):
        return 1
    elif (x > y and xIsComma and not yIsComma):
        return -1
    else:
        if x < y:
            return -1
        if x > y:
            return 1
        return 0

if (__name__ == '__main__'):
    main(sys.argv[1])
