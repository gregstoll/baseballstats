#!/usr/bin/python3

import re, os, cgi

pathPrefix = 'statsyears/statswithballsstrikescumulative.'
leverageFileName = 'statsyears/leverage'

def getProbabilityOfStringForYear(stringToLookFor, year):
    probsRe = re.compile(r'^%s,(\d+),(\d+)' % (stringToLookFor,))
    fileName = pathPrefix + str(year)
    if not os.path.exists(fileName):
        return (0,0)
    with open(fileName, 'r') as probsFile:
        # print(f"stringToLookFor is {stringToLookFor}")
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

def getLeverageOfString(stringToLookFor):
    leverageRe = re.compile(r'%s,([0-9.]+)' % (stringToLookFor,))
    with open(leverageFileName, 'r') as leverageFile:
        for line in leverageFile.readlines():
            if (line.startswith(stringToLookFor)):
                leverageMatch = leverageRe.match(line)
                if leverageMatch:
                    return float(leverageMatch.group(1))
    return 0.0 

def main():
    form = cgi.FieldStorage()
    stateString = form.getfirst('stateString')
    ballsStrikesState = form.getfirst('ballsStrikesState')
    startYear = form.getfirst('startYear')
    endYear = form.getfirst('endYear')
    (wins, total) = getProbabilityOfString(stateString + "," + ballsStrikesState, int(startYear), int(endYear))
    leverage = getLeverageOfString(stateString)
    # handled in apache config
    # print("Access-Control-Allow-Origin: *")
    print("Content-type: application/json\n")
    print('{"wins": %s, "total": %s, "leverage": %s}' % (wins, total, leverage), end='')

if (__name__ == '__main__'):
    main()
