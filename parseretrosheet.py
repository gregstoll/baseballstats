#!/usr/bin/python3
import re, sys, copy, getopt, os, os.path
import unittest
import typing
import cProfile
import copy
import multiprocessing
from enum import IntEnum

class Verbosity(IntEnum):
    quiet = 0
    normal = 1
    verbose = 2
doParallel = True

#TODO - use __all__
#TODO - do something with these
verbosity = Verbosity.normal
skipOutput = False
stopOnFirstError = False
sortByYear = False
knownBadGames = ['WS2196605270', 'MIL197107272', 'MON197108040', 'NYN198105090', 'SEA200709261', 'MIL201304190', 'SFN201407300', 'BAL201906250']
class GameRuleOptions:
    def __init__(self):
        self.innings = 9
        self.runnerStartsOnSecondInExtraInnings = False

positionToBase = {1:-1, 2:-1, 3:1, 4:2, 5:3, 6:2, 7:-1, 8:-1, 9:-1}
# TODO - make this a real class I guess
GameSituationKey = typing.Tuple[int, bool, int, typing.Tuple[int, int, int], int]
class GameSituation:
    def __init__(self):
        self.inning = 1
        self.isHome = False
        self.outs = 0
        # Runners on first, second, third
        self.runners : typing.List[int] = [0, 0, 0]
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

    def nextInningIfThreeOuts(self, runnerStartsOnSecondInExtraInnings, innings):
        if (self.outs >= 3):
            if (self.isHome):
                self.isHome = False
                self.inning = self.inning + 1
            else:
                self.isHome = True
            self.outs = 0
            self.runners = [0, 1 if runnerStartsOnSecondInExtraInnings and self.inning > innings else 0, 0]
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

# TODO - write this and use it
def parseBatterEvent(batterEvent: str):
    pass

def parseFilesParallel(fileNames: typing.Iterable[str]) -> typing.Tuple[int, typing.Iterable['Report']]:
    global verbosity
    verbosity = parseFilesParallel.localVerbosity
    clonedReportsToRun = [copy.deepcopy(x) for x in parseFilesParallel.originalReportsToRun]
    numGames = 0
    for fileName in fileNames:
        with open(fileName, 'r', encoding='latin-1') as eventFile:
            if verbosity >= Verbosity.normal:
                print(fileName)
            numGames += parseFile(eventFile, fileName, clonedReportsToRun)[0]
    return (numGames, clonedReportsToRun)

def parseFile(f: typing.IO[str], eventFileName: str, reports: typing.Iterable['Report']) -> typing.Tuple[int, typing.Iterable['Report']]:
    numGames = 0
    inGame = False
    curGameSituation : GameSituation = GameSituation()
    gameSituationKeys : typing.List[GameSituationKey] = []
    playLines : typing.List[str] = []
    curId : str = ""
    _, eventFileExtension = os.path.splitext(eventFileName)
    isPlayoffs = eventFileExtension.upper() == '.EVE'
    gameRuleOptions = GameRuleOptions()
    for line in f.readlines():
        if (not(inGame)):
            if (line.startswith("id,")):
                curId = line[3:].strip()
                curGameSituation = GameSituation()
                gameSituationKeys = []
                gameSituationKeys.append(curGameSituation.getKey())
                playLines = []
                inGame = True
                # In 2020 a runner started on second base in extra innings, but not in playoff games
                curYear = int(curId[3:7])
                gameRuleOptions.runnerStartsOnSecondInExtraInnings = (curYear == 2020 and not isPlayoffs)
                gameRuleOptions.innings = 9
                if eventFileName == "2020NLW1.EVE":
                    print(f"isPlayoffs: {isPlayoffs}, runneronsecond: {gameRuleOptions.runnerStartsOnSecondInExtraInnings}")
        else:
            if (line.startswith("id,")):
                assert curId != ""
                numGames = numGames + 1
                callReportsProcessedGame(gameSituationKeys, curGameSituation, reports, curId, playLines, gameRuleOptions)
                if (verbosity == Verbosity.verbose):
                    print("NEW GAME")
                curGameSituation = GameSituation()
                curId = line[3:].strip()
                gameSituationKeys = []
                gameSituationKeys.append(curGameSituation.getKey())
                playLines = []
                # In 2020 a runner started on second base in extra innings, but not in playoff games
                curYear = int(curId[3:7])
                gameRuleOptions.runnerStartsOnSecondInExtraInnings = (curYear == 2020 and not isPlayoffs)
                gameRuleOptions.innings = 9
            else:
                if (line.startswith("play")):
                    try:
                        parsePlay(line, curGameSituation, gameRuleOptions)
                    except AssertionError:
                        if verbosity >= Verbosity.normal:
                            print("Error in game " + curId)
                            if curId in knownBadGames:
                                print("known bad game")
                        if curId not in knownBadGames:
                            raise Exception(f"Error in game {curId}")
                        else:
                            # We're just gonna punt and ignore the error
                            inGame = False
                    else:
                        curGameSituationKey = curGameSituation.getKey()
                        if (curGameSituationKey not in gameSituationKeys):
                            gameSituationKeys.append(curGameSituationKey)
                            playLines.append(line.strip())
                elif (line.startswith("info,innings,")):
                    gameRuleOptions.innings = int(line[len("info,innings,"):])
    if inGame:
        assert curId != ""
        numGames = numGames + 1
        callReportsProcessedGame(gameSituationKeys, curGameSituation, reports, curId, playLines, gameRuleOptions)
    return (numGames, reports)

def callReportsProcessedGame(gameSituationKeys: typing.List[GameSituationKey], finalGameSituation: GameSituation, reports: typing.Iterable['Report'], curId: str, playLines: typing.List[str], gameRuleOptions: GameRuleOptions) -> None:
    # Don't include the last situation in the list of keys, because it's one after the last inning probably
    if (len(gameSituationKeys) > 0 and gameSituationKeys[-1] == finalGameSituation.getKey()):
        gameSituationKeys = gameSituationKeys[:-1]
    assert len(gameSituationKeys) == len(playLines)
    situationKeysAndNextPlayLines : typing.List[GameSituationKeyAndNextPlayLine] = [GameSituationKeyAndNextPlayLine(key, line) for (key, line) in zip(gameSituationKeys, playLines)]
    for report in reports:
        report.processedGame(curId, finalGameSituation, situationKeysAndNextPlayLines, gameRuleOptions)

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

reCache = {}
def getRe(pattern):
    global reCache
    oldRe = reCache.get(pattern, None)
    if oldRe is not None:
        return oldRe
    reCache[pattern] = re.compile(pattern)
    return reCache[pattern]

class PlayLineInfo(typing.NamedTuple):
    inning: int
    isHome: bool
    playerId: str
    countWhenPlayHappened: str
    pitchesString: str
    playString: str

    @staticmethod
    def fromLine(line: str) -> 'PlayLineInfo':
        # decription of the format is at http://www.retrosheet.org/eventfile.htm
        playMatch = getRe(r'^play,\s?(\d+),\s?([01]),(.*?),(.*?),(.*?),(.*)$').match(line)
        assert playMatch
        return PlayLineInfo(inning=int(playMatch.group(1)), isHome=(int(playMatch.group(2))==1), playerId=playMatch.group(3), countWhenPlayHappened=playMatch.group(4), pitchesString=playMatch.group(5), playString=playMatch.group(6))

def parsePlay(line: str, gameSituation: GameSituation, gameRuleOptions: GameRuleOptions):
    # decription of the format is at http://www.retrosheet.org/eventfile.htm
    playLineInfo = PlayLineInfo.fromLine(line)
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
    assert gameSituation.inning == playLineInfo.inning
    assert gameSituation.isHome == playLineInfo.isHome
    playString = playLineInfo.playString
    # Strip !'s, #'s, and ?'s
    playString = playString.replace('!', '').replace('#', '').replace('?', '')
    playArray = playString.split('.')
    assert len(playArray) <= 2
    # Deal with the first part of the string.
    batterEvents = playArray[0].split(';')
    for batterEvent in batterEvents:
        batterEvent = batterEvent.strip()
    
        doneParsingEvent = False
        simpleHitMatch = getRe(r"^([SDTH])(?:\d|/)").match(batterEvent)
        simpleHitMatch2 = getRe(r"^([SDTH])\s*$").match(batterEvent)
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
                        if (getRe(r'^CS.\([^)]*?E.*?\)').match(tempEvent)):
                            # Error, so no out.
                            dest = characterToBase(tempEvent[2])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = dest
                        else:
                            dest = characterToBase(tempEvent[2])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('POCS')):
                        if (getRe(r'^POCS.\([^)]*?E.*?\)').match(tempEvent)):
                            # Error, so no out.
                            dest = characterToBase(tempEvent[4])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = dest
                        else:
                            dest = characterToBase(tempEvent[4])
                            assert (dest == 2 or dest == 3 or dest == 4)
                            runnerDests[dest - 1] = 0
                    elif (tempEvent.startswith('PO')):
                        if (getRe(r'^PO.\([^)]*?E.*?\)').match(tempEvent)):
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
                        if verbosity >= Verbosity.normal:
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
                        if (getRe(r'^CS.\([^)]*?E.*?\)').match(tempEvent)):
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
                        if verbosity >= Verbosity.normal:
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
            doublePlayMatch = getRe(r'^\d+\((\d|B)\)(?:\d*\((\d|B)\))?(?:\d*\((\d|B)\))?').match(batterEvent)
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
            weirdDoublePlayMatch = getRe(r'^\d+(/.*?)*/.?[DT]P').match(batterEvent)
            if (weirdDoublePlayMatch):
                # This is a double play.  The specifics of who's out will
                # come later.
                if (verbosity == Verbosity.verbose):
                    print("weird double/triple play")
                runnerDests['B'] = 0
                runnersDefaultStayStill = True
                doneParsingEvent = True
        if (not doneParsingEvent):
            simpleOutMatch = getRe(r'^\d\D').match(batterEvent)
            if (simpleOutMatch and "/FO" not in batterEvent or (len(batterEvent) == 1 and (int(batterEvent) >= 1 and int(batterEvent) <= 9))):
                if (verbosity == Verbosity.verbose):
                    print("simple out")
                if (getRe(r'^\dE').match(batterEvent)):
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
            putOutMatch = getRe(r'^\d*(\d).*?(?:\((.)\))?').match(batterEvent)
            if (putOutMatch):
                if (verbosity == Verbosity.verbose):
                    print("Got a putout")
                if (getRe(r'\d?E\d').search(batterEvent)):
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
                if (getRe(r'^CS.\([^)]*?E.*?\)').match(batterEvent)):
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
                if (getRe(r'^POCS.\(.*?E.*?\)').match(batterEvent)):
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
                if (getRe(r'^PO.\([^)]*?E.*?\)').match(batterEvent)):
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
            if verbosity >= Verbosity.normal:
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
                if (getRe(r'^...(?:\([^)]*?\))*\(\d*E.*\)').match(runnerItem)):
                    #if (runner == 'B'):
                        # It seems to be the case that if it is the batter
                        # doing stuff, in this case the runner is safe
                        #runnerDests[runner] = base
                    # So this is probably an error.  See if the intervening
                    # parentheses indicate an out
                    if (getRe(r'^....*?\(\d*(/TH)?\).*?\(\d*E.*\)').match(runnerItem) or getRe(r'^....*?\(\d*E.*\)\(\d*\)').match(runnerItem)):
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
            if verbosity >= Verbosity.normal:
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
                if verbosity >= Verbosity.normal:
                    print("ERROR - unresolved runners %s!" % unresolvedRunners)
                    print("runnerDests: %s" % (runnerDests))
                assert False
    # Check that no new entries to runnerDests
    newRunners = [runner for runner in runnerDests if runner not in beginningRunners]
    if (verbosity == Verbosity.verbose):
        print("runnerDests: %s" % (runnerDests))
    if ('B' not in newRunners):
        if verbosity >= Verbosity.normal:
            print("ERROR - don't know what happened to B!")
        assert False
    else:
        newRunners.remove('B')
    if (len(newRunners) > 0):
        if verbosity >= Verbosity.normal:
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
                if verbosity >= Verbosity.normal:
                    print("ERROR - already a runner at base %d!" % runnerDests[runner])
                assert False
            newRunners[runnerDests[runner] - 1] = 1
    gameSituation.runners = newRunners
    gameSituation.nextInningIfThreeOuts(gameRuleOptions.runnerStartsOnSecondInExtraInnings, gameRuleOptions.innings)
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
                if verbosity >= Verbosity.normal:
                    print(f"Unknown pitch {pitch} in {pitches}, skipping")
            return [BallStrikeCount(0, 0)]
        else:
            assert False, "Unexpected pitch character " + str(pitch) + " in " + str(pitches)

    return counts

class Report:
    # game_id is the Retrosheet game id for the game. year_from_game_id() will return the year the game was played in.
    # final_game_situation is the situation _after_ the last play of the game. Beware - for a 9 inning game
    #    where the visiting team wins this will be in the top of the 10th inning with 0 outs. But for a 9 inning game
    #    where the home team wins on a walkoff this will be in the bottom of the 9th.
    # situations is the list of the situations at the _start_ of every play. So the last value here will be the
    #    situation before the final plate appearance of the game.
    # play_lines is the list of plays in the game - there are as many of these as entries in the situations slice.
    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        raise Exception(f"{type(self).__name__} must override processedGame!")

    def clearStats(self) -> None:
        pass

    def mergeInto(self, other: 'Report') -> None:
        raise Exception(f"{type(self).__name__} must override mergeInto to support parallel processing!")

    def supportsParallelProcessing(self) -> bool:
        return True

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

    def shouldProcessGame(self, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> bool:
        # In 2020 some games (doubleheaders) were played with only 7 innings, skip these
        # to avoid messing up statistics.
        if gameRuleOptions.innings != 9:
            return False
        # In 2020 extra innings started a runner on second base, which messes up
        # statistics.  If this rule continues we should figure out how to handle this,
        # but for now, skip these games.
        # don't use finalGameSituation here, because if the visiting team wins a normal 9 inning game
        # finalGameSituation will be the top of the 10th inning (with 0 outs)
        lastRealSituation = GameSituation.fromKey(situationKeysAndPlayLines[-1].situationKey)
        if gameRuleOptions.runnerStartsOnSecondInExtraInnings and lastRealSituation.inning > 9:
            return False
        return True
 
    def reportFileName(self) -> str:
        raise Exception(f"{type(self).__name__} must override reportFileName!")

    def doneWithYear(self, year: str) -> None:
        super().doneWithYear(year)
        outputFile = open('statsyears/' + self.reportFileName() + '.' + str(year), 'w')
        statKeys = list(self.stats.keys())
        statKeys.sort()
        for key in statKeys:
            outputFile.write("%s: %s\n" % (key, self.stats[key]))
            self.writeExtraInfo(outputFile, key, self.stats[key])
        outputFile.close()

    def doneWithAll(self) -> None:
        super().doneWithAll()
        outputFile = open(self.reportFileName(), 'w')
        statKeys = list(self.stats.keys())
        statKeys.sort()
        for key in statKeys:
            outputFile.write("%s: %s\n" % (key, self.stats[key]))
            self.writeExtraInfo(outputFile, key, self.stats[key])
        outputFile.close()
    
    def writeExtraInfo(self, outputFile, key, value) -> None:
        pass

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

    def mergeInto(self, other: 'StatsWinExpectancyReport') -> None:
        for key in self.stats:
            if key in other.stats:
                otherValue = other.stats[key]
                thisValue = self.stats[key]
                other.stats[key] = (otherValue[0] + thisValue[0], otherValue[1] + thisValue[1])
            else:
                other.stats[key] = self.stats[key]


    # Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff) to a tuple of
    # (number of wins, number of situations)
    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        if skipOutput:
            return
        if not self.shouldProcessGame(situationKeysAndPlayLines, gameRuleOptions):
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

    def reportFileName(self) -> str:
        return "statswithballsstrikes"

    # Maps a tuple (inning, isHome, outs, (runner on 1st, runner on 2nd, runner on 3rd), curScoreDiff, (balls, strikes)) to a tuple of
    # (number of wins, number of situations)
    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        if skipOutput:
            return
        if not self.shouldProcessGame(situationKeysAndPlayLines, gameRuleOptions):
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
            pitches = PlayLineInfo.fromLine(situationKeyAndPlayLine.playLine).pitchesString
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

    def getNextInning(self, inning: typing.Tuple[int, bool]) -> typing.Tuple[int, bool]:
        if (inning[1]):
            return (inning[0]+1, False)
        else:
            return (inning[0], True)

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        if not self.shouldProcessGame(situationKeysAndPlayLines, gameRuleOptions):
            return
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
            # Check if this was a walkoff
            if ((finalGameSituation.inning, finalGameSituation.isHome) == inning):
                endingRunDiff = finalGameSituation.curScoreDiff
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

    def mergeInto(self, other: 'StatsRunExpectancyPerInningReport') -> None:
        for key in self.stats:
            if key in other.stats:
                otherValue = other.stats[key]
                thisValue = self.stats[key]
                for i in range(len(otherValue)):
                    if i >= len(thisValue):
                        break
                    otherValue[i] += thisValue[i]
                for i in range(len(otherValue), len(thisValue)):
                    otherValue.append(thisValue[i])
            else:
                other.stats[key] = self.stats[key]


class StatsRunExpectancyPerInningWithBallsStrikesReport(StatsRunExpectancyPerInningReport):
    def __init__(self):
        super().__init__()

    def reportFileName(self) -> str:
        return "runsperinningballsstrikesstats"

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        if not self.shouldProcessGame(situationKeysAndPlayLines, gameRuleOptions):
            return
        inningsToKeys : typing.Dict[typing.Tuple[int, bool], typing.List[typing.Tuple[GameSituation, typing.List[BallStrikeCount]]]] = {}
        for situationKeyAndPlayLine in situationKeysAndPlayLines:
            situationKey = situationKeyAndPlayLine.situationKey
            pitches = PlayLineInfo.fromLine(situationKeyAndPlayLine.playLine).pitchesString
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
            # Check if this was a walkoff
            if ((finalGameSituation.inning, finalGameSituation.isHome) == inning):
                endingRunDiff = finalGameSituation.curScoreDiff
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

class StatsRunExpectancyPerInningByInningReport(StatsReport):
    def reportFileName(self) -> str:
        return "analysis/runsByInning/runsperinningbyinningstats"

    def getNextInning(self, inning: typing.Tuple[int, bool]) -> typing.Tuple[int, bool]:
        if (inning[1]):
            return (inning[0]+1, False)
        else:
            return (inning[0], True)

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        if not self.shouldProcessGame(situationKeysAndPlayLines, gameRuleOptions):
            return
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
            # Check if this was a walkoff
            if ((finalGameSituation.inning, finalGameSituation.isHome) == inning):
                endingRunDiff = finalGameSituation.curScoreDiff
            if (endingRunDiff - startingRunDiff < 0):
                print("uh-oh - scored %d runs!" % (endingRunDiff - startingRunDiff))
                assert False
            # Add the statistics now.
            runsGained = endingRunDiff - startingRunDiff
            if (inning in self.stats):
                while (len(self.stats[inning]) < (runsGained + 1)):
                    self.stats[inning].append(0)
            else:
                self.stats[inning] = [0] * (runsGained + 1)
            self.stats[inning][runsGained] += 1

    def writeExtraInfo(self, outputFile, key, value):
        total = sum(value)
        outputFile.write(f"total: {sum(value)}\n")
        weighted_totals = [v * i for (i, v) in enumerate(value)]
        outputFile.write(f"expected value: {sum(weighted_totals)/float(total):.6f}\n")
        percentages = [(v * 100)/float(total) for v in value]
        percentage_strs = ', '.join([f"{p:.2f}%" for p in percentages])
        outputFile.write(f"[{percentage_strs}]\n")
        contribs = ', '.join([f"{w/float(total):.2f}" for w in weighted_totals])
        outputFile.write(f"contribs: [{contribs}]\n")
        outputFile.write("\n")

    def mergeInto(self, other: 'StatsRunExpectancyPerInningByInningReport') -> None:
        for key in self.stats:
            if key in other.stats:
                otherValue = other.stats[key]
                thisValue = self.stats[key]
                for i in range(len(otherValue)):
                    if i >= len(thisValue):
                        break
                    otherValue[i] += thisValue[i]
                for i in range(len(otherValue), len(thisValue)):
                    otherValue.append(thisValue[i])
            else:
                other.stats[key] = self.stats[key]

# Finds games where the home team won after being down by 6 runs in the bottom of the ninth
# with two outs and nobody on base
class HomeTeamWonDownSixWithTwoOutsInNinthReport(Report):
    def __init__(self):
        super().__init__()
        self.gameIds = []

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        homeWon = finalGameSituation.isHomeWinning()
        if (homeWon is None):
            # This game must have been tied when it stopped.  Don't count
            # these stats.
            return
        if not homeWon:
            return
        if (9, True, 2, (0, 0, 0), -6) in [x.situationKey for x in situationKeysAndPlayLines]:
            self.gameIds.append(gameId)

    def doneWithAll(self) -> None:
        for gameId in sorted(self.gameIds):
            print(f"GOT IT with gameId: {gameId}")

    def mergeInto(self, other: 'HomeTeamWonDownSixWithTwoOutsInNinthReport'):
        other.gameIds.extend(self.gameIds)

# Finds games with a specific set of situation keys. Useful for debugging purposes
class SpecificSituationKeysReport(Report):
    def __init__(self):
        super().__init__()
        # Try to look for unusual situations to include here so hopefully there will be only one game
        # that satisfies all of them.
        self.requiredKeys = [
            #(13, True, 1, (1, 0, 1), 0),
            (13, True, 0, (1, 1, 0), 0),
            (13, True, 0, (1, 0, 0), 0),
            (13, False, 1, (0, 1, 0), 0),
            (12, False, 2, (0, 1, 1), 0),
            (11, False, 2, (1, 1, 1), 0),
            (7, False, 2, (1, 0, 1), 0),
            (6, True, 2, (0, 0, 1), 0)
        ]
        # ATL202009300
        self.gameIdsWithInfo = []

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        if gameId == "ATL202009300":
            self.gameIdsWithInfo.append((gameId, [x.situationKey for x in situationKeysAndPlayLines]))
        for requiredKey in self.requiredKeys:
            if requiredKey not in [x.situationKey for x in situationKeysAndPlayLines]:
                return
        self.gameIdsWithInfo.append((gameId, [x.situationKey for x in situationKeysAndPlayLines]))

    def doneWithAll(self) -> None:
        for gameIdAndInfo in sorted(self.gameIdsWithInfo):
            print(f"gameId: {gameIdAndInfo[0]}")
            for x in gameIdAndInfo[1]:
                print(f"  {x}")

    def mergeInto(self, other: 'SpecificSituationKeysReport'):
        other.gameIdsWithInfo.extend(self.gameIdsWithInfo)

# Finds games where the home team won with a walkoff walk on 4 pitches
class WalkOffWalkReport(Report):
    def __init__(self):
        super().__init__()
        self.numGames = 0
        self.numGamesWithPitches = 0
        self.walkOffWalks = 0
        self.walkOffWalksOnFourPitches = 0
        self.yearCount = {}
        self.walkOffWalksOnFourPitchesLines = []

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
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
        playLineInfo = PlayLineInfo.fromLine(lastPlayLine)
        pitches = playLineInfo.pitchesString
        if reallyVerbose:
            print(f"pitches: {pitches}")
        if len([c for c in pitches if c != '?']) > 0:
            self.numGamesWithPitches += 1
        if not homeWon:
            return
        if lastGameSituation.isHome and lastGameSituation.outs <= 2 and lastGameSituation.runners == [1, 1, 1] and lastGameSituation.curScoreDiff == 0:
            playString = playLineInfo.playString
            # TODO - refactor this with main parsing?
            playString = playString.replace('!', '').replace('#', '').replace('?', '')
            playArray = playString.split('.')
            batterEvents = playArray[0].split(';')
            for batterEvent in batterEvents:
                if ((batterEvent.startswith('W') and not batterEvent.startswith('WP')) or batterEvent.startswith('IW') or batterEvent.startswith('I')):
                    # walk
                    self.walkOffWalks += 1
                    self.yearCount[year] += 1
                    lastCount = getBallStrikeCountsFromPitches(pitches)[-1]
                    #print(f"Found game with gameId: {gameId}")
                    #print("Last line was " + lastPlayLine)
                    # U means unknown pitch, so it pretty much can't be a four pitch walk
                    if lastCount.strikes == 0 and lastCount.balls == 4:
                        #print("on four pitches!")
                        self.walkOffWalksOnFourPitches += 1
                        self.walkOffWalksOnFourPitchesLines.append(f"{gameId}: {lastPlayLine}")

    def doneWithAll(self) -> None:
        print(f"numGames: {self.numGames}")
        print(f"numGamesWithPitches: {self.numGamesWithPitches}")
        print(f"walkOffWalks: {self.walkOffWalks}")
        print(f"walkOffWalksOnFourPitches: {self.walkOffWalksOnFourPitches}")
        for year in sorted(self.yearCount.keys()):
            print(f"  {year}: {self.yearCount[year]}")
        #for line in sorted(self.walkOffWalksOnFourPitchesLines):
        #    print(line)

    def mergeInto(self, other: 'WalkOffWalkReport'):
        other.numGames += self.numGames
        other.numGamesWithPitches += self.numGamesWithPitches
        other.walkOffWalks += self.walkOffWalks
        other.walkOffWalksOnFourPitches += self.walkOffWalksOnFourPitches
        for line in self.walkOffWalksOnFourPitchesLines:
            other.walkOffWalksOnFourPitchesLines.append(line)
        for year in self.yearCount:
            if year not in other.yearCount:
                other.yearCount[year] = self.yearCount[year]
            else:
                other.yearCount[year] += self.yearCount[year]

class CountsToWalksAndStrikeoutsReport(Report):
    class CountStats:
        def __init__(self):
            self.total = 0
            self.walks = 0
            self.strikeouts = 0
        def __str__(self):
            walkPercent = (100 * float(self.walks)) / self.total
            strikeoutPercent = (100 * float(self.strikeouts)) / self.total
            return f"total: {self.total} walks: {self.walks} strikeouts: {self.strikeouts} walk%: {walkPercent:.2f} strikeout%: {strikeoutPercent:.2f}"
        def __repr__(self):
            return self.__str__()

    def __init__(self):
        super().__init__()
        self.numGames = 0
        self.numGamesWithPitches = 0
        self.countsStats = {}
        self.yearCount = {}

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
        reallyVerbose = False # gameId == 'CHA201404020'
        self.numGames += 1
        year = int(gameId[3:7])
        for playLine in [x.playLine for x in situationKeysAndPlayLines]:
            if reallyVerbose:
                print(f"playLine: {playLine}")
            playLineInfo = PlayLineInfo.fromLine(playLine)
            pitches = playLineInfo.pitchesString
            if reallyVerbose:
                print(f"pitches: {pitches}")
            if len([c for c in pitches if c != '?']) == 0:
                continue
            if year not in self.yearCount:
                self.yearCount[year] = 0
            self.yearCount[year] += 1
            allCounts = getBallStrikeCountsFromPitches(pitches)
            lastCount = allCounts[-1]
            isWalk = False
            isStrikeout = False
            if lastCount.balls == 4:
                isWalk = True
            elif lastCount.strikes == 3:
                isStrikeout = True
            for count in allCounts:
                if not (count in self.countsStats):
                    self.countsStats[count] = CountsToWalksAndStrikeoutsReport.CountStats()
                self.countsStats[count].total += 1
                if isWalk:
                    self.countsStats[count].walks += 1
                elif isStrikeout:
                    self.countsStats[count].strikeouts += 1
    def doneWithAll(self) -> None:
        print(f"numGames: {self.numGames}")
        for count in sorted(self.countsStats.keys()):
            if count.balls < 4 and count.strikes < 3:
                print(f"{count}: {self.countsStats[count]}")
        for year in sorted(self.yearCount.keys()):
            print(f"PAs in {year}: {self.yearCount[year]}")

    def mergeInto(self, other: 'CountsToWalksAndStrikeoutsReport'):
        other.numGames += self.numGames
        other.numGamesWithPitches += self.numGamesWithPitches
        for count in self.countsStats:
            if count not in other.countsStats:
                other.countsStats[count] = self.countsStats[count]
            else:
                other.countsStats[count].total += self.countsStats[count].total
                other.countsStats[count].walks += self.countsStats[count].walks
                other.countsStats[count].strikeouts += self.countsStats[count].strikeouts
        for year in self.yearCount:
            if year not in other.yearCount:
                other.yearCount[year] = self.yearCount[year]
            else:
                other.yearCount[year] += self.yearCount[year]

class BasesLoadedNoOutsNoRunsReport(Report):
    def __init__(self):
        super().__init__()
        self.numSituations = 0
        self.numZeroRuns = 0

    def getNextInning(self, inning: typing.Tuple[int, bool]) -> typing.Tuple[int, bool]:
        if (inning[1]):
            return (inning[0]+1, False)
        else:
            return (inning[0], True)

    def processedGame(self, gameId: str, finalGameSituation: GameSituation, situationKeysAndPlayLines: typing.List[GameSituationKeyAndNextPlayLine], gameRuleOptions: GameRuleOptions) -> None:
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
                if situation.runners == [1, 1, 1] and situation.outs == 0:
                    self.numSituations += 1
                    runsGained = endingRunDiff - situation.curScoreDiff
                    if runsGained == 0:
                        self.numZeroRuns += 1

    def doneWithAll(self) -> None:
        print(f"{self.numSituations}|{self.numZeroRuns}|{(100.0) * self.numZeroRuns / self.numSituations}")

    def doneWithYear(self, year: str) -> None:
        print(f"{year}|{self.numSituations}|{self.numZeroRuns}|{(100.0) * self.numZeroRuns / self.numSituations}")

    def mergeInto(self, other: 'BasesLoadedNoOutsNoRunsReport'):
        other.numSituations += self.numSituations
        other.numZeroRuns += self.numZeroRuns

def usage():
    print("Usage: parseRetrosheet.py [-t] [-v] [-q] [-s] [-h] [-y] [-r <report name>] [-p] <file paths>")
    print("-t: just run tests")
    print("-v: verbose")
    print("-q: quiet")
    print("-s: skip output, just parse everything and stop on first error")
    print("-h: help")
    print("-y: generate data sorted by year")
    print("-r: specify which reports to run (default: Stats)")
    print("-p: profile and output to file \"profile\"")
    print("-a: run all reports (useful to test changes with -q)")
    print()
    print("Possible reports:")
    for name in sorted(Reports.keys()):
        print("- " + name)

# https://stackoverflow.com/questions/10117073/how-to-use-initializer-to-set-up-my-multiprocess-pool/30816116#30816116
def set_reports(function, reportsToRun, localVerbosity):
    function.originalReportsToRun = reportsToRun
    function.localVerbosity = localVerbosity

# This selects what stats we're compiling.
Reports: typing.Dict[str, typing.Iterable[Report]] = {}
Reports['Stats'] = [StatsWinExpectancyReport(), StatsRunExpectancyPerInningReport()]
Reports['StatsWithBallsStrikes'] = [StatsWinExpectancyWithBallsStrikesReport(), StatsRunExpectancyPerInningWithBallsStrikesReport()]
Reports['RunExpectancyPerInning'] = [StatsRunExpectancyPerInningByInningReport()]
Reports['HomeTeamWonDownSixWithTwoOutsInNinth'] = [HomeTeamWonDownSixWithTwoOutsInNinthReport()]
Reports['SpecificSituationKeys'] = [SpecificSituationKeysReport()]
Reports['WalkOffWalk']= [WalkOffWalkReport()]
Reports['CountsToWalksAndStrikeouts']= [CountsToWalksAndStrikeoutsReport()]
Reports['BasesLoadedNoOutsNoRuns'] = [BasesLoadedNoOutsNoRunsReport()]
reportsToRun = Reports['Stats']
def main(args):
    global verbosity, skipOutput, stopOnFirstError, reportsToRun, sortByYear, doParallel
    doProfile = False
    try:
        opts, files = getopt.getopt(args, 'vhsyqr:pa')
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
        elif o == '-p':
            doProfile = True
        elif o == '-a':
            reportsToRun = []
            for a in Reports:
                reportsToRun.extend(Reports[a])
        else:
            assert False, "unhandled option: " + str(o)
    pr = None
    if doProfile:
        pr = cProfile.Profile()
        pr.enable()

    realFiles = []
    for fileName in files:
        if os.path.isdir(fileName):
            for childFileName in sorted(os.listdir(fileName)):
                realFiles.append(os.path.join(fileName, childFileName))
        else:
            realFiles.append(fileName)

    if doParallel:
        for report in reportsToRun:
            if not report.supportsParallelProcessing():
                print(f"{type(report).__name__} does not support parallel processing!  Using sequential processing instead.")
                doParallel = False

    if sortByYear:
        yearsToFiles = {}
        for fileName in realFiles:
            year = int(os.path.basename(fileName)[:4])
            if year not in yearsToFiles:
                yearsToFiles[year] = []
            yearsToFiles[year].append(fileName)
        if doParallel:
            cpus = os.cpu_count()
            with multiprocessing.Pool(initializer=set_reports, initargs=(parseFilesParallel, reportsToRun, verbosity), processes=cpus) as pool:
                # need to do chunksize=1 to make sure each year is done separately
                years = list(yearsToFiles.keys())
                results = pool.map(parseFilesParallel, [yearsToFiles[year] for year in years], chunksize=1)
                numGames = sum([x[0] for x in results])
                allReportsByYear = [x[1] for x in results]
                for (year, reportsForYear) in zip(years, allReportsByYear):
                    for report in reportsForYear:
                        report.doneWithYear(str(year))
        else:
            for year in sorted(yearsToFiles):
                if verbosity >= Verbosity.normal:
                    print(year)
                for report in reportsToRun:
                    report.clearStats()
                for fileName in yearsToFiles[year]:
                    if verbosity >= Verbosity.normal:
                        print(fileName)
                    eventFile = open(fileName, 'r', encoding='latin-1')
                    parseFile(eventFile, fileName, reportsToRun)
                    eventFile.close()
                if not skipOutput:
                    for report in reportsToRun:
                        report.doneWithYear(str(year))
    else:
        if doParallel:
            cpus = os.cpu_count()
            with multiprocessing.Pool(initializer=set_reports, initargs=(parseFilesParallel, reportsToRun, verbosity), processes=cpus) as pool:
                results = pool.map(parseFilesParallel, [[x] for x in realFiles])
                numGames = sum([x[0] for x in results])
                allReports = [x[1] for x in results]
                for (i, report) in enumerate(reportsToRun):
                    for clonedReport in [x[i] for x in allReports]:
                        clonedReport.mergeInto(report)
        else:
            numGames = 0
            for fileName in realFiles:
                if verbosity >= Verbosity.normal:
                    print(fileName)
                eventFile = open(fileName, 'r', encoding='latin-1')
                numGames += parseFile(eventFile, fileName, reportsToRun)[0]
                eventFile.close()
        if verbosity >= Verbosity.normal:
            print("numGames is %d" % numGames)
        if not skipOutput:
            for report in reportsToRun:
                report.doneWithAll()
    if doProfile:
        assert pr is not None
        pr.disable()
        pr.dump_stats('profile')

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
        return (situation, 'play,' + str(inning) + ',' + ('1' if situation.isHome else '0') + ',,,,' + playString)
    
    def test_simpleout(self):
        (situation, playString) = self.util_setup(0, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_simpleout_oneout(self):
        (situation, playString) = self.util_setup(1, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 2
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_top(self):
        (situation, playString) = self.util_setup(2, False, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 0
        sitCopy.isHome = True
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_bottom(self):
        (situation, playString) = self.util_setup(2, True, '8')
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 0
        sitCopy.isHome = False
        sitCopy.inning = 2
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_top_clearrunners(self):
        (situation, playString) = self.util_setup(2, False, '8')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 0
        sitCopy.isHome = True
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_simpleout_nextinning_bottom_clearrunners(self):
        (situation, playString) = self.util_setup(2, True, '8')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 0
        sitCopy.isHome = False
        sitCopy.inning = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_forceout(self):
        (situation, playString) = self.util_setup(0, False, '83')
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceFirstSecond(self):
        (situation, playString) = self.util_setup(0, False, '8.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThird(self):
        (situation, playString) = self.util_setup(0, False, '8.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_out_advanceThirdScore(self):
        (situation, playString) = self.util_setup(0, False, '8.3-H')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThirdScore(self):
        (situation, playString) = self.util_setup(0, False, '8.2-3;3-H')
        situation.runners = [0, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 1]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_out_advanceSecondThirdAllScore(self):
        (situation, playString) = self.util_setup(0, False, '8.2-H;3-H')
        situation.runners = [0, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 2
        self.assertEqual(sitCopy, situation)

    def test_groundout_advance(self):
        (situation, playString) = self.util_setup(0, False, '54(B)/BG25/SH.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_groundout_safe_and_score(self):
        (situation, playString) = self.util_setup(0, False, '54(1)/FO/G5.3-H;B-1')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        sitCopy.curScoreDiff = 1
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_explicit_sacrifice(self):
        (situation, playString) = self.util_setup(0, False, '23/SH.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay(self):
        (situation, playString) = self.util_setup(0, False, '64(1)3/GDP/G6')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay_lineout(self):
        (situation, playString) = self.util_setup(0, False, '8(B)84(2)/LDP/L8')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_doubleplay_lineout_unassisted(self):
        (situation, playString) = self.util_setup(0, False, '3(B)3(1)/LDP')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 2
        sitCopy.runners = [0, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference_runner(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_catchers_interference_runner_explicit(self):
        (situation, playString) = self.util_setup(0, False, 'C/E2.B-1;1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_pitchers_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E1')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_first_basemans_interference(self):
        (situation, playString) = self.util_setup(0, False, 'C/E3')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_single(self):
        (situation, playString) = self.util_setup(0, False, 'S7')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_double(self):
        (situation, playString) = self.util_setup(0, False, 'D7/G5.3-H;2-H;1-H')
        situation.runners = [1, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_triple(self):
        (situation, playString) = self.util_setup(0, False, 'T9/F9LD.2-H')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 1]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_groundrule_double(self):
        (situation, playString) = self.util_setup(0, False, 'DGR/L9LS.2-H')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_throwing_error(self):
        (situation, playString) = self.util_setup(0, False, 'E1/TH/BG15.1-3')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_fielding_error(self):
        (situation, playString) = self.util_setup(0, False, 'E3.1-2;B-1')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_fielders_choice_out_at_home(self):
        (situation, playString) = self.util_setup(0, False, 'FC5/G5.3XH(52)')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_fielders_choice_no_outs(self):
        (situation, playString) = self.util_setup(0, False, 'FC3/G3S.3-H;1-2')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_error_on_foul_ball(self):
        (situation, playString) = self.util_setup(0, False, 'FLE5/P5F')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_home_run(self):
        (situation, playString) = self.util_setup(0, False, 'H/L7D')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_home_run_explicit_runners(self):
        (situation, playString) = self.util_setup(0, False, 'HR/F78XD.2-H;1-H')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park(self):
        (situation, playString) = self.util_setup(0, False, 'HR9/F9LS.3-H;1-H')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park_just_h(self):
        (situation, playString) = self.util_setup(0, False, 'H9/F9LS.3-H;1-H')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 3
        self.assertEqual(sitCopy, situation)

    def test_home_run_inside_park_just_h_no_runners(self):
        (situation, playString) = self.util_setup(0, False, 'H9/F9LS')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_hit_by_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'HP.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_hit_by_pitch_no_runners(self):
        (situation, playString) = self.util_setup(0, False, 'HP')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_strikeout(self):
        (situation, playString) = self.util_setup(0, False, 'K')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout(self):
        (situation, playString) = self.util_setup(0, False, 'K23')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_passed_ball(self):
        (situation, playString) = self.util_setup(0, False, 'K+PB.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_miscue(self):
        (situation, playString) = self.util_setup(0, False, 'K+WP.B-1')
        situation.runners = [0, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout_other_runner_advance(self):
        (situation, playString) = self.util_setup(0, False, 'K23+WP.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 1]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_strikeout_putout_caught_stealing(self):
        # see game BAL196505282, end of 5th inning
        (situation, playString) = self.util_setup(0, False, 'K23+CS3(34)/DP')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 2
        self.assertEqual(sitCopy, situation)

    def test_no_play(self):
        (situation, playString) = self.util_setup(0, False, 'NP')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_walk(self):
        (situation, playString) = self.util_setup(0, False, 'W.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_intentional_walk(self):
        (situation, playString) = self.util_setup(0, False, 'IW')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_walk_wild_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'W+WP.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_balk(self):
        (situation, playString) = self.util_setup(0, False, 'BK.3-H;1-2')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing(self):
        (situation, playString) = self.util_setup(0, False, 'CSH(12)')
        situation.runners = [0, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing_advance(self):
        (situation, playString) = self.util_setup(0, False, 'CS2(24).2-3')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 1]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_caught_stealing_error(self):
        (situation, playString) = self.util_setup(0, False, 'CS2(2E4).1-3')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_defensive_indifference(self):
        (situation, playString) = self.util_setup(0, False, 'DI.1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_other_advance(self):
        # "Thompson out trying to advance after ball eluded catcher"
        (situation, playString) = self.util_setup(0, False, 'OA.2X3(25)')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_wild_pitch(self):
        (situation, playString) = self.util_setup(0, False, 'WP.2-3;1-2')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 1]
        self.assertEqual(sitCopy, situation)

    def test_passed_ball(self):
        (situation, playString) = self.util_setup(0, False, 'PB.2-3')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 1]
        self.assertEqual(sitCopy, situation)

    def test_pickoff(self):
        (situation, playString) = self.util_setup(0, False, 'PO2(14)')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_pickoff_error(self):
        (situation, playString) = self.util_setup(0, False, 'PO1(E3).1-2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_pickoff_caught_stealing(self):
        (situation, playString) = self.util_setup(0, False, 'POCS2(14)')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 0, 0]
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_stolen_base(self):
        (situation, playString) = self.util_setup(0, False, 'SB2')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_stolen_base_multiple(self):
        (situation, playString) = self.util_setup(0, False, 'SB3;SB2')
        situation.runners = [1, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 1]
        self.assertEqual(sitCopy, situation)

    def test_stolen_base_multiple_home(self):
        (situation, playString) = self.util_setup(0, False, 'SBH;SB2')
        situation.runners = [1, 0, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [0, 1, 0]
        sitCopy.curScoreDiff = 1
        self.assertEqual(sitCopy, situation)

    def test_weird_error_running(self):
        # game KCA200607040, bottom of the 3rd
        (situation, playString) = self.util_setup(0, False, 'S7/L.3-H;2-H;1XH(7432/TH)(E7)')
        situation.runners = [1, 1, 1]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 0, 0]
        sitCopy.curScoreDiff = 2
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_error_running(self):
        # game KCA200607210, bottom of the 3rd
        (situation, playString) = self.util_setup(0, False, 'FC1.1X2(6E4);B-1')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.runners = [1, 1, 0]
        self.assertEqual(sitCopy, situation)

    def test_putout_runner_at_wrong_base(self):
        # game DET196405140, bottom of the 4th
        (situation, playString) = self.util_setup(0, False, '36(1)/BF.B-1')
        situation.runners = [1, 0, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        self.assertEqual(sitCopy, situation)

    def test_walk_plus_putout_caught_stealing(self):
        # game CHN201708160, bottom of the 4th
        (situation, playString) = self.util_setup(0, False, 'W+POCS3(26)')
        situation.runners = [0, 1, 0]
        sitCopy = situation.copy()
        parsePlay(playString, situation, GameRuleOptions())
        sitCopy.outs = 1
        sitCopy.runners = [1, 0, 0]
        self.assertEqual(sitCopy, situation)

    # Not sure how we could parse this, so not running this test
    #def test_tagout_with_errors_run_scores(self):
    #    # game BAL201906250, bottom of the 3rd
    #    (situation, playString) = self.util_setup(2, False, 'D9/G+.1-H;BX3(E9)(95/TH)')
    #    situation.runners = [1, 0, 0]
    #    sitCopy = situation.copy()
    #    parsePlay(playString, situation, GameRuleOptions())
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


