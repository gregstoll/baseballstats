#!/usr/bin/python
import sys, re

lineRe = re.compile(r'^\((\d+), (\d+), (\d+), \((\d+), (\d+), (\d+)\), (-?\d+)\): \((\d+), (\d+)\)')
def main(fileName):
    file = open(fileName, 'r')
    linesToWrite = []
    for line in file.readlines():
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
            print "ERROR - couldn't parse line %s" %line
    linesToWrite.sort(cmpWithCommaFirst)
    for line in linesToWrite:
        print line
    file.close()

def cmpWithCommaFirst(x, y):
    if (cmp(x[:3], y[:3]) != 0):
        return cmp(x[:3], y[:3])
    xIsComma = (x[5] == ',')
    yIsComma = (y[5] == ',')
    if (cmp(x,y) == -1 and yIsComma and not xIsComma):
        return 1
    elif (cmp(x,y) == 1 and xIsComma and not yIsComma):
        return -1
    else:
        return cmp(x,y)

if (__name__ == '__main__'):
    main(sys.argv[1])
