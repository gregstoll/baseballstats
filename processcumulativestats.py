#!/usr/bin/python3
import sys, re, os, os.path

lineRe = re.compile(r'^\((\d+), (\d+), (\d+), \((\d+), (\d+), (\d+)\), (-?\d+)\): \((\d+), (\d+)\)')
fileNameRe = re.compile(r'^stats\.(\d+)$')
def main(directory):
    fileNames = [x for x in os.listdir(directory) if fileNameRe.match(x)]
    fileNames = sorted(fileNames)
    print(fileNames)
    existingLineMap = {}
    startYear = int(fileNameRe.match(fileNames[0]).group(1))
    endYear = int(fileNameRe.match(fileNames[-1]).group(1))
    for year in range(startYear, endYear+1):
        fileName = 'stats.' + str(year)
        f = None
        try:
            f = open(os.path.join(directory, fileName), 'r')
        except:
            pass
        linesToWrite = []
        newExistingLineMap = {}
        if f != None:
            for line in f.readlines():
                lineMatch = lineRe.match(line)
                if lineMatch:
                    if (lineMatch.group(2) == '1'):
                        keyString = '"H",'
                    else:
                        keyString = '"V",'
                    # Starting at one to make compliant with other file
                    baseSum = 1
                    if (lineMatch.group(4) == '1'):
                        baseSum = baseSum + 1
                    if (lineMatch.group(5) == '1'):
                        baseSum = baseSum + 2
                    if (lineMatch.group(6) == '1'):
                        baseSum = baseSum + 4
                    keyString = keyString + "%s,%s,%s,%s" % (lineMatch.group(1), lineMatch.group(3), baseSum, lineMatch.group(7))
                    total = int(lineMatch.group(9))
                    wins = int(lineMatch.group(8))
                    if keyString in existingLineMap:
                        total += existingLineMap[keyString][1]
                        wins += existingLineMap[keyString][0]
                    newExistingLineMap[keyString] = (wins, total)
                    if keyString in existingLineMap:
                        del existingLineMap[keyString]
                    stringToPrint = keyString + ",%s,%s" % (total, wins)
                    linesToWrite.append(stringToPrint)
                else:
                    print(("ERROR - couldn't parse line %s" %line))
            f.close()
        print((len(existingLineMap)))
        for existingKey in existingLineMap:
            linesToWrite.append(existingKey + ",%s,%s" % (existingLineMap[existingKey][1], existingLineMap[existingKey][0]))
            newExistingLineMap[existingKey] = existingLineMap[existingKey]
        existingLineMap = newExistingLineMap
        linesToWrite.sort(cmpWithCommaFirst)
        with open(os.path.join(directory, 'statscumulative.' + str(year)), 'w') as outFile:
            for line in linesToWrite:
                outFile.write(line + '\n')

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
