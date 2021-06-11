#!/usr/bin/python3
import sys, re, os, os.path, functools

lineRe = re.compile(r'^(\(\d+, \(\d+, \d+, \d+\)\)): \[(.*?)\]\s*')
fileNameRe = re.compile(r'^runsperinningstats\.(\d+)$')
def main(directory, isQuiet):
    fileNames = [x for x in os.listdir(directory) if fileNameRe.match(x)]
    fileNames = sorted(fileNames)
    if not isQuiet:
        print(fileNames)
    existingLineMap = {}
    startYear = int(fileNameRe.match(fileNames[0]).group(1))
    endYear = int(fileNameRe.match(fileNames[-1]).group(1))
    for year in range(startYear, endYear+1):
        fileName = 'runsperinningstats.' + str(year)
        f = None
        try:
            f = open(os.path.join(directory, fileName), 'r')
        except:
            pass
        linesToWrite = []
        if f != None:
            for line in f.readlines():
                lineMatch = lineRe.match(line)
                if lineMatch:
                    key = lineMatch.group(1)
                    runDistribution = [int(x.strip()) for x in lineMatch.group(2).split(',')]
                    if key not in existingLineMap:
                        existingLineMap[key] = []
                    existingRuns = existingLineMap[key]
                    while len(existingRuns) < len(runDistribution):
                        existingRuns.append(0)
                    for i in range(len(runDistribution)):
                        existingRuns[i] += runDistribution[i]
                    existingLineMap[key] = existingRuns
                    linesToWrite.append(key + ": [" + ', '.join([str(x) for x in existingRuns]) + "]")
                else:
                    print("ERROR - couldn't parse line %s" % line)
            f.close()
        linesToWrite.sort()
        with open(os.path.join(directory, 'runsperinningstatscumulative.' + str(year)), 'w') as outFile:
            for line in linesToWrite:
                outFile.write(line + '\n')

if (__name__ == '__main__'):
    isQuiet = len(sys.argv) > 2 and sys.argv[2] == '-q'
    main(sys.argv[1], isQuiet)