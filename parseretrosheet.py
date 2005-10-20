#!/usr/bin/python
import re

# Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff) to a tuple of
# (number of wins, number of situations)
# TODO - when outputting, add 1 to runners to comply with Birnbaum's data
stats = {}
positionToBase = {1:-1, 2:-1, 3:1, 4:2, 5:3, 6:2, 7:-1, 8:-1, 9:-1}

def initializeGame(gameSituation):
    gameSituation['inning'] = 1
    gameSituation['isHome'] = 0
    gameSituation['outs'] = 0
    gameSituation['runners'] = (0, 0, 0)
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
                initializeGame(gameSituation)
                gameKeys = []
            else:
                if (line.startswith("play")):
                    key = parsePlay(line, gameSituation)
                    if (key not in gameKeys):
                        gameKeys.append(key)
        #print line[0:-1]

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
    if (gameSituation['runners'][0]):
        runnerDests[1] = -1
    if (gameSituation['runners'][1]):
        runnerDests[2] = -1
    if (gameSituation['runners'][2]):
        runnerDests[3] = -1
    print line[0:-1]
    assert playMatch
    #assert gameSituation['inning'] == int(playMatch.group(1))
    #assert gameSituation['isHome'] == int(playMatch.group(2))
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
                runnerDests[runner] = 4
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('K')):
            runnerDests['B'] = 0
            for runner in runnerDests:
                runnerDests[runner] = 4
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('NP')):
            # No play
            runnerDests['B'] = -1
            for runner in runnerDests:
                runnerDests[runner] = runner
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('W') or batterEvent.startswith('IW')):
            # Walk
            runnerDests['B'] = 1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('HP')):
            # Hit by pitch
            runnerDests['B'] = 1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('DGR')):
            # Ground-rule double
            runnerDests['B'] = 2
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('C')):
            # Catcher's interference
            runnerDests['B'] = 1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('E')):
            # Error letting the runner reach base
            runnerDests['B'] = 1 # may be overridden
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('FC')):
            # Fielder's choice.  Batter goes to first unless overridden
            runnerDests['B'] = 1 # may be overridden
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('FLE')):
            # Error on fly foul ball.  Nothing happens.
            runnerDests['B'] = -1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('SHE')):
            # Error on sac hit (bunt).  Advances given explicitly
            runnerDests['B'] = -2
            doneParsingEvent = True
    if (not doneParsingEvent):
        # TODO - triple play here?
        doublePlayMatch = re.match(r'^\d\d?\((\d)\)', batterEvent)
        if (doublePlayMatch):
            runnerDests['B'] = 0
            # TODO
            #assert (int(doublePlayMatch.group(1)) in runnerDests)
            runnerDests[int(doublePlayMatch.group(1))] = 0
            doneParsingEvent = True
    if (not doneParsingEvent):
        lineDoublePlayMatch = re.match(r'^\d\(B\)(?:\d+\((\d)\))?(?:\d+\((\d)\))?', batterEvent)
        if (lineDoublePlayMatch):
            runnerDests['B'] = 0
            if (lineDoublePlayMatch.group(1)):
                #TODO
                #assert (int(lineDoublePlayMatch.group(1)) in runnerDests)
                runnerDests[int(lineDoublePlayMatch.group(1))] = 0
            if (lineDoublePlayMatch.group(2)):
                #TODO
                #assert (int(lineDoublePlayMatch.group(2)) in runnerDests)
                runnerDests[int(lineDoublePlayMatch.group(2))] = 0
            doneParsingEvent = True
    if (not doneParsingEvent):
        simpleOutMatch = re.match("^\d\D", batterEvent)
        if (simpleOutMatch):
            runnerDests['B'] = 0
            doneParsingEvent = True
    if (not doneParsingEvent):
        putOutMatch = re.match("^\d\d*(\d)(?:\((.)\))?", batterEvent)
        if (putOutMatch):
            # Determine from putOutMatch.group(1) (who made out) and
            # putOutMatch.group(2) (where out is) which base the out was at.
            if (putOutMatch.group(2)):
                outAtBase.append(putOutMatch.group(2))
            else:
                assert positionToBase[int(putOutMatch.group(2))] != -1
                outAtBase.append(positionToBase[int(putOutMatch.group(2))])
            runnerDests['B'] = -2
            defaultBatterBase = 1
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
            if (re.match(r'^CS.\(E')):
                # There was an error, so not an out.
                pass
            else:
                if (batterEvent[2] == 'H'):
                    # out at home
                    outAtBase.append(4)
                else:
                    assert (int(batterEvent[2]) == 2 or int(batterEvent[2]) == 3)
                    outAtBase.append(int(batterEvent[2]))
            runnerDests['B'] = -1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('SB')):
            # stolen base
            # TODO - advance runner(s)
            # TODO - handle double steals
            if (batterEvent[2] == 'H'):
                #runnerDests
            runnerDests['B'] = -1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('DI')):
            # defensive indifference.  runners resolved later
            runnerDests['B'] = -1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('OA')):
            # runner advances
            # TODO - advance runner(s)
            runnerDests['B'] = -1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('PB') or batterEvent.startswith('WP')):
            # Passed ball or wild pitch
            runnerDests['B'] = -1
            doneParsingEvent = True
    if (not doneParsingEvent):
        if (batterEvent.startswith('PO')):
            # Pick-off
            # TODO - get runner(s) out
            runnerDests['B'] = -1
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
                runnerDests[runner] = 0
            else:
                assert False
    unresolvedRunners = [runner for runner in runnerDests if runnerDests[runner] == -1]
    if ('B' in unresolvedRunners):
        unresolvedRunners.remove('B')
        unresolvedRunners.append(0)
    # See if there's an out at a base.
    for outBase in outAtBase:
        # Find the closest unresolved runner behind or equal to that base.
        possibleRunners = [runner for runner in unresolvedRunners if runner <= outBase]
        curRunner = max(possibleRunners)
        if (curRunner == 0):
            runnerDests['B'] = 0
            unresolvedRunners.remove('B')
        else:
            runnerDests[curRunner] = 0
            unresolvedRunners.remove(curRunner)
    unresolvedRunners = [runner for runner in runnerDests if runnerDests[runner] == -1]
    if (runnerDests['B'] == -2):
        if (defaultBatterBase != -1):
            runnerDests['B'] = defaultBatterBase
        else:
            print "ERROR - unresolved batter!"
            assert False
    # 'B' going to -1 means nothign happens, so don't consider that.
    if ('B' in unresolvedRunners):
        unresolvedRunners.remove('B')
    if (len(unresolvedRunners) > 0):
        print "ERROR - unresolved runners %s!" % unresolvedRunners
        assert False
    # TODO - deal with runnerDests, output the new situation (including
    # check for end of inning)
def main():
    eventFileName = 'sample'
    #eventFileName = '2004HOU.EVN'
    #eventFileName = '2004COL.EVN'
    eventFile = open(eventFileName, 'r')
    parseFile(eventFile)
    eventFile.close()


if (__name__ == '__main__'):
    main()
