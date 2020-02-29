#!/usr/bin/python3
import re, sys, copy, getopt, os, os.path
import unittest
import typing
from enum import IntEnum

class Verbosity(IntEnum):
    quiet = 0
    normal = 1
    verbose = 2
#TODO - use __all__
#TODO - do something with these
positionToBase = {1:-1, 2:-1, 3:1, 4:2, 5:3, 6:2, 7:-1, 8:-1, 9:-1}
verbosity = Verbosity.normal
skipOutput = False
stopOnFirstError = False
sortByYear = False
knownBadGames = ['WS2196605270', 'MIL197107272', 'MON197108040', 'NYN198105090', 'SEA200709261', 'MIL201304190', 'SFN201407300', 'BAL201906250']

# TODO - make this a real class I guess
GameSituationKey = typing.Tuple[int, bool, int, typing.Tuple[int, int, int], int]
class GameSituation:
    def __init__(self):
        self.inning = 1
        self.isHome = False
        self.outs = 0
        # Runners on first, second, third
        self.runners = [0, 0, 0]
        # Number of runs the currently batting team is ahead by (can be negative)
        self.curScoreDiff = 0

    def copy(self):
        return GameSituation.fromKey(self.getKey())

    def __str__(self):
        return "inning: %d isHome: %d outs: %d curScoreDiff: %d runners: %s" % (self.inning, self.isHome, self.outs, self.curScoreDiff, self.runners)

    def __repr__(self):
        return str(self)

    def getKey(self) -> GameSituationKey:
        return (self.inning, self.isHome, self.outs, (self.runners[0], self.runners[1], self.runners[2]), self.curScoreDiff)

    def __eq__(self, other):
        return self.getKey() == other.getKey()

    @staticmethod
    def fromKey(key: GameSituationKey) -> 'GameSituation':
        situation = GameSituation()
        situation.inning = key[0]
        situation.isHome = key[1]
        situation.outs = key[2]
        situation.runners = [key[3][0], key[3][1], key[3][2]]
        situation.curScoreDiff = key[4]
        return situation

    def nextInningIfThreeOuts(self):
        if (self.outs >= 3):
            if (self.isHome):
                self.isHome = False
                self.inning = self.inning + 1
            else:
                self.isHome = True
            self.outs = 0
            self.runners = [0, 0, 0]
            self.curScoreDiff = -1 * self.curScoreDiff

    # returns True, False, or None if it's still tied.
    def isHomeWinning(self):
        if (self.curScoreDiff == 0):
            # This game must have been tied when it stopped.
            return None
        if (self.isHome):
            return self.curScoreDiff > 0
        else:
            return self.curScoreDiff < 0

class GameSituationKeyAndNextPlayLine(typing.NamedTuple):
    situationKey: GameSituationKey
    playLine: str
    def __str__(self):
        return f"situationKey: {self.situationKey} playLine: {self.playLine}"
    def __repr__(self):
        return self.__str__()

def parseFile(f: typing.IO[str], reports: typing.Iterable['Report']) -> int:
    numGames = 0
    inGame = False
    curGameSituation : GameSituation = GameSituation()
    gameSituationKeys : typing.List[GameSituationKey] = []
    playLines : typing.List[str] = []
    curId : str = ""
    for line in f.readlines():
        if (not(inGame)):
            if (line.startswith("id,")):
                curId = line[3:].strip()
                curGameSituation = GameSituation()
                gameSituationKeys = []
                gameSituationKeys.append(curGameSituation.getKey())
                playLines = []
                inGame = True
                numGames = numGames + 1
        else:
            if (line.startswith("id,")):
                assert curId != ""
                callReportsProcessedGame(gameSituationKeys, curGameSituation, reports, curId, playLines)
                if (verbosity == Verbosity.verbose):
                    print("NEW GAME")
                curGameSituation = GameSituation()
                curId = line[3:].strip()
                gameSituationKeys = []
                gameSituationKeys.append(curGameSituation.getKey())
                playLines = []
                numGames = numGames + 1
            else:
                if (line.startswith("play")):
                    try:
                        parsePlay(line, curGameSituation)
                    except AssertionError:
                        print("Error in game " + curId)
                        if (curId in knownBadGames):
                            print("known bad game")
                        if (curId not in knownBadGames and (verbosity == Verbosity.verbose or stopOnFirstError)):
                            raise
                        else:
                            # We're just gonna punt and ignore the error
                            inGame = False
                    else:
                        curGameSituationKey = curGameSituation.getKey()
                        if (curGameSituationKey not in gameSituationKeys):
                            gameSituationKeys.append(curGameSituationKey)
                            playLines.append(line.strip())
    if numGames == 0:
        return 0
    assert curId != ""
    callReportsProcessedGame(gameSituationKeys, curGameSituation, reports, curId, playLines)
    return numGames

def callReportsProcessedGame(gameSituationKeys: typing.List[GameSituationKey], finalGameSituation: GameSituation, reports: typing.Iterable['Report'], curId: str, playLines: typing.List[str]) -> None:
    # Don't include the last situation in the list of keys, because it's one after the last inning probably
    if (len(gameSituationKeys) > 0 and gameSituationKeys[-1] == finalGameSituation.getKey()):
        gameSituationKeys = gameSituationKeys[:-1]
    assert len(gameSituationKeys) == len(playLines)
    situationKeysAndNextPlayLines : typing.List[GameSituationKeyAndNextPlayLine] = [GameSituationKeyAndNextPlayLine(key, line) for (key, line) in zip(gameSituationKeys, playLines)]
    for report in reports:
        report.processedGame(curId, finalGameSituation, situationKeysAndNextPlayLines)

def batterToFirst(runnerDests) -> None:
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
 
def characterToBase(ch) -> int:
    if ch == 'H':
        return 4
    return int(ch)

# decription of the format is at http://www.retrosheet.org/eventfile.htm
playRe = re.compile(r'^play,\s?(\d+),\s?([01]),.*?,.*?,.*?,(.*)$')
simpleHitRe = re.compile(r"^([SDTH])(?:\d|/)")
simpleHit2Re = re.compile(r"^([SDTH])\s*$")
doublePlayRe = re.compile(r'^\d+\((\d|B)\)(?:\d*\((\d|B)\))?(?:\d*\((\d|B)\))?')
weirdDoublePlayRe = re.compile(r'^\d+(/.*?)*/.?[DT]P')
simpleOutRe = re.compile(r'^\d\D')
putOutRe = re.compile(r'^\d*(\d).*?(?:\((.)\))?')

def parsePlay(line: str, gameSituation: GameSituation):
    global playRe, simpleHitRe, simpleHit2Re, doublePlayRe, weirdDoublePlayRe, simpleOutRe, putOutRe
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
    if (gameSituation.runners[0]):
        runnerDests[1] = -1
        beginningRunners.append(1)
    if (gameSituation.runners[1]):
        runnerDests[2] = -1
        beginningRunners.append(2)
    if (gameSituation.runners[2]):
        runnerDests[3] = -1
        beginningRunners.append(3)
    if (verbosity == Verbosity.verbose):
        print("Game situation is: %s" % gameSituation)
        print(line[0:-1])
    assert playMatch
    assert gameSituation.inning == int(playMatch.group(1))
    assert gameSituation.isHome == (int(playMatch.group(2)) == 1)
    playString = playMatch.group(3)
    # Strip !'s, #'s, and ?'s
    playString = playString.replace('!', '').replace('#', '').replace('?', '')
    playArray = playString.split('.')
    assert len(playArray) <= 2
    # Deal with the first part of the string.
    batterEvents = playArray[0].split(';')
    for batterEvent in batterEvents:
        batterEvent = batterEvent.strip()
    
        doneParsingEvent = False
        simpleHitMatch = simpleHitRe.match(batterEvent)
        simpleHitMatch2 = simpleHit2Re.match(batterEvent)
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
                if (batterEvent.startswith('K+') or batterEvent.startswith('K23+')):
                    if batterEvent.startswith('K+'):
                        tempEvent = batterEvent[2:]
                    else:
                        tempEvent = batterEvent[4:]
                    if (tempEvent.startswith('SB')):
                        dest = characterToBase(tempEvent[2])
                        assert (dest == 2 or dest == 3 or dest == 4)
                        runnerDests[dest - 1] = dest
                    elif (tempEvent.startswith('CS')):
                        if (re.match(r'^CS.\([^)]*?E.*?\)', tempEvent)):
                            # Error, so no out.
                            dest = characterToBase(tempEvent[2])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = dest
                        else:
                            dest = characterToBase(tempEvent[2])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('POCS')):
                        if (re.match(r'^POCS.\([^)]*?E.*?\)', tempEvent)):
                            # Error, so no out.
                            dest = characterToBase(tempEvent[4])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = dest
                        else:
                            dest = characterToBase(tempEvent[4])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('PO')):
                        if (re.match(r'^PO.\([^)]*?E.*?\)', tempEvent)):
                            # Error, so no out.
                            pass
                        else:
                            base = characterToBase(tempEvent[2])
                            assert (base == 1 or base == 2 or base == 3)
                            runnerDests[base] = 0
                    elif (tempEvent.startswith('PB') or tempEvent.startswith('WP')):
                        pass
                    # OBA is used instead of OA in BOS196704300
                    elif (tempEvent.startswith('OA') or tempEvent.startswith('OBA') or tempEvent.startswith('DI')):
                        pass
                    elif (tempEvent.startswith('E')):
                        pass
                    else:
                        print("ERROR - unrecognized K+ event: %s" % tempEvent)
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
                            dest = characterToBase(entry[2])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = dest
                    elif (tempEvent.startswith('CS')):
                        if (re.match(r'^CS.\([^)]*?E.*?\)', tempEvent)):
                            # There was an error, so not an out.
                            dest = characterToBase(tempEvent[2])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = dest
                        else:
                            dest = characterToBase(tempEvent[2])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('POCS')):
                        dest = characterToBase(tempEvent[4])
                        assert (dest == 2 or dest == 3 or dest == 4)
                        runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('PO')):
                        base = characterToBase(tempEvent[2])
                        assert (base == 1 or base == 2 or base == 3)
                        runnerDests[base] = 0
                    elif (tempEvent.startswith('PB') or tempEvent.startswith('WP')):
                        pass
                    elif (tempEvent.startswith('OA') or tempEvent.startswith('DI')):
                        pass
                    elif (tempEvent.startswith('E')):
                        runnerDests['B'] = 1
                    else:
                        print("ERROR - unrecognized W+ or IW+ event: %s" % tempEvent)
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
            doublePlayMatch = doublePlayRe.match(batterEvent)
            if (doublePlayMatch and ('DP' in batterEvent or 'TP' in batterEvent)):
                if (verbosity == Verbosity.verbose):
                    print("double/triple play")
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
            weirdDoublePlayMatch = weirdDoublePlayRe.match(batterEvent)
            if (weirdDoublePlayMatch):
                # This is a double play.  The specifics of who's out will
                # come later.
                if (verbosity == Verbosity.verbose):
                    print("weird double/triple play")
                runnerDests['B'] = 0
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            simpleOutMatch = simpleOutRe.match(batterEvent)
            if (simpleOutMatch and "/FO" not in batterEvent or (len(batterEvent) == 1 and (int(batterEvent) >= 1 and int(batterEvent) <= 9))):
                if (verbosity == Verbosity.verbose):
                    print("simple out")
                if (re.match(r'^\dE', batterEvent)):
                    if (verbosity == Verbosity.verbose):
                        print("error")
                    runnerDests['B'] = 1
                else:
                    runnerDests['B'] = 0
                # runners don't move unless explicit
                for runner in runnerDests:
                    if (runner != 'B'):
                        runnerDests[runner] = runner
                doneParsingEvent = True
        if (not doneParsingEvent):
            putOutMatch = putOutRe.match(batterEvent)
            if (putOutMatch):
                if (verbosity == Verbosity.verbose):
                    print("Got a putout")
                if (re.search(r'\d?E\d', batterEvent)):
                    # Error on the play - batter goes to first unless
                    # explicit
                    runnerDests['B'] = 1
                else:
                    foundBatterDest = False
                    if ("/FO" in batterEvent):
                        # Force out - this means the thing in parentheses
                        # is the runner who is out.
                        if (verbosity == Verbosity.verbose):
                            print("force out")
                        assert putOutMatch.group(2)
                        runnerDests[int(putOutMatch.group(2))] = 0
                    else:
                        # Determine from putOutMatch.group(1) (who made out) and
                        # putOutMatch.group(2) (where out is) which base the out was at.
                        if (putOutMatch.group(2)):
                            runnerOut = putOutMatch.group(2)
                            if runnerOut != 'B':
                                runnerOut = int(runnerOut)
                            else:
                                foundBatterDest = True
                            runnerDests[runnerOut] = 0
                        else:
                            # If we don't know what base it was at, assume first base.
                            if (positionToBase[int(putOutMatch.group(1))] == -1):
                                outAtBase.append(1)
                            else:
                                outAtBase.append(positionToBase[int(putOutMatch.group(1))])
                    if (not foundBatterDest):
                        runnerDests['B'] = -2
                    defaultBatterBase = 1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('BK')):
                # Balk
                runnerDests['B'] = -1
                # Advance runners
                # actually, this should be explicit, game NYA196209092
                # has a balk where the runner doesn't advance from
                # second??
                #for runner in runnerDests:
                #    if (runner != 'B'):
                #        runnerDests[runner] = runner + 1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('CS')):
                # Caught stealing
                if (re.match(r'^CS.\([^)]*?E.*?\)', batterEvent)):
                    # There was an error, so not an out.
                    if (verbosity == Verbosity.verbose):
                        print("no caught stealing")
                    dest = characterToBase(batterEvent[2])
                    assert (dest == 2 or dest == 3 or dest == 4)
                    runnerDests[dest - 1] = dest
                else:
                    dest = characterToBase(batterEvent[2])
                    assert (dest == 2 or dest == 3 or dest == 4)
                    outAtBase.append(dest)
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('SB')):
                # stolen base (could be multiple)
                dest = characterToBase(batterEvent[2])
                assert(dest == 2 or dest == 3 or dest == 4)
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
                    dest = characterToBase(batterEvent[4])
                    assert (dest == 2 or dest == 3 or dest == 4)
                    runnerDests[dest - 1] = dest
                else:
                    dest = characterToBase(batterEvent[4])
                    assert (dest == 2 or dest == 3 or dest == 4)
                    outAtBase.append(dest)
                runnersDefaultStayStill = True
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                doneParsingEvent = True
        if (not doneParsingEvent):
            if (batterEvent.startswith('PO')):
                # Pick-off
                if (re.match(r'^PO.\([^)]*?E.*?\)', batterEvent)):
                    # Error, so no out.
                    pass
                else:
                    base = characterToBase(batterEvent[2])
                    assert (base == 1 or base == 2 or base == 3)
                    runnerDests[base] = 0
                if ('B' not in runnerDests):
                    runnerDests['B'] = -1
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            print("ERROR - couldn't parse event %s" % batterEvent)
            print("line is: %s" % line[0:-1])
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
            base = characterToBase(runnerItem[2])
            assert (base >= 1 and base <= 4)
            if (runnerItem[1] == '-'):
                if (runner != 'B' and base != 0):
                    # This looks weird, but sometimes a runner can go to the
                    # same base (a little redundant, but OK)
                    assert (typing.cast(int, runner) <= base)
                runnerDests[runner] = base
            elif (runnerItem[1] == 'X'):
                # See if there was an error.
                if (re.match(r'^...(?:\([^)]*?\))*\(\d*E.*\)', runnerItem)):
                    #if (runner == 'B'):
                        # It seems to be the case that if it is the batter
                        # doing stuff, in this case the runner is safe
                        #runnerDests[runner] = base
                    # So this is probably an error.  See if the intervening
                    # parentheses indicate an out
                    if (re.match(r'^....*?\(\d*(/TH)?\).*?\(\d*E.*\)', runnerItem) or re.match(r'^....*?\(\d*E.*\)\(\d*\)', runnerItem)):
                        # Yup, this is really an out.
                        runnerDests[runner] = 0
                    else:
                        # Nope, so runner is safe.
                        if (runner != 'B' and base != 0):
                            # This looks weird, but sometimes a runner can go to the
                            # same base (a little redundant, but OK)
                            assert (typing.cast(int, runner) <= base)
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
            if (verbosity == Verbosity.verbose):
                print("picked runner %d" % curRunner)
            if (curRunner == 0):
                runnerDests['B'] = 0
                unresolvedRunners.remove(0)
            else:
                runnerDests[curRunner] = 0
                unresolvedRunners.remove(curRunner)
    unresolvedRunners = [runner for runner in runnerDests if runnerDests[runner] == -1]
    if (runnerDests['B'] == -2):
        if (defaultBatterBase != -1):
            if (verbosity == Verbosity.verbose):
                print("using defaultBatterBase of %d" % defaultBatterBase)
            runnerDests['B'] = defaultBatterBase
        else:
            print("ERROR - unresolved batter!")
            assert False
    # 'B' going to -1 means nothing happens, so don't consider that.
    if ('B' in unresolvedRunners):
        unresolvedRunners.remove('B')
    if (len(unresolvedRunners) > 0):
        # We're OK if there will be three outs.
        outs = gameSituation.outs
        for runner in runnerDests:
            if (runnerDests[runner] == 0):
                outs = outs + 1
        if (outs < 3):
            if (runnersDefaultStayStill):
                for runner in unresolvedRunners:
                    runnerDests[runner] = runner
            else:
                print("ERROR - unresolved runners %s!" % unresolvedRunners)
                print("runnerDests: %s" % (runnerDests))
                assert False
    # Check that no new entries to runnerDests
    newRunners = [runner for runner in runnerDests if runner not in beginningRunners]
    if (verbosity == Verbosity.verbose):
        print("runnerDests: %s" % (runnerDests))
    if ('B' not in newRunners):
        print("ERROR - don't know what happened to B!")
        assert False
    else:
        newRunners.remove('B')
    if (len(newRunners) > 0):
        print("ERROR - picked up extra runners %s!" % newRunners)
        assert False
    newRunners = [0, 0, 0]
    # Deal with runnerDests
    for runner in runnerDests:
        if (runnerDests[runner] == 0):
            gameSituation.outs += 1
        elif (runnerDests[runner] == 4):
            gameSituation.curScoreDiff += 1
        elif (runnerDests[runner] == -1):
            # Either we're the batter, and nothing happens, or
            # we don't know what happens, and it doesn't matter because there
            # are three outs.
            pass
        else:
            if (newRunners[runnerDests[runner] - 1] == 1):
                print("ERROR - already a runner at base %d!" % runnerDests[runner])
                assert False
            newRunners[runnerDests[runner] - 1] = 1
    gameSituation.runners = newRunners
    gameSituation.nextInningIfThreeOuts()
    # We're done - the information is "returned" in gameSituation

class BallStrikeCount(typing.NamedTuple):
    balls: int
    strikes: int
    def __str__(self):
        return f"{self.balls} balls, {self.strikes} strikes"
    # This is what gets serialized to the file, so make it look like a tuple
    def __repr__(self):
        return f"({self.balls}, {self.strikes})"
    def addBall(self) -> 'BallStrikeCount':
        return BallStrikeCount(self.balls + 1, self.strikes)
    def addStrike(self) -> 'BallStrikeCount':
        return BallStrikeCount(self.balls, self.strikes + 1)


def assertOnlySingleCharacterStringsInSet(s : typing.Set[str]) -> None:
    for x in s:
        assert(len(x) == 1)

# This is surprisingly complicated because there's a lot of extraneous stuff in here.
# Ignore irrelevant stuff as well as the final result of a pitch (if it goes in play)
BALL_STRIKE_IGNORE_CHARS : typing.Set[str] = set([x for x in '!#?+*.123>HNXY '])
assertOnlySingleCharacterStringsInSet(BALL_STRIKE_IGNORE_CHARS)
BALL_STRIKE_BALLS : typing.Set[str] = set([x for x in 'BIPV'])
assertOnlySingleCharacterStringsInSet(BALL_STRIKE_BALLS)
BALL_STRIKE_STRIKES : typing.Set[str] = set([x for x in 'CKLMOQST'])
assertOnlySingleCharacterStringsInSet(BALL_STRIKE_STRIKES)
BALL_STRIKE_FOUL_BALLS : typing.Set[str] = set([x for x in 'FR'])
assertOnlySingleCharacterStringsInSet(BALL_STRIKE_FOUL_BALLS)
def getBallStrikeCountsFromPitches(pitches: str) -> typing.List[BallStrikeCount]:
    counts = [BallStrikeCount(0, 0)]
    for pitch in pitches.upper():
        if pitch in BALL_STRIKE_IGNORE_CHARS:
            continue
        lastCount = counts[-1]
        # For performance, check in rough order of frequency
        if pitch in BALL_STRIKE_STRIKES:
            counts.append(lastCount.addStrike())
        elif pitch in BALL_STRIKE_BALLS:
            counts.append(lastCount.addBall())
        elif pitch in BALL_STRIKE_FOUL_BALLS:
            if lastCount.strikes != 2:
                counts.append(lastCount.addStrike())
        # TODO - actually go through these exceptions?
        elif pitch == 'U' or pitch == 'Z' or pitch == 'G' or pitch == '\\' or pitch == "`" or pitch == "8" or pitch == "A" or True:
            # sigh, just throw this one out I guess
            # "BZ" is used in 1988CHA.EVA, pretty sure it's supposed to be an X, but skip it
            # TODO - add exceptions
            # "FFFGFX" is used in 1989BAL.EVA, must be some kind of foul ball? (ended on 0-2 count)
            # "\BBSBSX" is used in 1989BOS.EVA, probably should just ignore it (ended on 3-2 count)
            # "11FB``PFBF1X`" is used in 1989CHA.EVA, ...??
            # "BBB8FB" is used in 1989DET.EVA, ...??
            # "CBABX" is used in 1989MIL.EVA
            # TODO - contact retrosheet?
            if pitch != 'U':
                print(f"Unknown pitch {pitch} in {pitches}, skipping")
            return [BallStrikeCount(0, 0)]
        else:
            assert False, "Unexpected pitch character " + str(pitch) + " in " + str(pitches)

    return counts

class Report:
    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine]) -> None:
        raise Exception(f"{type(self).__name__} must override processedGame!")

    def clearStats(self) -> None:
        pass

    def doneWithYear(self, year: str) -> None:
        assert sortByYear, "doneWithYear called but sortByYear is false!"

    def doneWithAll(self) -> None:
        assert not sortByYear, "doneWithAll called but sortByYear is true!"

class StatsReport(Report):
    def __init__(self):
        super().__init__()
        self.stats = {}

    def clearStats(self) -> None:
        self.stats = {}

    def reportFileName(self) -> str:
        raise Exception(f"{type(self).__name__} must override reportFileName!")

    def doneWithYear(self, year: str) -> None:
        super().doneWithYear(year)
        outputFile = open('statsyears/' + self.reportFileName() + '.' + str(year), 'w')
        statKeys = list(self.stats.keys())
        statKeys.sort()
        for key in statKeys:
            outputFile.write("%s: %s\n" % (key, self.stats[key]))
        outputFile.close()

    def doneWithAll(self) -> None:
        super().doneWithAll()
        outputFile = open(self.reportFileName(), 'w')
        statKeys = list(self.stats.keys())
        statKeys.sort()
        for key in statKeys:
            outputFile.write("%s: %s\n" % (key, self.stats[key]))
        outputFile.close()

class StatsWinExpectancyReport(StatsReport):
    def reportFileName(self) -> str:
        return "stats"

    def _addSituationKey(self, situationKey: typing.Tuple[typing.Any], isWin: bool):
        if (situationKey in self.stats):
            (numWins, numSituations) = self.stats[situationKey]
            numSituations = numSituations + 1
            if (isWin):
                numWins = numWins + 1
            self.stats[situationKey] = (numWins, numSituations)
        else:
            numWins = 1 if isWin else 0 
            self.stats[situationKey] = (numWins, 1)


    # Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff) to a tuple of
    # (number of wins, number of situations)
    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine]) -> None:
        if skipOutput:
            return
        # Add gameKeys to stats
        # Check the last situation to see who won.
        homeWon = finalGameSituation.isHomeWinning()
        if (homeWon is None):
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
        for situationKeyOriginal in [x.situationKey for x in situationKeysAndPlayLines]:
            isHomeInning = situationKeyOriginal[1]
            isWin = (isHomeInning and homeWon) or (not isHomeInning and not homeWon)
            #TODO this is probably slow?
            situationKeyList = list(situationKeyOriginal)
            situationKeyList[1] = 1 if isHomeInning else 0
            situationKey = tuple(situationKeyList)
            self._addSituationKey(situationKey, isWin)

class StatsWinExpectancyWithBallsStrikesReport(StatsWinExpectancyReport):
    def __init__(self):
        super().__init__()
        self.playPitchesRe = re.compile(r'^play,\s?\d+,\s?[01],.*?,.*?,(.*?),(.*)$')

    def reportFileName(self) -> str:
        return "statswithballsstrikes"

    # Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff, (balls, strikes)) to a tuple of
    # (number of wins, number of situations)
    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine]) -> None:
        if skipOutput:
            return
        # Add gameKeys to stats
        # Check the last situation to see who won.
        homeWon = finalGameSituation.isHomeWinning()
        if (homeWon is None):
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
        for situationKeyAndPlayLine in situationKeysAndPlayLines:
            situationKeyOriginal = situationKeyAndPlayLine.situationKey
            isHomeInning = situationKeyOriginal[1]
            #TODO this is probably slow?
            situationKeyList = list(situationKeyOriginal)
            situationKeyList[1] = 1 if isHomeInning else 0
            playMatch = self.playPitchesRe.match(situationKeyAndPlayLine.playLine)
            pitches = playMatch.group(1)
            counts = getBallStrikeCountsFromPitches(pitches)
            isWin = (isHomeInning and homeWon) or (not isHomeInning and not homeWon)
            situationKeyList.append(typing.cast(int, (0, 0)))
            for count in [x for x in counts if (x.balls < 4 and x.strikes < 3)]:
                situationKeyList[-1] = count
                situationKey = tuple(situationKeyList)
                self._addSituationKey(situationKey, isWin)

class StatsRunExpectancyPerInningReport(StatsReport):
    def reportFileName(self) -> str:
        return "runsperinningstats"

    def getNextInning(self, inning) -> typing.Tuple[int, bool]:
        if (inning[1]):
            return (inning[0]+1, False)
        else:
            return (inning[0], True)

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine]) -> None:
        inningsToKeys : typing.Dict[typing.Tuple[int, bool], typing.List[GameSituation]] = {}
        for situationKey in [x.situationKey for x in situationKeysAndPlayLines]:
            situation = GameSituation.fromKey(situationKey)
            key = (situation.inning, situation.isHome)
            if (key in inningsToKeys):
                inningsToKeys[key].append(situation)
            else:
                inningsToKeys[key] = [situation]
        for inning in inningsToKeys:
            startingRunDiff = inningsToKeys[inning][0].curScoreDiff
            if (self.getNextInning(inning) in inningsToKeys):
                endingRunDiff = -1 * inningsToKeys[self.getNextInning(inning)][0].curScoreDiff
            else:
                endingRunDiff = inningsToKeys[inning][-1].curScoreDiff
            if (endingRunDiff - startingRunDiff < 0):
                print("uh-oh - scored %d runs!" % (endingRunDiff - startingRunDiff))
                assert False
            # Add the statistics now.
            for situation in inningsToKeys[inning]:
                # Make sure we don't duplicate keys.
                # Strip off the inning info (for now?) and the curScoreDiff
                keyToUse = situation.getKey()[2:4]
                runsGained = endingRunDiff - situation.curScoreDiff
                if (keyToUse in self.stats):
                    while (len(self.stats[keyToUse]) < (runsGained + 1)):
                        self.stats[keyToUse].append(0)
                else:
                    self.stats[keyToUse] = [0] * (runsGained + 1)
                self.stats[keyToUse][runsGained] += 1

class StatsRunExpectancyPerInningWithBallsStrikesReport(StatsRunExpectancyPerInningReport):
    def __init__(self):
        super().__init__()
        self.playPitchesRe = re.compile(r'^play,\s?\d+,\s?[01],.*?,.*?,(.*?),(.*)$')

    def reportFileName(self) -> str:
        return "runsperinningballsstrikesstats"

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine]) -> None:
        inningsToKeys : typing.Dict[typing.Tuple[int, bool], typing.List[typing.Tuple[GameSituation, typing.List[BallStrikeCount]]]] = {}
        for situationKeyAndPlayLine in situationKeysAndPlayLines:
            situationKey = situationKeyAndPlayLine.situationKey
            playMatch = self.playPitchesRe.match(situationKeyAndPlayLine.playLine)
            pitches = playMatch.group(1)
            counts = getBallStrikeCountsFromPitches(pitches)
            situation = GameSituation.fromKey(situationKey)
            key = (situation.inning, situation.isHome)
            if (key in inningsToKeys):
                inningsToKeys[key].append((situation, counts))
            else:
                inningsToKeys[key] = [(situation, counts)]
        for inning in inningsToKeys:
            startingRunDiff = inningsToKeys[inning][0][0].curScoreDiff
            if (self.getNextInning(inning) in inningsToKeys):
                endingRunDiff = -1 * inningsToKeys[self.getNextInning(inning)][0][0].curScoreDiff
            else:
                endingRunDiff = inningsToKeys[inning][-1][0].curScoreDiff
            if (endingRunDiff - startingRunDiff < 0):
                print("uh-oh - scored %d runs!" % (endingRunDiff - startingRunDiff))
                assert False
            # Add the statistics now.
            for (situation, counts) in inningsToKeys[inning]:
                # Make sure we don't duplicate keys.
                # Strip off the inning info (for now?) and the curScoreDiff
                runsGained = endingRunDiff - situation.curScoreDiff
                keyToUsePrefix = situation.getKey()[2:4]
                for count in [x for x in counts if (x.balls < 4 and x.strikes < 3)]:
                    keyToUseList = list(keyToUsePrefix)
                    keyToUseList.append(typing.cast(int, count))
                    keyToUse = tuple(keyToUseList)
                    if (keyToUse in self.stats):
                        while (len(self.stats[keyToUse]) < (runsGained + 1)):
                            self.stats[keyToUse].append(0)
                    else:
                        self.stats[keyToUse] = [0] * (runsGained + 1)
                    self.stats[keyToUse][runsGained] += 1



# Finds games where the home team won after being down by 6 runs in the bottom of the ninth
# with two outs and nobody on base
class HomeTeamWonDownSixWithTwoOutsInNinthReport(Report):
    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine]) -> None:
        homeWon = finalGameSituation.isHomeWinning()
        if (homeWon is None):
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
        if not homeWon:
            return
        if (9, True, 2, (0, 0, 0), -6) in [x.situationKey for x in situationKeysAndPlayLines]:
            print("GOT IT with gameId:")
            print(gameId)
            sys.exit(0)

# Finds games where the home team won with a walkoff walk on 4 pitches
class WalkOffWalkReport(Report):
    def __init__(self):
        super().__init__()
        self.playPitchesRe = re.compile(r'^play,\s?\d+,\s?[01],.*?,.*?,(.*?),(.*)$')
        self.numGames = 0
        self.numGamesWithPitches = 0
        self.walkOffWalks = 0
        self.walkOffWalksOnFourPitches = 0
        self.yearCount = {}

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine]) -> None:
        reallyVerbose = False # gameId == 'CHA201404020'
        year = int(gameId[3:7])
        if year not in self.yearCount:
            self.yearCount[year] = 0
        gameSituationKeys = [x.situationKey for x in situationKeysAndPlayLines]
        lastGameSituation = GameSituation.fromKey(gameSituationKeys[-1])
        if reallyVerbose:
            print(f"lastGameSituation: {lastGameSituation}")
            print(f"finalGameSituation: {finalGameSituation}")
        if reallyVerbose:
            for gameSituationKey in gameSituationKeys:
                print(GameSituation.fromKey(gameSituationKey))
        homeWon = finalGameSituation.isHomeWinning()
        if reallyVerbose:
            print(f"homeWon: {homeWon}")
        if (homeWon is None):
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
        self.numGames += 1
        lastPlayLine = situationKeysAndPlayLines[-1].playLine
        if reallyVerbose:
            print(f"lastPlayLine: {lastPlayLine}")
        playMatch = self.playPitchesRe.match(lastPlayLine)
        pitches = playMatch.group(1)
        if reallyVerbose:
            print(f"pitches: {pitches}")
        if len([c for c in pitches if c != '?']) > 0:
            self.numGamesWithPitches += 1
        if not homeWon:
            return
        if lastGameSituation.isHome and lastGameSituation.outs <= 2 and lastGameSituation.runners == [1, 1, 1] and lastGameSituation.curScoreDiff == 0:
            playString = playMatch.group(2)
            playString = playString.replace('!', '').replace('#', '').replace('?', '')
            # TODO - refactor this stuff and share with StatsWinExpectancyWithBallsStrikesReport
            playArray = playString.split('.')
            batterEvents = playArray[0].split(';')
            for batterEvent in batterEvents:
                if ((batterEvent.startswith('W') and not batterEvent.startswith('WP')) or batterEvent.startswith('IW') or batterEvent.startswith('I')):
                    # walk
                    self.walkOffWalks += 1
                    self.yearCount[year] += 1
                    # This is surprisingly complicated because there's a lot of extraneous stuff in here.
                    # TODO - use getBallStrikeCountsFromPitches instead
                    # TODO - could look at count instead, make sure it's 3-0
                    numStrikes = len([p for p in pitches if p == 'C' or p == 'F' or p == 'K' or p == 'L' or p == 'M' or p == 'O' or p == 'R' or p == 'S' or p == 'T'])
                    # Check this to make sure we have reasonable pitches
                    numBalls = len([p for p in pitches if p == 'B' or p == 'I' or p == 'P' or p == 'V'])
                    print(f"Found game with gameId: {gameId}")
                    print("Last line was " + lastPlayLine)
                    if numStrikes == 0 and numBalls == 4:
                        print("on four pitches!")
                        self.walkOffWalksOnFourPitches += 1

    def doneWithAll(self) -> None:
        print(f"numGames: {self.numGames}")
        print(f"numGamesWithPitches: {self.numGamesWithPitches}")
        print(f"walkOffWalks: {self.walkOffWalks}")
        print(f"walkOffWalksOnFourPitches: {self.walkOffWalksOnFourPitches}")
        for year in sorted(self.yearCount.keys()):
            print(f"  {year}: {self.yearCount[year]}")

def usage():
    print("Usage: parseRetrosheet.py [-t] [-v] [-q] [-s] [-h] [-y] [-r <report name>] <file paths>")
    print("-t: just run tests")
    print("-v: verbose")
    print("-q: quiet")
    print("-s: skip output, just parse everything and stop on first error")
    print("-h: help")
    print("-y: generate data sorted by year")
    print("-r: specify which reports to run (default: Stats)")
    print()
    print("Possible reports:")
    for name in sorted(Reports.keys()):
        print("- " + name)

# This selects what stats we're compiling.
Reports: typing.Dict[str, typing.Iterable[Report]] = {}
Reports['Stats'] = [StatsWinExpectancyReport(), StatsRunExpectancyPerInningReport()]
Reports['StatsWithBallsStrikes'] = [StatsWinExpectancyWithBallsStrikesReport(), StatsRunExpectancyPerInningWithBallsStrikesReport()]
Reports['HomeTeamWonDownSixWithTwoOutsInNinth'] = [HomeTeamWonDownSixWithTwoOutsInNinthReport()]
Reports['WalkOffWalk']= [WalkOffWalkReport()]
reportsToRun = Reports['Stats']
def main(args):
    global verbosity, skipOutput, stopOnFirstError, reportsToRun, sortByYear
    try:
        opts, files = getopt.getopt(args, 'vhsyqr:')
    except getopt.GetoptError as err:
        print(str(err))
        sys.exit(2)
    for o, a in opts:
        if o == '-h':
            usage()
            sys.exit(1)
        elif o == '-y':
            sortByYear = True
        elif o == '-v':
            verbosity = Verbosity.verbose
        elif o == '-q':
            verbosity = Verbosity.quiet
        elif o == '-s':
            skipOutput = True
            stopOnFirstError = True
        elif o == '-r':
            if a in Reports:
                reportsToRun = Reports[a]
            else:
                print("Unrecognized report name!")
                usage()
                sys.exit(1)
        else:
            assert False, "unhandled option: " + str(o)
    if sortByYear:
        yearsToFiles = {}
        realFiles = []
        for fileName in files:
            if os.path.isdir(fileName):
                for childFileName in sorted(os.listdir(fileName)):
                    realFiles.append(os.path.join(fileName, childFileName))
            else:
                realFiles.append(fileName)
        for fileName in realFiles:
            year = int(os.path.basename(fileName)[:4])
            if year not in yearsToFiles:
                yearsToFiles[year] = []
            yearsToFiles[year].append(fileName)
        for year in sorted(yearsToFiles):
            if verbosity >= Verbosity.normal:
                print(year)
            for report in reportsToRun:
                report.clearStats()
            for fileName in yearsToFiles[year]:
                if verbosity >= Verbosity.normal:
                    print(fileName)
                eventFile = open(fileName, 'r', encoding='latin-1')
                parseFile(eventFile, reportsToRun)
                eventFile.close()
            if not skipOutput:
                for report in reportsToRun:
                    report.doneWithYear(str(year))
    else:
        numGames = 0
        realFiles = []
        for fileName in files:
            if os.path.isdir(fileName):
                for childFileName in sorted(os.listdir(fileName)):
                    realFiles.append(os.path.join(fileName, childFileName))
            else:
                realFiles.append(fileName)
        for fileName in realFiles:
            #eventFileName = '2004COL.EVN'
            if verbosity >= Verbosity.normal:
                print(fileName)
            eventFile = open(fileName, 'r', encoding='latin-1')
            numGames += parseFile(eventFile, reportsToRun)
            eventFile.close()
        if verbosity >= Verbosity.normal:
            print("numGames is %d" % numGames)
        if not skipOutput:
            for report in reportsToRun:
                report.doneWithAll()

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
        situation = GameSituation()
        situation.inning = inning
        situation.isHome = isHome
        situation.outs = outs
        #TODO refactor?
        return (situation, 'play,' + str(inning) + ',' + ('1' if situation.isHome else '0') + ',,,,' + playString)
    
    def test_simpleout(self):
        (situation, playString) = self.util_setup(0, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_simpleout_oneout(self):
        (situation, playString) = self.util_setup(1, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 2
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_top(self):
        (situation, playString) = self.util_setup(2, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 0
        sitCopy.isHome = True
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_bottom(self):
        (situation, playString) = self.util_setup(2, True, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 0
        sitCopy.isHome = False
        sitCopy.inning = 2
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_top_clearrunners(self):
        (situation, playString) = self.util_setup(2, False, '8')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 0
        sitCopy.isHome = True
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_bottom_clearrunners(self):
        (situation, playString) = self.util_setup(2, True, '8')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 0
        sitCopy.isHome = False
        sitCopy.inning = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_forceout(self):
        (situation, playString) = self.util_setup(0, False, '83')
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceFirstSecond(self):
        (situation, playString) = self.util_setup(0, False, '8.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThird(self):
        (situation, playString) = self.util_setup(0, False, '8.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_out_advanceThirdScore(self):
        (situation, playString) = self.util_setup(0, False, '8.3-H')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThirdScore(self):
        (situation, playString) = self.util_setup(0, False, '8.2-3;3-H')
        situation.runners = [0, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 1]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThirdAllScore(self):
        (situation, playString) = self.util_setup(0, False, '8.2-H;3-H')
        situation.runners = [0, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 2
        self.assertEqual(sitCopy, situation)

    def test_groundout_advance(self):
        (situation, playString) = self.util_setup(0, False, '54(B)/BG25/SH.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_groundout_safe_and_score(self):
        (situation, playString) = self.util_setup(0, False, '54(1)/FO/G5.3-H;B-1')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        sitCopy.curScoreDiff = 1
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_explicit_sacrifice(self):
        (situation, playString) = self.util_setup(0, False, '23/SH.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay(self):
        (situation, playString) = self.util_setup(0, False, '64(1)3/GDP/G6')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay_lineout(self):
        (situation, playString) = self.util_setup(0, False, '8(B)84(2)/LDP/L8')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay_lineout_unassisted(self):
        (situation, playString) = self.util_setup(0, False, '3(B)3(1)/LDP')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference_runner(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference_runner_explicit(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2.B-1;1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_pitchers_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E1')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_first_basemans_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E3')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_single(self):
        (situation, playString) = self.util_setup(0, False, 'S7')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_double(self):
        (situation, playString) = self.util_setup(0, False, 'D7/G5.3-H;2-H;1-H')
        situation.runners = [1, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_triple(self):
        (situation, playString) = self.util_setup(0, False, 'T9/F9LD.2-H')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 1]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_groundrule_double(self):
        (situation, playString) = self.util_setup(0, False, 'DGR/L9LS.2-H')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_throwing_error(self):
        (situation, playString) = self.util_setup(0, False, 'E1/TH/BG15.1-3')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_fielding_error(self):
        (situation, playString) = self.util_setup(0, False, 'E3.1-2;B-1')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_fielders_choice_out_at_home(self):
        (situation, playString) = self.util_setup(0, False, 'FC5/G5.3XH(52)')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_fielders_choice_no_outs(self):
        (situation, playString) = self.util_setup(0, False, 'FC3/G3S.3-H;1-2')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_error_on_foul_ball(self):
        (situation, playString) = self.util_setup(0, False, 'FLE5/P5F')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_home_run(self):
        (situation, playString) = self.util_setup(0, False, 'H/L7D')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_home_run_explicit_runners(self):
        (situation, playString) = self.util_setup(0, False, 'HR/F78XD.2-H;1-H')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park(self):
        (situation, playString) = self.util_setup(0, False, 'HR9/F9LS.3-H;1-H')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park_just_h(self):
        (situation, playString) = self.util_setup(0, False, 'H9/F9LS.3-H;1-H')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park_just_h_no_runners(self):
        (situation, playString) = self.util_setup(0, False, 'H9/F9LS')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_hit_by_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'HP.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_hit_by_pitch_no_runners(self):
        (situation, playString) = self.util_setup(0, False, 'HP')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_strikeout(self):
        (situation, playString) = self.util_setup(0, False, 'K')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout(self):
        (situation, playString) = self.util_setup(0, False, 'K23')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_passed_ball(self):
        (situation, playString) = self.util_setup(0, False, 'K+PB.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_miscue(self):
        (situation, playString) = self.util_setup(0, False, 'K+WP.B-1')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout_other_runner_advance(self):
        (situation, playString) = self.util_setup(0, False, 'K23+WP.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 1]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout_caught_stealing(self):
        # see game BAL196505282, end of 5th inning
        (situation, playString) = self.util_setup(0, False, 'K23+CS3(34)/DP')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 2
        self.assertEqual(sitCopy, situation)

    def test_no_play(self):
        (situation, playString) = self.util_setup(0, False, 'NP')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_walk(self):
        (situation, playString) = self.util_setup(0, False, 'W.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_intentional_walk(self):
        (situation, playString) = self.util_setup(0, False, 'IW')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_walk_wild_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'W+WP.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_balk(self):
        (situation, playString) = self.util_setup(0, False, 'BK.3-H;1-2')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing(self):
        (situation, playString) = self.util_setup(0, False, 'CSH(12)')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing_advance(self):
        (situation, playString) = self.util_setup(0, False, 'CS2(24).2-3')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 1]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing_error(self):
        (situation, playString) = self.util_setup(0, False, 'CS2(2E4).1-3')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_defensive_indifference(self):
        (situation, playString) = self.util_setup(0, False, 'DI.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_other_advance(self):
        # "Thompson out trying to advance after ball eluded catcher"
        (situation, playString) = self.util_setup(0, False, 'OA.2X3(25)')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_wild_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'WP.2-3;1-2')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 1]
        self.assertEqual(sitCopy, situation)

    def test_passed_ball(self):
        (situation, playString) = self.util_setup(0, False, 'PB.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_pickoff(self):
        (situation, playString) = self.util_setup(0, False, 'PO2(14)')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_pickoff_error(self):
        (situation, playString) = self.util_setup(0, False, 'PO1(E3).1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_pickoff_caught_stealing(self):
        (situation, playString) = self.util_setup(0, False, 'POCS2(14)')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_stolen_base(self):
        (situation, playString) = self.util_setup(0, False, 'SB2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_stolen_base_multiple(self):
        (situation, playString) = self.util_setup(0, False, 'SB3;SB2')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 1]
        self.assertEqual(sitCopy, situation)

    def test_stolen_base_multiple_home(self):
        (situation, playString) = self.util_setup(0, False, 'SBH;SB2')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_weird_error_running(self):
        # game KCA200607040, bottom of the 3rd
        (situation, playString) = self.util_setup(0, False, 'S7/L.3-H;2-H;1XH(7432/TH)(E7)')
        situation.runners = [1, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 0, 0]
        sitCopy.curScoreDiff = 2
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_error_running(self):
        # game KCA200607210, bottom of the 3rd
        (situation, playString) = self.util_setup(0, False, 'FC1.1X2(6E4);B-1')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_putout_runner_at_wrong_base(self):
        # game DET196405140, bottom of the 4th
        (situation, playString) = self.util_setup(0, False, '36(1)/BF.B-1')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_walk_plus_putout_caught_stealing(self):
        # game CHN201708160, bottom of the 4th
        (situation, playString) = self.util_setup(0, False, 'W+POCS3(26)')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation)
        sitCopy.outs = 1
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    # Not sure how we could parse this, so not running this test
    #def test_tagout_with_errors_run_scores(self):
    #    # game BAL201906250, bottom of the 3rd
    #    (situation, playString) = self.util_setup(2, False, 'D9/G+.1-H;BX3(E9)(95/TH)')
    #    situation.runners = [1, 0, 0]
    #    sitCopy = situation.copy()
    #    parsePlay(playString, situation)
    #    sitCopy.outs = 0
    #    sitCopy.runners = [0, 0, 0]
    #    sitCopy.isHome = True
    #    sitCopy.curScoreDiff = -1
    #    self.assertEqual(sitCopy, situation)
   
    def util_test_ballstrike(self, pitches: str, ballStrikes: typing.Iterable[typing.Tuple[int, int]]):
        expected = [BallStrikeCount(x, y) for (x, y) in ballStrikes]
        self.assertEqual(expected, getBallStrikeCountsFromPitches(pitches))

    def test_ballstrike_empty_string(self):
        self.util_test_ballstrike("", [(0, 0)])

    def test_ballstrike_allballs(self):
        self.util_test_ballstrike("IPVB", [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)])

    def test_ballstrike_allstrikes_withignorecharacters(self):
        self.util_test_ballstrike("+*.123>CNS>.*2K", [(0, 0), (0, 1), (0, 2), (0, 3)])

    def test_ballstrike_ballsandstrikes(self):
        self.util_test_ballstrike("LBMBBO", [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (3, 2), (3, 3)])

    def test_ballstrike_hitfirstpitch(self):
        self.util_test_ballstrike("X", [(0, 0)])

    def test_ballstrike_hitlaterpitch(self):
        self.util_test_ballstrike("QTX", [(0, 0), (0, 1), (0, 2)])

    def test_ballstrike_unknownpitch_returnnothing(self):
        self.util_test_ballstrike("SBSUBBB", [(0, 0)])
        
    def test_ballstrike_foulzerostrikes(self):
        self.util_test_ballstrike("BFY", [(0, 0), (1, 0), (1, 1)])

    def test_ballstrike_foulonestrikes(self):
        self.util_test_ballstrike("BSRX", [(0, 0), (1, 0), (1, 1), (1, 2)])

    def test_ballstrike_multiplefoulstwostrikes(self):
        self.util_test_ballstrike("SBSFBFFX", [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)])

    def test_ballstrike_lotsoffouls(self):
        self.util_test_ballstrike("BFFBFFBX", [(0, 0), (1, 0), (1, 1), (1, 2), (2, 2), (3, 2)])


if (__name__ == '__main__'):
    if (len(sys.argv) > 1 and sys.argv[1] == '-t'):
        # get rid of the -t
        unittest.main(argv=[sys.argv[0]] + sys.argv[2:])
    else:
        main(sys.argv[1:])


