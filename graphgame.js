//<![CDATA[

var runnerNames = new Array();
runnerNames[1] = "none";
runnerNames[2] = "1st";
runnerNames[3] = "2nd";
runnerNames[4] = "1st & 2nd";
runnerNames[5] = "3rd";
runnerNames[6] = "1st & 3rd";
runnerNames[7] = "2nd & 3rd";
runnerNames[8] = "loaded";
var numEntries = 0;
var numScores = 8;

function updateInnings(idNumber, value) {
    var curScore = document.getElementById("score" + idNumber).selectedIndex;
    var newScore = 2 * numScores - curScore;
    document.getElementById("score" + idNumber).selectedIndex = newScore;
    for (var i = idNumber + 1; i < numEntries; i++) {
        var inningInput = document.getElementById("inning" + i);
        inningInput.selectedIndex = value;
        var outsInput = document.getElementById("outs" + i);
        outsInput.selectedIndex = 0;
        var runnerInput = document.getElementById("runner" + i);
        runnerInput.selectedIndex = 0;
        var scoreInput = document.getElementById("score" + i);
        scoreInput.selectedIndex = newScore;
    }
    // Change the current number of outs and runners as well.
    var outsInput = document.getElementById("outs" + idNumber);
    outsInput.selectedIndex = 0;
    var runnerInput = document.getElementById("runner" + idNumber);
    runnerInput.selectedIndex = 0;
    return false;
}

function updateOuts(idNumber, value) {
    for (var i = idNumber + 1; i < numEntries; i++) {
        var outsInput = document.getElementById("outs" + i);
        outsInput.selectedIndex = value;
    }
    return false;
}

function updateScore(idNumber, value) {
    for (var i = idNumber + 1; i < numEntries; i++) {
        var scoreInput = document.getElementById("score" + i);
        scoreInput.selectedIndex = value;
    }
    return false;
}

function updateRunners(idNumber, value) {
    for (var i = idNumber + 1; i < numEntries; i++) {
        var runnerInput = document.getElementById("runner" + i);
        runnerInput.selectedIndex = value;
    }
    return false;
}

function startOver() {
    for (var i = 0; i < numEntries; i++) {
        var inningInput = document.getElementById("inning" + i);
        inningInput.selectedIndex = 0;
        var outsInput = document.getElementById("outs" + i);
        outsInput.selectedIndex = 0;
        var runnerInput = document.getElementById("runner" + i);
        runnerInput.selectedIndex = 0;
        var scoreInput = document.getElementById("score" + i);
        scoreInput.selectedIndex = numScores;
    }
}

function setTitle(doTop, newValue) {
    var input;
    if (doTop) {
        input = document.getElementById("formtoptitle");
    } else {
        input = document.getElementById("formbottomtitle");
    }
    input.value = newValue;
    return false;
}

function setDoKey(doTop, newValue) {
    var input;
    if (doTop) {
        input = document.getElementById("formtopdoKey");
    } else {
        input = document.getElementById("formbottomdoKey");
    }
    input.checked = newValue;
    return false;
}

function setDoRunsScored(doTop, newValue) {
    var input;
    if (doTop) {
        input = document.getElementById("formtopdoRunsScored");
    } else {
        input = document.getElementById("formbottomdoRunsScored");
    }
    input.checked = newValue;
    // If we're not showing where runs are scored, it doesn't make sense
    // to show the key.
    if (newValue == false) {
        setDoKey(false, false);
        setDoKey(true, false);
    }
    return false;
}


function createRow(idNumber) {
    var row = document.createElement("tr");
    row.id = "row" + idNumber;
    var inningTd = document.createElement("td");
    var inningInput = document.createElement("select");
    inningInput.id = "inning" + idNumber;
    inningInput.name = "inning" + idNumber;
    inningInput.onchange = function() {
        return updateInnings(idNumber, this.selectedIndex);
    }
    for (var i = 1; i <= 18; i++) {
        var visitorInning = document.createElement("option");
        visitorInning.value = "V" + i;
        visitorInning.appendChild(document.createTextNode("Visitor " + i));
        inningInput.appendChild(visitorInning);
        var homeInning = document.createElement("option");
        homeInning.value = "H" + i;
        homeInning.appendChild(document.createTextNode("Home " + i));
        inningInput.appendChild(homeInning);
    }
    inningTd.appendChild(inningInput);
    row.appendChild(inningTd);
    var outsTd = document.createElement("td");
    var outsInput = document.createElement("select");
    outsInput.onchange = function() {
        return updateOuts(idNumber, this.selectedIndex);
    }
    outsInput.id = "outs" + idNumber;
    outsInput.name = "outs" + idNumber;
    for (var i = 0; i < 3; i++) {
        var outsOption = document.createElement("option");
        outsOption.value = i;
        outsOption.appendChild(document.createTextNode(i));
        outsInput.appendChild(outsOption);
    }
    outsTd.appendChild(outsInput);
    row.appendChild(outsTd);
    var runnerTd = document.createElement("td");
    var runnerInput = document.createElement("select");
    runnerInput.onchange = function() {
        return updateRunners(idNumber, this.selectedIndex);
    }
    runnerInput.id = "runner" + idNumber;
    runnerInput.name = "runner" + idNumber;
    for (var i = 1; i <= 8; i++) {
        var runnerOption = document.createElement("option");
        runnerOption.value = i;
        runnerOption.appendChild(document.createTextNode(runnerNames[i]));
        runnerInput.appendChild(runnerOption);
    }
    runnerTd.appendChild(runnerInput);
    row.appendChild(runnerTd);
    var scoreTd = document.createElement("td");
    var scoreInput = document.createElement("select");
    scoreInput.onchange = function() {
        return updateScore(idNumber, this.selectedIndex);
    }
    scoreInput.id = "score" + idNumber;
    scoreInput.name = "score" + idNumber;
    for (var i = -numScores; i <= numScores; i++) {
        var scoreOption = document.createElement("option");
        scoreOption.value = i;
        if (i == 0) {
            scoreOption.selected = true;
        }
        scoreOption.appendChild(document.createTextNode(i));
        scoreInput.appendChild(scoreOption);
    }
    scoreTd.appendChild(scoreInput);
    row.appendChild(scoreTd);
    var lastTd = document.createElement("td");
    var lastInput = document.createElement("input");
    lastInput.setAttribute("type", "submit");
    lastInput.value = "Last situation";
    lastInput.name = "situation" + idNumber;
    lastTd.appendChild(lastInput);
    row.appendChild(lastTd);
    return row;
}

function addEntries(entries, reset) {
    var situationTBody = document.getElementById('situationTBody');
    var startingI = 0;
    if (reset) {
        numEntries = entries;
        clearAllAfterFirstElementType(situationTBody, "tr");
    } else {
        startingI = numEntries;
        numEntries = numEntries + entries;
    }
    for (var i = startingI; i < numEntries; i++) {
        situationTBody.appendChild(createRow(i));
    }
}

setTimeout('addEntries(100, true)', 0);
//]]>
