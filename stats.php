<?php
$probsFileName = "probs.txt";

print "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\">\n";
print "<html><head><title>Win Expectancy Finder</title>\n";
print "<style type=\"text/css\">\n";
print "  P.littlespace {margin: 2px;}\n";
print "</style></head>\n";
print "<body>\n";
print "<form action=\"" . basename($PHP_SELF) . "\" method=\"post\">\n";
print "<p class=\"littlespace\">Team:\n";
if (!isset($_POST["expectancy"])) {
    $toSelect = "H";
} else {
    $toSelect = $_POST["team"];
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
    if ((!isset($_POST["expectancy"]) && $i == 1) ||
        (isset($_POST["expectancy"]) && $i == $_POST["inning"])) {
        print " selected";
    }
    print ">$i</option>\n";
}
print "</select>\n";
print "<p class=\"littlespace\">Outs: <select name=\"outs\">\n";
for ($i = 0; $i <= 2; $i++) {
    print "<option value=\"$i\"";
    if ((!isset($_POST["expectancy"]) && $i == 0) ||
        (isset($_POST["expectancy"]) && $i == $_POST["outs"])) {
        print " selected";
    }
    print ">$i</option>\n";
}
print "</select>\n";
print "<p class=\"littlespace\">Runners on base: <select name=\"runners\">\n";
if (!isset($_POST["expectancy"])) {
    $toSelect = 1;
} else {
    $toSelect = $_POST["runners"];
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
    if ((!isset($_POST["expectancy"]) && $i == 0) ||
        (isset($_POST["expectancy"]) && $i == $_POST["scorediff"])) {
        print " selected";
    }
    print ">$i</option>\n";
}
print "</select>\n";
print "<p class=\"littlespace\"><input type=\"submit\" value=\"Get expectancy\" name=\"expectancy\"></p>\n";
print "</form>\n";
if (isset($_POST["expectancy"])) {
    $lineToLookFor = "\"" . $_POST["team"] . "\"," . $_POST["inning"] . "," . $_POST["outs"] . "," . $_POST["runners"] . "," . $_POST["scorediff"] . ",";
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
print "<p>To make a graph of the Win Expectancy of a baseball game, use the <a href=\"graphgame.html\">graph a game</a> tool.</p>\n";
print "<p>This data is from MLB games from 1960-1992 and 2000-2004. It now includes all regular-season event files available at <a href=\"http://www.retrosheet.org/game.htm\">Retrosheet</a>.</p>\n";
print "<p>Idea taken from <a href=\"http://walkoffbalk.com/tools/winexp/index.php\">Win Expectancy Finder</a> at <a href=\"http://walkoffbalk.com\">walkoffbalk.com</a>.</p>\n";
print "<ul><li><a href=\"stats.txt\">stats.php</a> - the source for .php file\n";
print "<li><a href=\"parseretrosheet.txt\">parseretrosheet.py</a> - parses the <a href=\"http://www.retrosheet.org/game.htm\">Retrosheet data</a>\n";
print "<li><a href=\"processstats.txt\">processstats.py</a> - puts the Retrosheet data in the <a href=\"probs.txt\">probs.txt</a> file.  See <a href=\"http://www.philbirnbaum.com/probs2.txt\">Phil Birnbaum's description of the data file</a>.</ul>\n";
print "<p>The information used here was obtained free of charge from and is copyrighted by Retrosheet.  Interested parties may contact Retrosheet at 20 Sunset Rd., Newark, DE 19711.</p>\n";
print "</body></html>\n";

?>
