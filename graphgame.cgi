#!/usr/bin/python

import cgi, os, sys, Gnuplot, re, os.path, urlparse, shutil
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
for i in range(0, lastSituation + 1):
    inningCombined = form["inning%d" % i].value
    outs = int(form["outs%d" % i].value)
    runners = int(form["runner%d" % i].value)
    scoreDiff = int(form["score%d" % i].value)
    homeOrVisitor = inningCombined[0]
    inning = int(inningCombined[1:])
    prob = getProbability(homeOrVisitor, inning, outs, runners, scoreDiff)
    # We want to show home probabilities
    if (homeOrVisitor == 'V'):
        prob = 1 - prob
    probs.append(prob)
#for key in os.environ:
    #print "<p>%s: %s</p>" % (key, os.environ[key])
(tempPsFile, tempPsFileName) = mkstemp(suffix=".ps")
tempPngFileName = tempPsFileName[:-3] + ".png"
g = Gnuplot.Gnuplot()
g('set data style linespoints')
# TODO - try using png terminal
g('set terminal postscript color')
g('set yrange[0:1]')
g('set ylabel "Win Probability"')
g('set ytics 0, .1, 1.0')
g('set grid ytics')
g('set output "%s"' % tempPsFileName)
g('set title "Home win probability"')
g.plot(probs)
os.system('pstoimg -type png -flip cw %s > /dev/null' % tempPsFileName)
os.close(tempPsFile)
pictureName = os.path.join(os.getcwd() + '/images', os.path.basename(tempPngFileName))
shutil.move(tempPngFileName, pictureName)
urlName = urlparse.urljoin(os.environ['SCRIPT_URI'], 'images/' + os.path.basename(pictureName))
print '<img src="%s">' % urlName
print '</body></html>'
