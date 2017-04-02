#!/usr/bin/python3
import re, os, cgi

directory = 'statsyears'
fileNameRe = re.compile(r'^statscumulative.(\d+)$')
lineRe = re.compile(r'^"(H|V)",(\d+),(\d),(\d),(-?\d+),(\d+),(\d+)$')
outputFileName = 'leverage'

class Situation:
    def initReal(self, homeOrVisitor, inning, outs, runnersOneBased, runDiff, totalCount, winCount):
        self.homeOrVisitor = homeOrVisitor
        assert self.homeOrVisitor == "H" or self.homeOrVisitor == "V"
        self.inning = inning
        assert self.inning >= 1
        self.outs = outs
        assert self.outs >= 0 and self.outs <= 2
        self.runnersOneBased = runnersOneBased
        assert self.runnersOneBased >= 1 and self.runnersOneBased <= 8
        self.runDiff = runDiff
        self.totalCount = totalCount
        self.winCount = winCount
        assert self.winCount >= 0 and self.winCount <= self.totalCount
    def __init__(self, match=None):
        if match is not None:
            self.initReal(match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6)), int(match.group(7)))
    @staticmethod
    def makeFromKey(key):
        s = Situation()
        s.initReal(key[0], key[1], key[2], key[3], key[4], 1, 1)
        return s
    def __str__(self):
        return str(self.getKey()) + ": " + str(self.winCount) + " / " + str(self.totalCount)
    def clone(self):
        s = Situation()
        s.initReal(self.homeOrVisitor, self.inning, self.outs, self.runnersOneBased, self.runDiff, self.totalCount, self.winCount)
        return s
    def getKey(self):
        return (self.homeOrVisitor, self.inning, self.outs, self.runnersOneBased, self.runDiff)
    def getFileString(self):
        return ','.join(['"' + self.getKey()[0] + '"'] + [str(x) for x in self.getKey()[1:]])
    def getNumRunners(self):
        numRunners = 0
        r = self.runnersOneBased - 1
        if (r & 1 != 0): numRunners += 1
        if (r & 2 != 0): numRunners += 1
        if (r & 4 != 0): numRunners += 1
        return numRunners

    def getNumRunnersInScoringPosition(self):
        numRunners = 0
        r = self.runnersOneBased - 1
        if (r & 2 != 0): numRunners += 1
        if (r & 4 != 0): numRunners += 1
        return numRunners

    def getIsRunnerOnFirst(self):
        r = self.runnersOneBased - 1
        return (r & 1 != 0)

    def getKeyFromHomeRun(self):
        s = self.clone()
        # clear the bases, add runs
        runsToAdd = 1 + s.getNumRunners()
        s.runnersOneBased = 1
        s.runDiff += runsToAdd
        return s.getKey()

    def getKeyFromOut(self):
        s = self.clone()
        if (s.outs < 2):
            s.outs += 1
        else:
            # new inning
            s.outs = 0
            s.runnersOneBased = 1
            if s.inning >= 9 and s.runDiff < 0:
                # inning just ended and we're behind, so game is actually over
                # make sure we don't find this in our data
                return 0.0
            s.runDiff = -1 * s.runDiff
            if (s.homeOrVisitor == 'V'):
                s.homeOrVisitor = 'H'
            else:
                s.homeOrVisitor = 'V'
                s.inning += 1
        return s.getKey()

    def getKeyFromHit(self):
        s = self.clone()
        runnersISP = s.getNumRunnersInScoringPosition()
        s.runDiff += runnersISP
        if s.getIsRunnerOnFirst():
            s.runnersOneBased = 1 + 1 + 4
        else:
            s.runnersOneBased = 1 + 1
        return s.getKey()
    def getWinProb(self, homeOrVisitor=None):
        if homeOrVisitor is None:
            homeOrVisitor = self.homeOrVisitor
        if homeOrVisitor == self.homeOrVisitor:
            return float(self.winCount)/self.totalCount
        else:
            return 1.0-float(self.winCount)/self.totalCount
    # returns a list of tuples of (bool if it's good for the team, probability, key for next situation)
    def getLeverageKeys(self):
        # per http://www.hardballtimes.com/crucial-situations/, let's use
        # 3% home run
        # 27% single, runners advance two bases
        # 70% out
        return [(True, 0.03, self.getKeyFromHomeRun()), (True, 0.27, self.getKeyFromHit()), (False, 0.7, self.getKeyFromOut())]

def getProbabilityOfStringForYear(stringToLookFor, year):
    probsRe = re.compile(r'^%s,(\d+),(\d+)' % (stringToLookFor))
    fileName = pathPrefix + str(year)
    if not os.path.exists(fileName):
        return (0,0)
    with open(fileName, 'r') as probsFile:
        for line in probsFile.readlines():
            if (line.startswith(stringToLookFor)):
                probsMatch = probsRe.match(line)
                if (probsMatch):
                    totalGames = int(probsMatch.group(1))
                    winGames = int(probsMatch.group(2))
                    return (winGames, totalGames)
    return (0,0)

def getProbabilityOfString(stringToLookFor, startYear, endYear):
    # These are cumulative files, so from start-end inclusive is
    # (end cumulative) - ((start - 1) cumulative)
    (startWins, startTotal) = getProbabilityOfStringForYear(stringToLookFor, startYear - 1)
    (endWins, endTotal) = getProbabilityOfStringForYear(stringToLookFor, endYear)
    wins = endWins - startWins
    total = endTotal - startTotal
    return (wins, total)

def readData(filePath):
    data = {}
    with open(filePath, 'r') as f:
        for line in f.readlines():
            line = line[:-1]
            lineMatch = lineRe.match(line)
            if lineMatch is None:
                print(('x' + line + 'x'))
                assert False
            s = Situation(lineMatch)
            data[s.getKey()] = s
    return data

def calculateRawLeverage(data, situation, verbose=False):
    leverageKeys = situation.getLeverageKeys()
    startingWinProb = situation.getWinProb()
    if verbose:
        print(("Starting: " + str(startingWinProb)))
    leverage = 0.0
    for leverageKey in leverageKeys:
        isGood = leverageKey[0]
        prob = leverageKey[1]
        key = leverageKey[2]
        if verbose:
            print(key)
        winProb = None
        if key in data:
            winProb = data[key].getWinProb(situation.homeOrVisitor)
        elif type(key) is float:
            # hack
            winProb = key
        else:
            # assume whatever our run diff says goes
            fakeSituation = Situation.makeFromKey(key)
            winProb = 1.0 if (fakeSituation.homeOrVisitor == situation.homeOrVisitor) == (fakeSituation.runDiff >= 0) else 0.0
        if verbose:
            print(winProb)
        leverage += abs(winProb - startingWinProb) * prob
    return leverage


def main():
    fileNames = [x for x in os.listdir(directory) if fileNameRe.match(x)]
    fileName = sorted(fileNames)[-1]
    print(fileName)
    data = readData(os.path.join(directory, fileName))
    totalGames = 0
    for k in list(data.keys()):
        totalGames += data[k].totalCount
    print(totalGames)
    totalLeverage = 0.0
    for k in list(data.keys()):
        totalLeverage += calculateRawLeverage(data, data[k]) * data[k].totalCount
    averageLeverage = totalLeverage / totalGames
    print(averageLeverage)
    with open(os.path.join(directory, outputFileName), 'w') as f:
        for k in sorted(data.keys()):
            s = data[k]
            f.write('{0},{1:.2f}\n'.format(s.getFileString(), calculateRawLeverage(data, s)/averageLeverage))

    if True:
        k = ("H", 9, 2, 3, -1)
        s = data[k]
        print((calculateRawLeverage(data, s)))
        k = ("V", 1, 0, 1, 0)
        s = data[k]
        print((calculateRawLeverage(data, s)))
        k = ("H", 9, 0, 1, -21)
        s = data[k]
        print((calculateRawLeverage(data, s, True)))
        k = ("H", 1, 0, 1, -10)
        s = data[k]
        print((calculateRawLeverage(data, s, True)))


if (__name__ == '__main__'):
    main()
