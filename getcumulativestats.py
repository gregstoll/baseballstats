#!/usr/bin/python
from __future__ import print_function
import re, os, cgi

pathPrefix = 'statsyears/statscumulative.'

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

def main():
    form = cgi.FieldStorage()
    stateString = form.getfirst('stateString')
    startYear = form.getfirst('startYear')
    endYear = form.getfirst('endYear')
    (wins, total) = getProbabilityOfString(stateString, int(startYear), int(endYear))
    print("Content-type: application/json\n")
    print('{"wins": %s, "total": %s}' % (wins, total), end='')

if (__name__ == '__main__'):
    main()
