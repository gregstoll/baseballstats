#!/usr/bin/python
import re

fileName = 'probs.txt'

def getProbability(homeOrVisitor, inning, outs, runners, scoreDiff):
    return getProbabilityOfString('"%s",%d,%d,%d,%d' % (homeOrVisitor, inning, outs, runners, scoreDiff))

def getProbabilityOfString(stringToLookFor):
    probsRe = re.compile(r'^%s,(\d+),(\d+)' % (stringToLookFor))
    probsFile = open(fileName, 'r')
    for line in probsFile.readlines():
        if (line.startswith(stringToLookFor)):
            probsMatch = probsRe.match(line)
            if (probsMatch):
                totalGames = int(probsMatch.group(1))
                winGames = int(probsMatch.group(2))
                probsFile.close()
                return float(winGames)/float(totalGames)
            else:
                print "ERROR - inconsistent re!"
    probsFile.close()
    return -1

if (__name__ == '__main__'):
    print getProbability('V', 1, 0, 1, 0)
