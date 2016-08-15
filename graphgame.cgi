#!/usr/bin/python

import cgi, os, sys, Gnuplot, re, os.path, urlparse, shutil, time
from getstats import getProbability
from getstats import getProbabilityOfString
from tempfile import mkstemp

form = cgi.FieldStorage()
print 'Content-type: text/html\n\n'
print '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
print '<html><head><title>Win probability graph</title></head><body>'
print '<p>These image files are cleaned out every few hours, so please download a copy of the image if you want to keep it. Or see <a href=\"#text\">below</a> to save a text representation that can be easily re-entered.</p>'
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
        directSituationLines = [line for line in directSituationLines if (not line.startswith('//'))]
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
    else:
        # Correct for end conditions
        if (inning >= 9 and homeOrVisitor == 'H' and scoreDiff > 0):
            prob = 1
            probs.append(prob)
            xValues.append(i)
        elif (inning > 9 and homeOrVisitor == 'V' and scoreDiff > 0):
            prob = 0
            probs.append(prob)
            xValues.append(i)
        else:
            # We should never see this value in the graph, but we need to keep
            # the probs list in sync.
            # TODO - put a marker on the graph?
            probs.append(-1)
    if (homeOrVisitor == lastHomeOrVisitor):
        if (scoreDiff != lastScoreDiff):
            runEntries[homeOrVisitor].append((i, scoreDiff - lastScoreDiff))
    else:
        if (scoreDiff != -1 * lastScoreDiff):
            runEntries[lastHomeOrVisitor].append((i, -1 * lastScoreDiff - scoreDiff))
    lastHomeOrVisitor = homeOrVisitor
    lastScoreDiff = scoreDiff
if (inningStarts[-1][1] == lastSituation):
    # This is just an entry to show the final outcome of the game, so don't
    # plot on x-axis.
    inningStarts = inningStarts[:-1]
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
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], title='Runs for Home', with_='points linetype 2 pointtype 4 pointsize %d' % pointSize))
                    haveTitled = True
                else:
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], with_='points linetype 2 pointtype 4 pointsize %d' % pointSize))
    if ('V' in pointsToPlot and len(pointsToPlot['V']) > 0):
        haveTitled = False
        for pointToPlot in pointsToPlot['V']:
            for pointSize in range(1, pointToPlot[2] + 1):
                if (doKey and not haveTitled and pointSize == 1):
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], title='Runs for Visitor', with_='points linetype 3 pointtype 4 pointsize %d' % pointSize))
                    haveTitled = True
                else:
                    g.replot(Gnuplot.Data([(pointToPlot[0], pointToPlot[1])], with_='points linetype 3 pointtype 4 pointsize %d' % pointSize))
if (doKey):
    g('set key on left top reverse Left')
else:
    g('set key off')
pngOptions = ""
# TODO - make the size an option.
if (xValues[-1] >= 100):
    # More than 100 entries means we're kind of long, so make the graph bigger.
    if (xValues[-1] >= 150):
        pngOptions = "size %d, %d" % (1024, 768)
    else:
        pngOptions = "size %d, %d" % (800, 600)
g('set terminal png %s ' % pngOptions)
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
print '<p><a name=\"text\">Here is a text representation of the game that you can use to input again:</p>'
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
# TODO - output .csv representation of probs or something?
print '<p><a href="https://validator.w3.org/check?uri=referer"><img src="https://www.w3.org/Icons/valid-html401" alt="Valid HTML 4.01 Transitional" height="31" width="88"></a></p>'
print '<script src="//www.google-analytics.com/urchin.js" type="text/javascript"></script>'
print '<script type="text/javascript">'
print '_uacct = "UA-362292-1";'
print 'urchinTracker();'
print '</script>'
print '</body></html>'
