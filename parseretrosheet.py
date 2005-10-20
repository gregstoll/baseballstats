#!/usr/bin/python
import re

# Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff) to a tuple of
# (number of wins, number of situations)
# TODO - when outputting, add 1 to runners to comply with Birnbaum's data
stats = {}
positionToBase = {1:-1, 2:-1, 3:1, 4:2, 5:3, 6:2, 7:-1, 8:-1, 9:-1}

def gameSitString(gameSituation):
    return "inning: %d isHome: %d outs: %d curScoreDiff: %d runners: %s" % (gameSituation['inning'], gameSituation['isHome'], gameSituation['outs'], gameSituation['curScoreDiff'], gameSituation['runners'])

def initializeGame(gameSituation):
    gameSituation['inning'] = 1
    gameSituation['isHome'] = 0
    gameSituation['outs'] = 0
    gameSituation['runners'] = [0, 0, 0]
    gameSituation['curScoreDiff'] = 0

def parseFile(file):
    inGame = 0
    gameSituation = {}
    curGameKeys = []
    for line in file.readlines():
        if (not(inGame)):
            if (line.startswith("id,")):
                # TODO - Add gameKeys to stats
                initializeGame(gameSituation)
                gameKeys = []
                inGame = 1
        else:
            if (line.startswith("id,")):
                # TODO - Add gameKeys to stats
                print "NEW GAME"
                initializeGame(gameSituation)
                gameKeys = []
            else:
                if (line.startswith("play")):
                    key = parsePlay(line, gameSituation)
                    if (key not in gameKeys):
                        gameKeys.append(key)
        #print line[0:-1]
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
    print "Game situation is: %s" % gameSitString(gameSituation)
    print line[0:-1]
    assert playMatch
    assert gameSituation['inning'] == int(playMatch.group(1))
    assert gameSituation['isHome'] == int(playMatch.group(2))
    playString = playMatch.group(3)
    playArray = playString.split('.')
    assert len(playArray) <= 2
    # Deal with the first part of the string.
    batterEvent = playArray[0]
    doneParsingEvent = False
    simpleHitMatch = re.match("^([SDTH])\d", batterEvent)
    if (simpleHitMatch):
        if (simpleHitMatch.group(1) == 'S'):
            runnerDests['B'] = 1
        elif (simpleHitMatch.group(1) == 'D'):
            runnerDests['B'] = 2
        elif (simpleHitMatch.group(1) == 'T'):
            runnerDests['B'] = 3
        elif (simpleHitMatch.group(1) == 'H'):
            runnerDests['B'] = 4
            for runner in runnerDests:
                runnerDests[runner] = 4
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
                elif (tempEvent.startswith('OA')):
                    pass
                elif (tempEvent.startswith('E')):
                    runnerDests['B'] = 1
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
        if ((batterEvent.startswith('W') and not batterEvent.startswith('WP'))or batterEvent.startswith('IW')):
            # Walk
            runnerDests['B'] = 1
            batterToFirst(runnerDests)
            if (batterEvent.startswith('W+') or batterEvent.startswith('IW+')):
                tempEvent = batterEvent[2:]
                if (batterEvent.startswith('IW+')):
                    tempEvent = batterEvent[3:]
                if (tempEvent.startswith('SB')):
                    if (tempEvent[2] == 'H'):
                        runnerDests[3] = 4
                    else:
                        dest = int(tempEvent[2])
                        assert (dest == 2 or dest == 3)
                        runnerDests[dest - 1] = dest 
                elif (tempEvent.startswith('CS')):
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
        doublePlayMatch = re.match(r'^\d\d*\((\d)\)(?:\d*\((\d)\))?', batterEvent)
        if (doublePlayMatch and ('DP' in batterEvent)):
            print "double play"
            # The batter is out if the last character is a number, not ')'
            doublePlayString = batterEvent.split('/')[0]
            if (doublePlayString[-1:] != ')'):
                runnerDests['B'] = 0
            else:
                runnerDests['B'] = 1
            runnerDests[int(doublePlayMatch.group(1))] = 0
            if (doublePlayMatch.group(2)):
                runnerDests[int(doublePlayMatch.group(2))] = 0
            doneParsingEvent = True
    if (not doneParsingEvent):
        lineDoublePlayMatch = re.match(r'^\d+\(B\)(?:\d+\((\d)\))?(?:\d+\((\d)\))?', batterEvent)
        if (lineDoublePlayMatch and 'DP' in batterEvent):
            print "double play"
            runnerDests['B'] = 0
            if (lineDoublePlayMatch.group(1)):
                assert (int(lineDoublePlayMatch.group(1)) in runnerDests)
                runnerDests[int(lineDoublePlayMatch.group(1))] = 0
            if (lineDoublePlayMatch.group(2)):
                assert (int(lineDoublePlayMatch.group(2)) in runnerDests)
                runnerDests[int(lineDoublePlayMatch.group(2))] = 0
            doneParsingEvent = True
    if (not doneParsingEvent):
        weirdDoublePlayMatch = re.match(r'^\d+/.DP', batterEvent)
        if (weirdDoublePlayMatch):
            # This is a double play.  The specifics of who's out will
            # come later.
            print "weird double play"
            runnerDests['B'] = 0
            runnersDefaultStayStill = True
            doneParsingEvent = True
    if (not doneParsingEvent):
        simpleOutMatch = re.match("^\d\D", batterEvent)
        if (simpleOutMatch and "/FO" not in batterEvent):
            print "simple out"
            if (re.match(r'^\dE', batterEvent)):
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
        putOutMatch = re.match("^\d*(\d)(?:\((.)\))?", batterEvent)
        if (putOutMatch and not 'DP' in batterEvent):
            print "Got a putout"
            if ("/FO" in batterEvent):
                # Force out - this means the thing in parentheses
                # is the runner who is out.
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
            if (re.match(r'^CS.\(.*?E', batterEvent)):
                # There was an error, so not an out.
                print "no caught stealing"
                if (batterEvent[2] == 'H'):
                    runnerDests[3] = 4
                else:
                    assert (int(batterEvent[2]) == 2 or int(batterEvent[2]) == 3)
                    runnerDests[int(batterEvent[2]) - 1] = int(batterEvent[2])
            else:
                if (batterEvent[2] == 'H'):
                    # out at home
                    outAtBase.append(4)
                else:
                    assert (int(batterEvent[2]) == 2 or int(batterEvent[2]) == 3)
                    outAtBase.append(int(batterEvent[2]))
            runnerDests['B'] = -1
            runnersDefaultStayStill = True
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('SB')):
            # stolen base (could be multiple)
            sbArray = batterEvent.split(';')
            for entry in sbArray:
                if (entry[2] == 'H'):
                    runnerDests[3] = 4
                else:
                    assert (int(entry[2]) == 2 or int(entry[2]) == 3)
                    runnerDests[int(entry[2]) - 1] = int(entry[2])
            runnerDests['B'] = -1
            runnersDefaultStayStill = True
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('DI')):
            # defensive indifference.  runners resolved later
            runnerDests['B'] = -1
            for runner in runnerDests:
                if (runner != 'B' and runnerDests[runner] == -1):
                    runnerDests[runner] = runner
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('OA')):
            # runner advances somehow (resolved later)
            runnerDests['B'] = -1
            runnersDefaultStayStill = True
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('PB') or batterEvent.startswith('WP')):
            # Passed ball or wild pitch
            runnerDests['B'] = -1
            for runner in runnerDests:
                if (runner != 'B'):
                    runnerDests[runner] = runner
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('POCS')):
            # Pick-off (and caught stealing)
            if (batterEvent[4] == 'H'):
                # out at home
                outAtBase.append(4)
            else:
                assert (int(batterEvent[4]) == 2 or int(batterEvent[4]) == 3)
                outAtBase.append(int(batterEvent[4]))
 
            runnersDefaultStayStill = True
            runnerDests['B'] = -1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('PO')):
            # Pick-off
            base = int(batterEvent[2])
            assert (base == 1 or base == 2 or base == 3)
            runnerDests[base] = 0
            runnerDests['B'] = -1
            for runner in runnerDests:
                if (runner != 'B' and runnerDests[runner] == -1):
                    runnerDests[runner] = runner
            doneParsingEvent = True
    if (not doneParsingEvent):
        print "ERROR - couldn't parse event %s" % batterEvent
        print "line is: %s" % line[0:-1]
        return ()
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
                if (re.match('^...\(\d*E.*\)', runnerItem)):
                    # Yup, so runner is safe.
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
        # Find the closest unresolved runner behind or equal to that base.
        possibleRunners = [runner for runner in unresolvedRunners if runner <= outBase]
        curRunner = max(possibleRunners)
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
    # TODO - return the key or something
    return ()

def main():
    #eventFileName = 'sample'
    eventFileName = '2004HOU.EVN'
    #eventFileName = '2004COL.EVN'
    eventFile = open(eventFileName, 'r')
    parseFile(eventFile)
    eventFile.close()


if (__name__ == '__main__'):
    main()
