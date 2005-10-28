#!/usr/bin/python

import cgi, os, sys, Gnuplot, re, os.path, urlparse, shutil, time
from getstats import getProbability
from getstats import getProbabilityOfString
from tempfile import mkstemp

form = cgi.FieldStorage()
print 'Content-type: text/html\n\n'
print '<html><head></head><body>\n'
#for key in form:
    #print '<p>%s: %s</p>' % (key, form[key].value)
hasDirectText = False
for key in form:
    situationMatch = re.match(r'^situation(\d+)$', key)
    if (situationMatch):
        lastSituation = int(situationMatch.group(1))
    elif (key == 'directtext'):
        hasDirectText = True
        directSituationLines = form["directtext"].value.split("\n")
        directSituationLines = [line.strip() for line in directSituationLines]
        directSituationLines = [line for line in directSituationLines if line != '']
        lastSituation = len(directSituationLines) - 1
probs = []
inningStarts = []
for i in range(0, lastSituation + 1):
    if (not hasDirectText):
        inningCombined = form["inning%d" % i].value
        outs = int(form["outs%d" % i].value)
        runners = int(form["runner%d" % i].value)
        scoreDiff = int(form["score%d" % i].value)
        if (len(inningStarts) == 0 or inningCombined != inningStarts[-1][0]):
            inningStarts.append((inningCombined, i))
        homeOrVisitor = inningCombined[0]
        inning = int(inningCombined[1:])
        prob = getProbability(homeOrVisitor, inning, outs, runners, scoreDiff)
    else:
        curLine = directSituationLines[i]
        homeOrVisitor = curLine[1:2]
        inningCombined = ''.join(''.join(curLine.split(",")[:2]).split('"'))
        if (len(inningStarts) == 0 or inningCombined != inningStarts[-1][0]):
            inningStarts.append((inningCombined, i))
        curLine = curLine.strip()
        prob = getProbabilityOfString(curLine)
    # We want to show home probabilities
    if (homeOrVisitor == 'V'):
        prob = 1 - prob
    probs.append(prob)
#for key in os.environ:
    #print "<p>%s: %s</p>" % (key, os.environ[key])
(tempPngFile, tempPngFileName) = mkstemp(suffix=".png")
os.close(tempPngFile)
g = Gnuplot.Gnuplot()
g('set data style lines')
g('set terminal png')
g('set yrange[0:1]')
g('set ylabel "Win Probability"')
g('set ytics 0, .1, 1.0')
g('set output "%s"' % tempPngFileName)
g('set title "Home win probability"')
# Build the string for the xticks
xTicksString = "("
for entry in inningStarts:
    combinedInning = entry[0]
    index = entry[1]
    if (index != 0):
        xTicksString = xTicksString + ", "
    xTicksString = xTicksString + '"%s" %d' % (combinedInning, index)
xTicksString = xTicksString + ")"
if (len(xTicksString) > 2):
    g('set xtics %s' % xTicksString)
    g('set grid ytics xtics')
else:
    g('set grid ytics')
g.plot(probs)
# This is necessary so the file has data when we copy it - apparently
# g.plot() is a little asynchronous or something.
time.sleep(.5)
pictureName = os.path.join(os.getcwd() + '/images', os.path.basename(tempPngFileName))
#print "<p>%s to %s</p>" % (newTempName, pictureName)
shutil.copyfile(tempPngFileName, pictureName)
urlName = urlparse.urljoin(os.environ['SCRIPT_URI'], 'images/' + os.path.basename(pictureName))
print '<img src="%s">' % urlName
print '<p>Here is a text representation of the game that you can use to input again:</p>'
print '<pre>'
# print out textual representation
for i in range(0, lastSituation + 1):
    if (not hasDirectText):
        inningCombined = form["inning%d" % i].value
        outs = int(form["outs%d" % i].value)
        runners = int(form["runner%d" % i].value)
        scoreDiff = int(form["score%d" % i].value)
        homeOrVisitor = inningCombined[0]
        inning = int(inningCombined[1:])
        print '"%s",%d,%d,%d,%d' % (homeOrVisitor, inning, outs, runners, scoreDiff)
    else:
        print directSituationLines[i]
print '</pre>'
print '</body></html>'
