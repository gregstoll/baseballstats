#!/usr/bin/python
import re, sys

# Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff) to a tuple of
# (number of wins, number of situations)
# TODO - when outputting, add 1 to runners to comply with Birnbaum's data
stats = {}
positionToBase = {1:-1, 2:-1, 3:1, 4:2, 5:3, 6:2, 7:-1, 8:-1, 9:-1}
numGames = 0
quiet = 0

def gameSitString(gameSituation):
    return "inning: %d isHome: %d outs: %d curScoreDiff: %d runners: %s" % (gameSituation['inning'], gameSituation['isHome'], gameSituation['outs'], gameSituation['curScoreDiff'], gameSituation['runners'])

def initializeGame(gameSituation):
    gameSituation['inning'] = 1
    gameSituation['isHome'] = 0
    gameSituation['outs'] = 0
    gameSituation['runners'] = [0, 0, 0]
    gameSituation['curScoreDiff'] = 0

def getKeyFromSituation(situation):
    return (situation['inning'], situation['isHome'], situation['outs'], (situation['runners'][0], situation['runners'][1], situation['runners'][2]), situation['curScoreDiff'])

def addGameToStats(gameKeys, gameSituation):
    # Add gameKeys to stats
    # Check the last situation to see who won.
    if (gameSituation['isHome']):
        if (gameSituation['curScoreDiff'] > 0):
            homeWon = True
        elif (gameSituation['curScoreDiff'] < 0):
            homeWon = False
        else:
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
    else:
        if (gameSituation['curScoreDiff'] > 0):
            # TODO - can this really happen?
            homeWon = False
        elif (gameSituation['curScoreDiff'] < 0):
            homeWon = True
        else:
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
    for situationKey in gameKeys:
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

def parseFile(file):
    global numGames
    inGame = 0
    gameSituation = {}
    curGameKeys = []
    for line in file.readlines():
        if (not(inGame)):
            if (line.startswith("id,")):
                initializeGame(gameSituation)
                gameKeys = []
                gameKeys.append(getKeyFromSituation(gameSituation))
                inGame = 1
                numGames = numGames + 1
        else:
            if (line.startswith("id,")):
                # Add gameKeys to stats
                addGameToStats(gameKeys, gameSituation)
                if (not quiet):
                    print "NEW GAME"
                initializeGame(gameSituation)
                gameKeys = []
                gameKeys.append(getKeyFromSituation(gameSituation))
                numGames = numGames + 1
            else:
                if (line.startswith("play")):
                    parsePlay(line, gameSituation)
                    key = getKeyFromSituation(gameSituation)
                    if (key not in gameKeys):
                        gameKeys.append(key)
    addGameToStats(gameKeys, gameSituation)

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
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = runner
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
                        # TODO - is this ok?
                        #runnerDests['B'] = 1
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

def main(files):
    global quiet
    if (files[0] == '-q'):
        quiet = 1
        #files = files[1:]
        del files[0]
    for fileName in files:
        #eventFileName = '2004COL.EVN'
        print fileName
        eventFile = open(fileName, 'r')
        parseFile(eventFile)
        eventFile.close()
    print "numGames is %d" % numGames
    outputFile = open('stats', 'w')
    statKeys = stats.keys()
    statKeys.sort()
    for key in statKeys:
        outputFile.write("%s: %s\n" % (key, stats[key]))
    outputFile.close()

if (__name__ == '__main__'):
    main(sys.argv[1:])
