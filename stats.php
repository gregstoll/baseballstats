<?php
$probsFileName = "probs.txt";

print "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\">\n";
print "<html><head><title>Win Expectancy Finder</title>\n";
print "<style type=\"text/css\">\n";
print "  P.littlespace {margin: 2px;}\n";
print "</style></head>\n";
print "<body>\n";
print "<form action=\"" . basename($PHP_SELF) . "\" method=\"GET\">\n";
print "<p class=\"littlespace\">Team:\n";
$isSubmitted = isset($_GET["team"]) && isset($_GET["inning"]) && isset($_GET["outs"]) && isset($_GET["runners"]) && isset($_GET["scorediff"]);
if (!isSubmitted) {
    $toSelect = "H";
} else {
    $toSelect = $_GET["team"];
}
print "<input type=\"radio\" name=\"team\" value=\"H\"";
if ($toSelect == "H") {
    print "checked";
}
print ">Home\n";
print "<input type=\"radio\" name=\"team\" value=\"V\"";
if ($toSelect == "V") {
    print "checked";
}
print ">Visitor\n";
print "<p class=\"littlespace\">Inning: <select name=\"inning\">\n";
for ($i = 1; $i <= 15; $i++) {
    print "<option value=\"$i\"";
    if ((!$isSubmitted && $i == 1) ||
        ($isSubmitted && $i == $_GET["inning"])) {
        print " selected";
    }
    print ">$i</option>\n";
}
print "</select>\n";
print "<p class=\"littlespace\">Outs: <select name=\"outs\">\n";
for ($i = 0; $i <= 2; $i++) {
    print "<option value=\"$i\"";
    if ((!$isSubmitted && $i == 0) ||
        ($isSubmitted && $i == $_GET["outs"])) {
        print " selected";
    }
    print ">$i</option>\n";
}
print "</select>\n";
print "<p class=\"littlespace\">Runners on base: <select name=\"runners\">\n";
if (!$isSubmitted) {
    $toSelect = 1;
} else {
    $toSelect = $_GET["runners"];
}
$runnerText = array(1 => "none",
2 => "1st",
3 => "2nd",
4 => "1st &amp; 2nd",
5 => "3rd",
6 => "1st &amp; 3rd",
7 => "2nd &amp; 3rd",
8 => "loaded");
for ($i = 1; $i <= 8; $i++) {
    print "<option value=\"$i\"";
    if ($toSelect == $i) {
        print " selected";
    }
    print ">" . $runnerText[$i] . "</option>\n";
}
print "</select>\n";
print "<p class=\"littlespace\">Score difference: <select name=\"scorediff\">\n";
for ($i = -8; $i <= 8; $i++) {
    print "<option value=\"$i\"";
    if ((!$isSubmitted && $i == 0) ||
        ($isSubmitted && $i == $_GET["scorediff"])) {
        print " selected";
    }
    print ">$i</option>\n";
}
print "</select>\n";
print "<p class=\"littlespace\"><input type=\"submit\" value=\"Get expectancy\"></p>\n";
print "</form>\n";
if ($isSubmitted) {
    $lineToLookFor = "\"" . $_GET["team"] . "\"," . $_GET["inning"] . "," . $_GET["outs"] . "," . $_GET["runners"] . "," . $_GET["scorediff"] . ",";
    print "<!-- Line to look for: $lineToLookFor -->\n";
    $foundData = 0;
    $lines = file($probsFileName);
    foreach ($lines as $line_num => $line) {
        if (strpos($line, $lineToLookFor) === 0) {
            $lastCommaPos = strrpos($line, ",");
            $lastCommaPos2 = strrpos(substr($line, 0, $lastCommaPos), ",");
            $totalGames = (integer) substr($line, $lastCommaPos2 + 1, ($lastCommaPos - $lastCommaPos2 - 1));
            $wins = (integer) substr($line, $lastCommaPos + 1);
            print "<p class=\"littlespace\">Total games: $totalGames</p><p class=\"littlespace\">Wins: $wins</p><p class=\"littlespace\"><b>Win percentage</b>: ";
            if ($wins == $totalGames) {
                print "1";
            } else {
                print "0" . substr($wins/$totalGames, 1, 6);
            }
            print "</p>\n";
            $foundData = 1;
        }
    }
    if ($foundData == 0) {
        print "<p>No data available</p>\n";
    }

}
?>
<p>To make a graph of the Win Expectancy of a baseball game, use the <a href="graphgame.html">graph a game</a> tool.</p>
<p>This data is from MLB games from 1957-2005 (excluding 1999). It now includes almost all regular-season event files available at <a href="http://www.retrosheet.org/game.htm">Retrosheet</a>.</p>
<p>Idea taken from <a href="http://walkoffbalk.com/tools/winexp/index.php">Win Expectancy Finder</a> at <a href="http://walkoffbalk.com">walkoffbalk.com</a>.  Here's a <a href="http://www.hardballtimes.com/main/article/the-one-about-win-probability/">good article about Win Expectancy</a>.</p>
<ul>
<li><a href="stats.txt">stats.php</a> - the source for .php file</li>
<li><a href="parseretrosheet.txt">parseretrosheet.py</a> - parses the <a href="http://www.retrosheet.org/game.htm">Retrosheet data</a></li>
<li><a href="processstats.txt">processstats.py</a> - puts the Retrosheet data in the <a href="probs.txt">probs.txt</a> file.  See <a href="http://www.philbirnbaum.com/probs2.txt">Phil Birnbaum's description of the data file</a>.</li>
</ul>
<p>The information used here was obtained free of charge from and is copyrighted by Retrosheet.  Interested parties may contact Retrosheet at 20 Sunset Rd., Newark, DE 19711.</p>
<p><a href="/">Greg's home page</a></p>
<p><a href="index.html">Baseball statistic calculators</a></p>
<p>
    <a href="http://validator.w3.org/check?uri=referer"><img
        src="http://www.w3.org/Icons/valid-html401"
        alt="Valid HTML 4.01 Transitional" height="31" width="88"></a>
</p>
<script src="http://www.google-analytics.com/urchin.js" type="text/javascript"></script>
<script type="text/javascript">
_uacct = "UA-362292-1";
urchinTracker();
</script>
</body></html>
