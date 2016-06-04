#!/usr/bin/python
import re, sys, copy, getopt, os, os.path
import unittest

# Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff) to a tuple of
# (number of wins, number of situations)
# When outputting, add 1 to runners to comply with Birnbaum's data
#stats = {}
positionToBase = {1:-1, 2:-1, 3:1, 4:2, 5:3, 6:2, 7:-1, 8:-1, 9:-1}
numGames = 0
quiet = True
skipOutput = False

def gameSitString(gameSituation):
    return "inning: %d isHome: %d outs: %d curScoreDiff: %d runners: %s" % (gameSituation['inning'], gameSituation['isHome'], gameSituation['outs'], gameSituation['curScoreDiff'], gameSituation['runners'])

def initializeGame(gameSituation):
    gameSituation['inning'] = 1
    gameSituation['isHome'] = 0
    gameSituation['outs'] = 0
    # Runners on first, second, third
    gameSituation['runners'] = [0, 0, 0]
    # Number of runs the currently batting team is ahead by (can be negative)
    gameSituation['curScoreDiff'] = 0

def getKeyFromSituation(situation):
    return (situation['inning'], situation['isHome'], situation['outs'], (situation['runners'][0], situation['runners'][1], situation['runners'][2]), situation['curScoreDiff'])

def getSituationFromKey(key):
    situation = {}
    situation['inning'] = key[0]
    situation['isHome'] = key[1]
    situation['outs'] = key[2]
    situation['runners'] = [key[3][0], key[3][1], key[3][2]]
    situation['curScoreDiff'] = key[4]
    return situation

def addGameToStatsWinExpectancy(gameSituationKeys, finalGameSituation, stats, gameId):
    # Add gameKeys to stats
    # Check the last situation to see who won.
    if (finalGameSituation['isHome']):
        if (finalGameSituation['curScoreDiff'] > 0):
            homeWon = True
        elif (finalGameSituation['curScoreDiff'] < 0):
            homeWon = False
        else:
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
    else:
        if (finalGameSituation['curScoreDiff'] > 0):
            # FODO - can this really happen?
            homeWon = False
        elif (finalGameSituation['curScoreDiff'] < 0):
            homeWon = True
        else:
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
    for situationKey in gameSituationKeys:
        isHomeInning = situationKey[1]
        isWin = (isHomeInning and homeWon) or (not isHomeInning and not homeWon)
        if (situationKey in stats):
            (numWins, numSituations) = stats[situationKey]
            numSituations = numSituations + 1
            if (isWin):
                numWins = numWins + 1
            stats[situationKey] = (numWins, numSituations)
        else:
            if (isWin):
                numWins = 1
            else:
                numWins = 0
            stats[situationKey] = (numWins, 1)

def getNextInning(inning):
    if (inning[1]):
        return (inning[0]+1, 0)
    else:
        return (inning[0], 1)

def addGameToStatsRunExpectancyPerInning(gameSituationKeys, finalGameSituation, stats, gameId):
    inningsToKeys = {}
    for situationKey in gameSituationKeys:
        situation = getSituationFromKey(situationKey)
        key = (situation['inning'], situation['isHome'])
        if (key in inningsToKeys):
            inningsToKeys[key].append(situation)
        else:
            inningsToKeys[key] = [situation]
    for inning in inningsToKeys:
        startingRunDiff = inningsToKeys[inning][0]['curScoreDiff']
        if (getNextInning(inning) in inningsToKeys):
            endingRunDiff = -1 * inningsToKeys[getNextInning(inning)][0]['curScoreDiff']
        else:
            endingRunDiff = inningsToKeys[inning][-1]['curScoreDiff']
        if (endingRunDiff - startingRunDiff < 0):
            print "uh-oh - scored %d runs!" % (endingRunDiff - startingRunDiff)
            assert False
        # Add the statistics now.
        for situation in inningsToKeys[inning]:
            # Make sure we don't duplicate keys.
            keysUsed = []
            # Strip off the inning info (for now?) and the curScoreDiff
            keyToUse = getKeyFromSituation(situation)[2:4] 
            runsGained = endingRunDiff - situation['curScoreDiff']
            if (keyToUse in stats):
                while (len(stats[keyToUse]) < (runsGained + 1)):
                    stats[keyToUse].append(0)
            else:
                stats[keyToUse] = [0] * (runsGained + 1)
            stats[keyToUse][runsGained] += 1

def parseFile(f, reports):
    global numGames
    inGame = 0
    curGameSituation = {}
    gameSituationKeys = []
    curId = None
    for line in f.readlines():
        if (not(inGame)):
            if (line.startswith("id,")):
                curId = line[3:]
                initializeGame(curGameSituation)
                gameSituationKeys = []
                gameSituationKeys.append(getKeyFromSituation(curGameSituation))
                inGame = 1
                numGames = numGames + 1
        else:
            if (line.startswith("id,")):
                # Add gameKeys to stats
                for report in reports:
                    report[0](gameSituationKeys, curGameSituation, report[2], curId)
                if (not quiet):
                    print "NEW GAME"
                initializeGame(curGameSituation)
                curId = line[3:]
                gameSituationKeys = []
                gameSituationKeys.append(getKeyFromSituation(curGameSituation))
                numGames = numGames + 1
            else:
                if (line.startswith("play")):
                    try:
                        parsePlay(line, curGameSituation)
                    except AssertionError:
                        if (not quiet):
                            raise
                        else:
                            # We're just gonna punt and ignore the error
                            inGame = 0
                    else:
                        curGameSituationKey = getKeyFromSituation(curGameSituation)
                        if (curGameSituationKey not in gameSituationKeys):
                            gameSituationKeys.append(curGameSituationKey)
    for report in reports:
        report[0](gameSituationKeys, curGameSituation, report[2], curId)

def batterToFirst(runnerDests):
    runnerDests['B'] = 1
    if 1 in runnerDests:
        runnerDests[1] = 2
        if 2 in runnerDests:
            runnerDests[2] = 3
            if 3 in runnerDests:
                runnerDests[3] = 4
        else:
            if 3 in runnerDests:
                runnerDests[3] = 3
    else:
        if 2 in runnerDests:
            runnerDests[2] = 2
        if 3 in runnerDests:
            runnerDests[3] = 3
 
def parsePlay(line, gameSituation):
    playRe = re.compile(r'^play,(\d+),([01]),.*?,.*?,.*?,(.*)$')
    playMatch = playRe.match(line)
    # if runnerDests[x] = 0, runner (or batter) is out
    # if runnerDests[x] = 4, runner (or batter) scores
    # if runnerDests['B'] = -1, batter is still up
    # if runnerDests['B'] = -2, undetermined
    runnerDests = {}
    outAtBase = []
    defaultBatterBase = -1
    beginningRunners = []
    runnersDefaultStayStill = False
    if (gameSituation['runners'][0]):
        runnerDests[1] = -1
        beginningRunners.append(1)
    if (gameSituation['runners'][1]):
        runnerDests[2] = -1
        beginningRunners.append(2)
    if (gameSituation['runners'][2]):
        runnerDests[3] = -1
        beginningRunners.append(3)
    if (not quiet):
        print "Game situation is: %s" % gameSitString(gameSituation)
        print line[0:-1]
    assert playMatch
    assert gameSituation['inning'] == int(playMatch.group(1))
    assert gameSituation['isHome'] == int(playMatch.group(2))
    playString = playMatch.group(3)
    # Strip !'s, #'s, and ?'s
    playString = ''.join(playString.split('!'))
    playString = ''.join(playString.split('#'))
    playString = ''.join(playString.split('?'))
    playArray = playString.split('.')
    assert len(playArray) <= 2
    # Deal with the first part of the string.
    batterEvents = playArray[0].split(';')
    for batterEvent in batterEvents:
        batterEvent = batterEvent.strip()
    
        doneParsingEvent = False
        simpleHitMatch = re.match(r"^([SDTH])(?:\d|/)", batterEvent)
        simpleHitMatch2 = re.match(r"^([SDTH])\s*$", batterEvent)
        if (simpleHitMatch or simpleHitMatch2):
            if (simpleHitMatch):
                typeOfHit = simpleHitMatch.group(1)
            else:
                typeOfHit = simpleHitMatch2.group(1)
            if (typeOfHit == 'S'):
                runnerDests['B'] = 1
            elif (typeOfHit == 'D'):
                runnerDests['B'] = 2
            elif (typeOfHit == 'T'):
                runnerDests['B'] = 3
            elif (typeOfHit == 'H'):
                runnerDests['B'] = 4
                for runner in runnerDests:
                    runnerDests[runner] = 4
            # Sometimes these aren't specified - assume runners don't move
            runnersDefaultStayStill = True
            doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('HR')):
                runnerDests['B'] = 4
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = 4
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('K')):
                runnerDests['B'] = 0
                runnersDefaultStayStill = True
                if (batterEvent.startswith('K+')):
                    tempEvent = batterEvent[2:]
                    if (tempEvent.startswith('SB')):
                        if (tempEvent[2] == 'H'):
                            runnerDests[3] = 4
                        else:
                            dest = int(tempEvent[2])
                            assert (dest == 2 or dest == 3)
                            runnerDests[dest - 1] = dest
                    elif (tempEvent.startswith('CS')):
                        if (re.match('^CS.\([^)]*?E.*?\)', tempEvent)):
                            # Error, so no out.
                            if (tempEvent[2] == 'H'):
                                runnerDests[3] = 4
                            else:
                                dest = int(tempEvent[2])
                                assert (dest == 2 or dest == 3)
                                runnerDests[dest - 1] = dest
                        else:
                            if (tempEvent[2] == 'H'):
                                runnerDests[3] = 0
                            else:
                                dest = int(tempEvent[2])
                                assert (dest == 2 or dest == 3)
                                runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('POCS')):
                        if (re.match('^POCS.\([^)]*?E.*?\)', tempEvent)):
                            # Error, so no out.
                            if (tempEvent[4] == 'H'):
                                runnerDests[3] = 4
                            else:
                                base = int(tempEvent[4])
                                assert (base == 2 or base == 3)
                                runnerDests[base-1] = base
                        else:
                            if (tempEvent[4] == 'H'):
                                runnerDests[3] = 0
                            else:
                                base = int(tempEvent[4])
                                assert (base == 2 or base == 3)
                                runnerDests[base-1] = 0
                    elif (tempEvent.startswith('PO')):
                        if (re.match('^PO.\([^)]*?E.*?\)', tempEvent)):
                            # Error, so no out.
                            pass
                        else:
                            base = int(tempEvent[2])
                            assert (base == 1 or base == 2 or base == 3)
                            runnerDests[base] = 0
                    elif (tempEvent.startswith('PB') or tempEvent.startswith('WP')):
                        pass
                    elif (tempEvent.startswith('OA') or tempEvent.startswith('DI')):
                        pass
                    elif (tempEvent.startswith('E')):
                        pass
                    else:
                        print "ERROR - unrecognized K+ event: %s" % tempEvent
                        assert False
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('NP')):
                # No play
                runnerDests['B'] = -1
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = runner
                doneParsingEvent = True
        if (not doneParsingEvent):
            if ((batterEvent.startswith('W') and not batterEvent.startswith('WP')) or batterEvent.startswith('IW') or batterEvent.startswith('I')):
                # Walk
                runnerDests['B'] = 1
                batterToFirst(runnerDests)
                if (batterEvent.startswith('W+') or batterEvent.startswith('IW+') or batterEvent.startswith('I+')):
                    tempEvent = batterEvent[2:]
                    if (batterEvent.startswith('IW+')):
                        tempEvent = batterEvent[3:]
                    if (tempEvent.startswith('SB')):
                        sbArray = tempEvent.split(';')
                        for entry in sbArray:
                            if (entry[2] == 'H'):
                                runnerDests[3] = 4
                            else:
                                dest = int(entry[2])
                                assert (dest == 2 or dest == 3)
                                runnerDests[dest - 1] = dest 
                    elif (tempEvent.startswith('CS')):
                        if (re.match(r'^CS.\([^)]*?E.*?\)', tempEvent)):
                            # There was an error, so not an out.
                            if (tempEvent[2] == 'H'):
                                runnerDests[3] = 4
                            else:
                                dest = int(tempEvent[2])
                                assert (dest == 2 or dest == 3)
                                runnerDests[dest - 1] = dest
                        else:
                            if (tempEvent[2] == 'H'):
                                runnerDests[3] = 0
                            else:
                                dest = int(tempEvent[2])
                                assert (dest == 2 or dest == 3)
                                runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('POCS')):
                        if (tempEvent[4] == 'H'):
                            # ...this is weird
                            runnerDests[3] = 0
                        else:
                            base = int(tempEvent[4])
                            assert (base == 1 or base == 2 or base == 3)
                            runnerDests[base] = 0
                    elif (tempEvent.startswith('PO')):
                        base = int(tempEvent[2])
                        assert (base == 1 or base == 2 or base == 3)
                        runnerDests[base] = 0
                    elif (tempEvent.startswith('PB') or tempEvent.startswith('WP')):
                        pass
                    elif (tempEvent.startswith('OA') or tempEvent.startswith('DI')):
                        pass
                    elif (tempEvent.startswith('E')):
                        runnerDests['B'] = 1
                    else:
                        print "ERROR - unrecognized W+ or IW+ event: %s" % tempEvent
                        assert False
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('HP')):
                # Hit by pitch
                batterToFirst(runnerDests)
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('DGR')):
                # Ground-rule double
                runnerDests['B'] = 2
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('C/') or batterEvent == 'C'):
                # Catcher's interference
                runnerDests['B'] = 1
                doneParsingEvent = True
                runnersDefaultStayStill = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('E')):
                # Error letting the runner reach base
                runnerDests['B'] = 1 # may be overridden
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('FC')):
                # Fielder's choice.  Batter goes to first unless overridden
                runnerDests['B'] = 1 # may be overridden
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('FLE')):
                # Error on fly foul ball.  Nothing happens.
                runnerDests['B'] = -1
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = runner
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('SHE')):
                # Error on sac hit (bunt).  Advances given explicitly
                runnerDests['B'] = -2
                doneParsingEvent = True
        if (not doneParsingEvent):
            # double or triple play
            doublePlayMatch = re.match(r'^\d+\((\d|B)\)(?:\d*\((\d|B)\))?(?:\d*\((\d|B)\))?', batterEvent)
            if (doublePlayMatch and ('DP' in batterEvent or 'TP' in batterEvent)):
                if (not quiet):
                    print "double/triple play"
                # The batter is out if the last character is a number, not ')'
                # (unless there's a "(B)" in the string
                doublePlayString = batterEvent.split('/')[0]
                if (doublePlayString[-1:] != ')'):
                    runnerDests['B'] = 0
                else:
                    runnerDests['B'] = 1
                if (doublePlayMatch.group(1) == 'B'):
                    runnerDests['B'] = 0
                else:
                    runnerDests[int(doublePlayMatch.group(1))] = 0
                if (doublePlayMatch.group(2)):
                    if (doublePlayMatch.group(2) == 'B'):
                        runnerDests['B'] = 0
                    else:
                        runnerDests[int(doublePlayMatch.group(2))] = 0
                if (doublePlayMatch.group(3)):
                    if (doublePlayMatch.group(3) == 'B'):
                        runnerDests['B'] = 0
                    else:
                        runnerDests[int(doublePlayMatch.group(3))] = 0
                # Unfortunately, since it could be a caught fly ball and throw
                # out, we have to assume runners don't go anywhere.
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            weirdDoublePlayMatch = re.match(r'^\d+(/.*?)*/.?[DT]P', batterEvent)
            if (weirdDoublePlayMatch):
                # This is a double play.  The specifics of who's out will
                # come later.
                if (not quiet):
                    print "weird double/triple play"
                runnerDests['B'] = 0
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            simpleOutMatch = re.match("^\d\D", batterEvent)
            if (simpleOutMatch and "/FO" not in batterEvent or (len(batterEvent) == 1 and (int(batterEvent) >= 1 and int(batterEvent) <= 9))):
                if (not quiet):
                    print "simple out"
                if (re.match(r'^\dE', batterEvent)):
                    if (not quiet):
                        print "error"
                    runnerDests['B'] = 1
                else:
                    runnerDests['B'] = 0
                # runners don't move unless explicit
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = runner
                doneParsingEvent = True
        if (not doneParsingEvent):
            putOutMatch = re.match(r'^\d*(\d).*?(?:\((.)\))?', batterEvent)
            if (putOutMatch):
                if (not quiet):
                    print "Got a putout"
                if (re.search(r'\d?E\d', batterEvent)):
                    # Error on the play - batter goes to first unless
                    # explicit
                    runnerDests['B'] = 1
                else:
                    if ("/FO" in batterEvent):
                        # Force out - this means the thing in parentheses
                        # is the runner who is out.
                        if (not quiet):
                            print "force out"
                        assert putOutMatch.group(2)
                        runnerDests[int(putOutMatch.group(2))] = 0
                    else:
                        # Determine from putOutMatch.group(1) (who made out) and
                        # putOutMatch.group(2) (where out is) which base the out was at.
                        if (putOutMatch.group(2)):
                            outAtBase.append(putOutMatch.group(2))
                        else:
                            # If we don't know what base it was at, assume first base.
                            if (positionToBase[int(putOutMatch.group(1))] == -1):
                                outAtBase.append(1)
                            else:
                                outAtBase.append(positionToBase[int(putOutMatch.group(1))])
                    runnerDests['B'] = -2
                    defaultBatterBase = 1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('BK')):
                # Balk
                runnerDests['B'] = -1
                # Advance runners
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = runner + 1
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('CS')):
                # Caught stealing
                if (re.match(r'^CS.\([^)]*?E.*?\)', batterEvent)):
                    # There was an error, so not an out.
                    if (not quiet):
                        print "no caught stealing"
                    if (batterEvent[2] == 'H'):
                        runnerDests[3] = 4
                    else:
                        dest = int(batterEvent[2])
                        assert (dest == 2 or dest == 3)
                        runnerDests[dest - 1] = dest
                else:
                    if (batterEvent[2] == 'H'):
                        # out at home
                        outAtBase.append(4)
                    else:
                        dest = int(batterEvent[2])
                        assert (dest == 2 or dest == 3)
                        outAtBase.append(dest)
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('SB')):
                # stolen base (could be multiple)
                if (batterEvent[2] == 'H'):
                    runnerDests[3] = 4
                else:
                    dest = int(batterEvent[2])
                    assert(dest == 2 or dest == 3)
                    runnerDests[dest - 1] = dest
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('DI')):
                # defensive indifference.  runners resolved later
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                for runner in runnerDests:
                    if (runner != 'B' and runnerDests[runner] == -1):
                        runnerDests[runner] = runner
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('OA')):
                # runner advances somehow (resolved later)
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('PB') or batterEvent.startswith('WP')):
                # Passed ball or wild pitch
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = runner
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('POCS')):
                # Pick-off (and caught stealing)
                if (re.match(r'^POCS.\(.*?E.*?\)', batterEvent)):
                    # There was an error, so not an out
                    if (batterEvent[4] == 'H'):
                        runnerDests[3] = 4
                    else:
                        assert (int(batterEvent[4]) == 2 or int(batterEvent[4]) == 3)
                        runnerDests[int(batterEvent[4]) - 1] = int(batterEvent[4])
                else:
                    if (batterEvent[4] == 'H'):
                        # out at home
                        outAtBase.append(4)
                    else:
                        assert (int(batterEvent[4]) == 2 or int(batterEvent[4]) == 3)
                        outAtBase.append(int(batterEvent[4]))
                runnersDefaultStayStill = True
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('PO')):
                # Pick-off
                if (re.match('^PO.\([^)]*?E.*?\)', batterEvent)):
                    # Error, so no out.
                    pass
                else:
                    base = int(batterEvent[2])
                    assert (base == 1 or base == 2 or base == 3)
                    runnerDests[base] = 0
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            print "ERROR - couldn't parse event %s" % batterEvent
            print "line is: %s" % line[0:-1]
            return
    # Now parse runner stuff.
    if (len(playArray) > 1):
        runnerArray = playArray[1].split(';')
        runnerArray = [x.strip() for x in runnerArray]
        for runnerItem in runnerArray:
            if (len(runnerItem) != 3):
                assert (runnerItem[3] == '(')
            if (runnerItem[0] == 'B'):
                runner = 'B'
            else:
                runner = int(runnerItem[0])
                assert (runner >= 1 and runner <= 3)
            if (runnerItem[2] == 'H'):
                base = 4
            else:
                base = int(runnerItem[2])
                assert (base >= 1 and base <= 3)
            if (runnerItem[1] == '-'):
                if (runner != 'B' and base != 0):
                    # This looks weird, but sometimes a runner can go to the
                    # same base (a little redundant, but OK)
                    assert (runner <= base)
                runnerDests[runner] = base
            elif (runnerItem[1] == 'X'):
                # See if there was an error.
                if (re.match('^...(?:\([^)]*?\))*\(\d*E.*\)', runnerItem)):
                    #if (runner == 'B'):
                        # It seems to be the case that if it is the batter
                        # doing stuff, in this case the runner is safe
                        #runnerDests[runner] = base
                    # So this is probably an error.  See if the intervening
                    # parentheses indicate an out
                    if (re.match('^....*?\(\d*\).*?\(\d*E.*\)', runnerItem) or re.match('^....*?\(\d*E.*\)\(\d*\)', runnerItem)):
                        # Yup, this is really an out.
                        runnerDests[runner] = 0
                    else:
                        # Nope, so runner is safe.
                        if (runner != 'B' and base != 0):
                            # This looks weird, but sometimes a runner can go to the
                            # same base (a little redundant, but OK)
                            assert (runner <= base)
                        runnerDests[runner] = base
                else:
                    runnerDests[runner] = 0
            else:
                assert False
    unresolvedRunners = [runner for runner in runnerDests if runnerDests[runner] == -1]
    if ('B' in unresolvedRunners):
        unresolvedRunners.remove('B')
    if (runnerDests['B'] == -2):
        unresolvedRunners.append(0)
    # See if there's an out at a base.
    for outBase in outAtBase:
        if (outBase == 'B'):
            runnerDests['B'] = 0
            unresolvedRunners.remove(0)
        else:
            # Find the closest unresolved runner behind that base.
            possibleRunners = [runner for runner in unresolvedRunners if runner < outBase]
            curRunner = max(possibleRunners)
            if (not quiet):
                print "picked runner %d" % curRunner
            if (curRunner == 0):
                runnerDests['B'] = 0
                unresolvedRunners.remove(0)
            else:
                runnerDests[curRunner] = 0
                unresolvedRunners.remove(curRunner)
    unresolvedRunners = [runner for runner in runnerDests if runnerDests[runner] == -1]
    if (runnerDests['B'] == -2):
        if (defaultBatterBase != -1):
            if (not quiet):
                print "using defaultBatterBase of %d" % defaultBatterBase
            runnerDests['B'] = defaultBatterBase
        else:
            print "ERROR - unresolved batter!"
            assert False
    # 'B' going to -1 means nothing happens, so don't consider that.
    if ('B' in unresolvedRunners):
        unresolvedRunners.remove('B')
    if (len(unresolvedRunners) > 0):
        # We're OK if there will be three outs.
        outs = gameSituation['outs']
        for runner in runnerDests:
            if (runnerDests[runner] == 0):
                outs = outs + 1
        if (outs < 3):
            if (runnersDefaultStayStill):
                for runner in unresolvedRunners:
                    runnerDests[runner] = runner
            else:
                print "ERROR - unresolved runners %s!" % unresolvedRunners
                assert False
    # Check that no new entries to runnerDests
    newRunners = [runner for runner in runnerDests if runner not in beginningRunners]
    if ('B' not in newRunners):
        print "ERROR - don't know what happened to B!"
        assert False
    else:
        newRunners.remove('B')
    if (len(newRunners) > 0):
        print "ERROR - picked up extra runners %s!" % newRunners
        assert False
    newRunners = [0, 0, 0]
    # Deal with runnerDests
    for runner in runnerDests:
        if (runnerDests[runner] == 0):
            gameSituation['outs'] = gameSituation['outs'] + 1
        elif (runnerDests[runner] == 4):
            gameSituation['curScoreDiff'] = gameSituation['curScoreDiff'] + 1
        elif (runnerDests[runner] == -1):
            # Either we're the batter, and nothing happens, or
            # we don't know what happens, and it doesn't matter because there
            # are three outs.
            pass
        else:
            if (newRunners[runnerDests[runner] - 1] == 1):
                print "ERROR - already a runner at base %d!" % runnerDests[runner]
                assert False
            newRunners[runnerDests[runner] - 1] = 1
    if (gameSituation['outs'] >= 3):
        # new inning
        if (gameSituation['isHome'] == 1):
            gameSituation['isHome'] = 0
            gameSituation['inning'] = gameSituation['inning'] + 1
        else:
            gameSituation['isHome'] = 1
        gameSituation['outs'] = 0
        gameSituation['runners'] = [0, 0, 0]
        gameSituation['curScoreDiff'] = -1 * gameSituation['curScoreDiff']
    else:
        gameSituation['runners'] = newRunners
    # We're done - the information is "returned" in gameSituation

def findImprobableGame(gameSituationKeys, finalGameSituation, stats, gameId):
    if (finalGameSituation['isHome']):
        if (finalGameSituation['curScoreDiff'] > 0):
            homeWon = True
        elif (finalGameSituation['curScoreDiff'] < 0):
            homeWon = False
        else:
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
    else:
        if (finalGameSituation['curScoreDiff'] > 0):
            # FODO - can this really happen?
            homeWon = False
        elif (finalGameSituation['curScoreDiff'] < 0):
            homeWon = True
        else:
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
    if not homeWon:
        return
    if (9, True, 2, (0, 0, 0), -6) in gameSituationKeys:
        print "GOT IT with gameId:"
        print gameId
        sys.exit(0)

def usage():
    print "-t: just run tests"
    print "-v: verbose"
    print "-s: skip output, just parse everything"
    print "-h: help"
    print "-y: generate data sorted by year"

# This selects what stats we're compiling.
reportsToRun = [(addGameToStatsWinExpectancy, 'stats', {}), (addGameToStatsRunExpectancyPerInning, 'runsperinningstats', {})]
#reportsToRun = [(findImprobableGame, 'improbable', {})]
def main(args):
    global quiet, skipOutput, TestBatterToFirst
    sortByYear = False
    try:
        opts, files = getopt.getopt(args, 'vhsy')
    except getopt.GetoptError as err:
        print str(err)
        sys.exit(2)
    for o, a in opts:
        if o == '-h':
            usage()
            sys.exit(1)
        elif o == '-y':
            sortByYear = True
        elif o == '-v':
            quiet = False
        elif o == '-s':
            skipOutput = True
        else:
            assert False, "unhandled option: " + str(o)
    if sortByYear:
        yearsToFiles = {}
        for fileName in files:
            year = int(os.path.basename(fileName)[:4])
            if year not in yearsToFiles:
                yearsToFiles[year] = []
            yearsToFiles[year].append(fileName)
        for year in sorted(yearsToFiles):
            print year
            for report in reportsToRun:
                report[2].clear()
            for fileName in yearsToFiles[year]:
                print fileName
                eventFile = open(fileName, 'r')
                parseFile(eventFile, reportsToRun)
                eventFile.close()
            if not skipOutput:
                for report in reportsToRun:
                    outputFile = open('statsyears/' + report[1] + '.' + str(year), 'w')
                    statKeys = report[2].keys()
                    statKeys.sort()
                    for key in statKeys:
                        outputFile.write("%s: %s\n" % (key, report[2][key]))
                    outputFile.close()
    else:
        for fileName in files:
            #eventFileName = '2004COL.EVN'
            print fileName
            eventFile = open(fileName, 'r')
            parseFile(eventFile, reportsToRun)
            eventFile.close()
        print "numGames is %d" % numGames
        if not skipOutput:
            for report in reportsToRun:
                outputFile = open(report[1], 'w')
                statKeys = report[2].keys()
                statKeys.sort()
                for key in statKeys:
                    outputFile.write("%s: %s\n" % (key, report[2][key]))
                outputFile.close()

class TestBatterToFirst(unittest.TestCase):
    def util_test_expected(self, beginRunnerDests, endRunnerDests):
        rd = beginRunnerDests.copy()
        batterToFirst(rd)
        self.assertEqual(endRunnerDests, rd)

    def test_empty(self):
        self.util_test_expected({}, {'B': 1})

    def test_first(self):
        self.util_test_expected({1: 1}, {'B': 1, 1: 2})

    def test_second(self):
        self.util_test_expected({2: 2}, {'B': 1, 2: 2})

    def test_third(self):
        self.util_test_expected({3: 3}, {'B': 1, 3: 3})

    def test_firstSecond(self):
        self.util_test_expected({1: 1, 2: 2}, {'B': 1, 1: 2, 2: 3})

    def test_firstThird(self):
        self.util_test_expected({1: 1, 3: 3}, {'B': 1, 1: 2, 3: 3})

    def test_secondThird(self):
        self.util_test_expected({2: 2, 3: 3}, {'B': 1, 2: 2, 3: 3})

    def test_loaded(self):
        self.util_test_expected({1: 1, 2: 2, 3: 3}, {'B': 1, 1: 2, 2: 3, 3: 4})

class TestParsePlay(unittest.TestCase):
    def util_setup(self, outs, isHome, playString):
        inning = 1
        if isHome != True and isHome != False:
            self.fail('bad value for isHome')
        situation = {}
        initializeGame(situation)
        situation['inning'] = inning
        situation['isHome'] = 1 if isHome else 0
        situation['outs'] = outs
        return (situation, 'play,' + str(inning) + ',' + str(situation['isHome']) + ',,,,' + playString)
    
    def test_simpleout(self):
        (situation, playString) = self.util_setup(0, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_simpleout_oneout(self):
        (situation, playString) = self.util_setup(1, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 2
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_top(self):
        (situation, playString) = self.util_setup(2, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 0
        sitCopy['isHome'] = 1
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_bottom(self):
        (situation, playString) = self.util_setup(2, True, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 0
        sitCopy['isHome'] = 0
        sitCopy['inning'] = 2
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_top_clearrunners(self):
        (situation, playString) = self.util_setup(2, False, '8')
        situation['runners'][0] = 1
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 0
        sitCopy['isHome'] = 1
        sitCopy['runners'][0] = 0
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_bottom_clearrunners(self):
        (situation, playString) = self.util_setup(2, True, '8')
        situation['runners'][0] = 1
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 0
        sitCopy['isHome'] = 0
        sitCopy['inning'] = 2
        sitCopy['runners'][0] = 0
        self.assertEqual(sitCopy, situation)

    def test_forceout(self):
        (situation, playString) = self.util_setup(0, False, '83')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceFirstSecond(self):
        (situation, playString) = self.util_setup(0, False, '8.1-2')
        situation['runners'][0] = 1
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        sitCopy['runners'] = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThird(self):
        (situation, playString) = self.util_setup(0, False, '8.2-3')
        situation['runners'][1] = 1
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        sitCopy['runners'] = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_out_advanceThirdScore(self):
        (situation, playString) = self.util_setup(0, False, '8.3-H')
        situation['runners'][2] = 1
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThirdScore(self):
        (situation, playString) = self.util_setup(0, False, '8.2-3;3-H')
        situation['runners'] = [0, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        sitCopy['runners'] = [0, 0, 1]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThirdAllScore(self):
        (situation, playString) = self.util_setup(0, False, '8.2-H;3-H')
        situation['runners'] = [0, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['curScoreDiff'] = 2
        self.assertEqual(sitCopy, situation)

    def test_groundout_advance(self):
        (situation, playString) = self.util_setup(0, False, '54(B)/BG25/SH.1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        sitCopy['runners'] = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_groundout_safe_and_score(self):
        # TODO - fails, this is from spec
        return
        (situation, playString) = self.util_setup(0, False, 'FO/G5.3-H;B-1')
        situation['runners'] = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_explicit_sacrifice(self):
        (situation, playString) = self.util_setup(0, False, '23/SH.1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 1
        sitCopy['runners'] = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay(self):
        (situation, playString) = self.util_setup(0, False, '64(1)3/GDP/G6')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 2
        sitCopy['runners'] = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay_lineout(self):
        (situation, playString) = self.util_setup(0, False, '8(B)84(2)/LDP/L8')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 2
        sitCopy['runners'] = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay_lineout_unassisted(self):
        (situation, playString) = self.util_setup(0, False, '3(B)3(1)/LDP')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['outs'] = 2
        sitCopy['runners'] = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference_runner(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2.1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference_runner_explicit(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2.B-1;1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_pitchers_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E1')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_first_basemans_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E3')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_single(self):
        (situation, playString) = self.util_setup(0, False, 'S7')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_double(self):
        (situation, playString) = self.util_setup(0, False, 'D7/G5.3-H;2-H;1-H')
        situation['runners'] = [1, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 0]
        sitCopy['curScoreDiff'] = 3
        self.assertEqual(sitCopy, situation)

    def test_triple(self):
        (situation, playString) = self.util_setup(0, False, 'T9/F9LD.2-H')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 1]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_groundrule_double(self):
        (situation, playString) = self.util_setup(0, False, 'DGR/L9LS.2-H')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 0]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_throwing_error(self):
        (situation, playString) = self.util_setup(0, False, 'E1/TH/BG15.1-3')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_fielding_error(self):
        (situation, playString) = self.util_setup(0, False, 'E3.1-2;B-1')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_fielders_choice_out_at_home(self):
        (situation, playString) = self.util_setup(0, False, 'FC5/G5.3XH(52)')
        situation['runners'] = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_fielders_choice_no_outs(self):
        (situation, playString) = self.util_setup(0, False, 'FC3/G3S.3-H;1-2')
        situation['runners'] = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 1, 0]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_error_on_foul_ball(self):
        (situation, playString) = self.util_setup(0, False, 'FLE5/P5F')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_home_run(self):
        (situation, playString) = self.util_setup(0, False, 'H/L7D')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_home_run_explicit_runners(self):
        (situation, playString) = self.util_setup(0, False, 'HR/F78XD.2-H;1-H')
        situation['runners'] = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['curScoreDiff'] = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park(self):
        (situation, playString) = self.util_setup(0, False, 'HR9/F9LS.3-H;1-H')
        situation['runners'] = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['curScoreDiff'] = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park_just_h(self):
        (situation, playString) = self.util_setup(0, False, 'H9/F9LS.3-H;1-H')
        situation['runners'] = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['curScoreDiff'] = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park_just_h_no_runners(self):
        (situation, playString) = self.util_setup(0, False, 'H9/F9LS')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_hit_by_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'HP.1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_hit_by_pitch_no_runners(self):
        (situation, playString) = self.util_setup(0, False, 'HP')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_strikeout(self):
        (situation, playString) = self.util_setup(0, False, 'K')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout(self):
        (situation, playString) = self.util_setup(0, False, 'K23')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_passed_ball(self):
        (situation, playString) = self.util_setup(0, False, 'K+PB.1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_miscue(self):
        (situation, playString) = self.util_setup(0, False, 'K+WP.B-1')
        situation['runners'] = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout_other_runner_advance(self):
        (situation, playString) = self.util_setup(0, False, 'K23+WP.2-3')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 1]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_no_play(self):
        (situation, playString) = self.util_setup(0, False, 'NP')
        situation['runners'] = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_walk(self):
        (situation, playString) = self.util_setup(0, False, 'W.1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_intentional_walk(self):
        (situation, playString) = self.util_setup(0, False, 'IW')
        situation['runners'] = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_walk_wild_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'W+WP.2-3')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_balk(self):
        (situation, playString) = self.util_setup(0, False, 'BK.3-H;1-2')
        situation['runners'] = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 0]
        sitCopy['curScoreDiff'] = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing(self):
        (situation, playString) = self.util_setup(0, False, 'CSH(12)')
        situation['runners'] = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing_advance(self):
        (situation, playString) = self.util_setup(0, False, 'CS2(24).2-3')
        situation['runners'] = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 1]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing_error(self):
        (situation, playString) = self.util_setup(0, False, 'CS2(2E4).1-3')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_defensive_indifference(self):
        (situation, playString) = self.util_setup(0, False, 'DI.1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_other_advance(self):
        # "Thompson out trying to advance after ball eluded catcher"
        (situation, playString) = self.util_setup(0, False, 'OA.2X3(25)')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_wild_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'WP.2-3;1-2')
        situation['runners'] = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 1]
        self.assertEqual(sitCopy, situation)

    def test_passed_ball(self):
        (situation, playString) = self.util_setup(0, False, 'PB.2-3')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_pickoff(self):
        (situation, playString) = self.util_setup(0, False, 'PO2(14)')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)

    def test_pickoff_error(self):
        (situation, playString) = self.util_setup(0, False, 'PO1(E3).1-2')
        situation['runners'] = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_pickoff_caught_stealing(self):
        (situation, playString) = self.util_setup(0, False, 'POCS2(14)')
        situation['runners'] = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy['runners'] = [0, 0, 0]
        sitCopy['outs'] = 1
        self.assertEqual(sitCopy, situation)


if (__name__ == '__main__'):
    if (len(sys.argv) > 1 and sys.argv[1] == '-t'):
        # get rid of the -t
        unittest.main(argv=[sys.argv[0]] + sys.argv[2:])
    else:
        main(sys.argv[1:])


