#!/usr/bin/python

import cgi, os, sys, Gnuplot, re, os.path, urlparse, shutil, time
from getstats import getProbability
from tempfile import mkstemp

form = cgi.FieldStorage()
print 'Content-type: text/html\n\n'
print '<html><head></head><body>\n'
#for key in form:
    #print '<p>%s: %s</p>' % (key, form[key].value)
for key in form:
    situationMatch = re.match(r'^situation(\d+)$', key)
    if (situationMatch):
        lastSituation = int(situationMatch.group(1))
probs = []
inningStarts = []
for i in range(0, lastSituation + 1):
    inningCombined = form["inning%d" % i].value
    outs = int(form["outs%d" % i].value)
    runners = int(form["runner%d" % i].value)
    scoreDiff = int(form["score%d" % i].value)
    if (len(inningStarts) == 0 or inningCombined != inningStarts[-1][0]):
        inningStarts.append((inningCombined, i))
    homeOrVisitor = inningCombined[0]
    inning = int(inningCombined[1:])
    prob = getProbability(homeOrVisitor, inning, outs, runners, scoreDiff)
    # We want to show home probabilities
    if (homeOrVisitor == 'V'):
        prob = 1 - prob
    probs.append(prob)
#for key in os.environ:
    #print "<p>%s: %s</p>" % (key, os.environ[key])
(tempPngFile, tempPngFileName) = mkstemp(suffix=".png")
os.close(tempPngFile)
g = Gnuplot.Gnuplot()
g('set data style linespoints')
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
print '</body></html>'
