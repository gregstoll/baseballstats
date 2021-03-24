# baseballstats
Baseball win expectancy and expected runs per inning calculators

This is the source for the [win expectancy calculator](https://gregstoll.com/~gregstoll/baseball/stats.html) and [expected runs in an inning calculator](https://gregstoll.com/~gregstoll/baseball/runsperinning.html).

The main scripts are [`main.rs`](https://github.com/gregstoll/baseballstats/blob/master/retrosheet_stats/src/main.rs) (in Rust) and [`parseretrosheet.py`](https://github.com/gregstoll/baseballstats/blob/master/parseretrosheet.py) (in Python), both of which parse play-by-play files in the [Retrosheet](http://www.retrosheet.org/game.htm) format. The scripts are designed to work identically; presumably the Rust version will run faster. To run the script you should download the files from Retrosheet and put them in a `data` directory.

Other interesting files:
* [`getcumulativestats.py`](https://github.com/gregstoll/baseballstats/blob/master/getcumulativestats.py) - the CGI script that the web page calls
* [`processstats.py`](https://github.com/gregstoll/baseballstats/blob/master/processstats.py) - puts the Retrosheet data in the [`probs.txt`](https://github.com/gregstoll/baseballstats/blob/master/probs.txt) file.  See [Phil Birnbaum's description of the data file](http://www.philbirnbaum.com/probs2.txt).

See the [`HOWTO`](https://github.com/gregstoll/baseballstats/blob/master/HOWTO) file for how to update everything after adding more data.

[This article](https://gregstoll.wordpress.com/2021/01/10/parsing-baseball-files-in-rust-instead-of-python-for-an-8x-speedup/) talks about the process of porting the script from Python to Rust.

The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd., Newark, DE 19711.
