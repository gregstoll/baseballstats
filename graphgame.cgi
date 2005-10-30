#!/usr/bin/python

import cgi, os, sys, Gnuplot, re, os.path, urlparse, shutil, time
from getstats import getProbability
from getstats import getProbabilityOfString
from tempfile import mkstemp

form = cgi.FieldStorage()
print 'Content-type: text/html\n\n'
print '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
print '<html><head><title>Win probability graph</title></head><body>'
print '<p>These image files are cleaned out every few hours, so please download a copy of the image if you want to keep it.</p>'
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
title = form["title"].value
if ("doKey" in form):
    doKey = form["doKey"].value
else:
    doKey = False
if ("doRunsScored" in form):
    doRunsScored = form["doRunsScored"].value
else:
    doRunsScored = False
if (not doRunsScored):
    doKey = False
probs = []
xValues = []
inningStarts = []
# Stores (frame number, change in score)
runEntries = {}
runEntries['H'] = []
runEntries['V'] = []
lastScoreDiff = 0
lastHomeOrVisitor = 'H'
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
        curLine = curLine.strip()
        curLineComponents = curLine.split(',')
        homeOrVisitor = curLineComponents[0][1:2]
        inning = int(curLineComponents[1])
        inningCombined = homeOrVisitor + str(inning)
        runners = int(curLineComponents[3])
        outs = int(curLineComponents[2])
        scoreDiff = int(curLineComponents[4])
        if (len(inningStarts) == 0 or inningCombined != inningStarts[-1][0]):
            inningStarts.append((inningCombined, i))
        prob = getProbabilityOfString(curLine)
    # Keep a list of x-values, too
    if (prob != -1):
        # We want to show home probabilities
        if (homeOrVisitor == 'V'):
            prob = 1 - prob
        probs.append(prob)
        xValues.append(i)
    if (homeOrVisitor == lastHomeOrVisitor):
        if (scoreDiff != lastScoreDiff):
            runEntries[homeOrVisitor].append((i, scoreDiff - lastScoreDiff))
    else:
        if (scoreDiff != -1 * lastScoreDiff):
            runEntries[lastHomeOrVisitor].append((i, -1 * lastScoreDiff - scoreDiff))
    lastHomeOrVisitor = homeOrVisitor
    lastScoreDiff = scoreDiff
#for key in os.environ:
    #print "<p>%s: %s</p>" % (key, os.environ[key])
(tempPngFile, tempPngFileName) = mkstemp(suffix=".png")
os.close(tempPngFile)
g = Gnuplot.Gnuplot()
g('set data style lines')
g('set yrange[0:1]')
g('set ylabel "Win Probability"')
g('set ytics 0, .1, 1.0')
g('set title "%s"' % title)
# Build the string for the xticks
xTicksString = "("
for entry in inningStarts:
    combinedInning = entry[0]
    index = entry[1]
    if (index != 0):
        xTicksString = xTicksString + ", "
    xTicksString = xTicksString + '"%s" %d' % (combinedInning, index)
xTicksString = xTicksString + ")"
# Find the points where runs were scored.
if (doRunsScored):
    pointsToPlot = {}
    for homeOrVisitor in runEntries.keys():
        if (homeOrVisitor == 'H'):
            lineType = 2
        else:
            lineType = 3
        pointsToPlot[homeOrVisitor] = []
        for runTuple in runEntries[homeOrVisitor]:
            index = runTuple[0]
            yVal = probs[index]
            pointsToPlot[homeOrVisitor].append((index, yVal, runTuple[1]))
if (len(xTicksString) > 2):
    g('set xtics %s' % xTicksString)
    g('set grid ytics xtics')
else:
    g('set grid ytics')
g.plot(zip(xValues, probs))
# Plot the points where runs were scored
# Indicate how many runs scored by the number of boxes around it (the boxes
# get bigger)
if (doRunsScored):
    if ('H' in pointsToPlot and len(pointsToPlot['H']) > 0):
        haveTitled = False
        for pointToPlot in pointsToPlot['H']:
            for pointSize in range(1, pointToPlot[2] + 1):
                if (doKey and not haveTitled and pointSize == 1):
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], title='Runs for Home', with='points linetype 2 pointtype 4 pointsize %d' % pointSize))
                    haveTitled = True
                else:
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], with='points linetype 2 pointtype 4 pointsize %d' % pointSize))
    if ('V' in pointsToPlot and len(pointsToPlot['V']) > 0):
        haveTitled = False
        for pointToPlot in pointsToPlot['V']:
            for pointSize in range(1, pointToPlot[2] + 1):
                if (doKey and not haveTitled and pointSize == 1):
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], title='Runs for Visitor', with='points linetype 3 pointtype 4 pointsize %d' % pointSize))
                    haveTitled = True
                else:
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], with='points linetype 3 pointtype 4 pointsize %d' % pointSize))
if (probs[-1] > .5):
    keyLocation = "bottom"
else:
    keyLocation = "top"
if (doKey):
    g('set key on %s' % keyLocation)
else:
    g('set key off')
g('set terminal png')
g('set output "%s"' % tempPngFileName)
g.refresh()
# This is necessary so the file has data when we copy it - apparently
# g.plot() is a little asynchronous or something.
time.sleep(0.5)
pictureName = os.path.join(os.getcwd() + '/images', os.path.basename(tempPngFileName))
#print "<p>%s to %s</p>" % (newTempName, pictureName)
shutil.copyfile(tempPngFileName, pictureName)
urlName = urlparse.urljoin(os.environ['SCRIPT_URI'], 'images/' + os.path.basename(pictureName))
print '<img src="%s" alt="Win probability graph">' % urlName
if (doRunsScored):
    print '<p>Note that the number of boxes around a point indicate the number of runs scored on that play.</p>'
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
print '<p><a href="http://validator.w3.org/check?uri=referer"><img src="http://www.w3.org/Icons/valid-html401" alt="Valid HTML 4.01 Transitional" height="31" width="88"></a></p>'
print '</body></html>'
