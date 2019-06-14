# baseballstats
Baseball win expectancy and expected runs per inning calculators

This is the source for the [win expectancy calculator](https://gregstoll.com/~gregstoll/baseball/stats.html) and [expected runs in an inning calculator](https://gregstoll.com/~gregstoll/baseball/runsperinning.html).

The main script is [`parseretrosheet.py`](https://github.com/gregstoll/baseballstats/blob/master/parseretrosheet.py), which parses play-by-play files in the [Retrosheet](http://www.retrosheet.org/game.htm) format.  To run the script you should download the files from Retrosheet and put them in a `data` directory.

Other interesting files:
* [`getcumulativestats.py`](https://github.com/gregstoll/baseballstats/blob/master/getcumulativestats.py) - the CGI script that the web page calls
* [`processstats.py`](https://github.com/gregstoll/baseballstats/blob/master/processstats.py) - puts the Retrosheet data in the [`probs.txt`](https://github.com/gregstoll/baseballstats/blob/master/probs.txt) file.  See [Phil Birnbaum's description of the data file](http://www.philbirnbaum.com/probs2.txt).

See the `HOWTO` file for how to update everything after adding more data.

The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd., Newark, DE 19711.
