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

function clearAll(elem) {
    clearAllStarting(elem, 0);
}

function clearAllButFirstElement(elem) {
    clearAllStarting(elem, 1);
}

function clearAllAfterFirstElementType(elem, elemType) {
    if (!elem || elem.childNodes.length == 0) {
        return;
    }
    var curChild = elem.childNodes[0];
    while (curChild != null && curChild.nodeName.toUpperCase() != elemType.toUpperCase()) {
        curChild = curChild.nextSibling;
    }
    if (curChild != null) {
        clearAllStartingNode(elem, curChild.nextSibling);
    }
}

function clearAllStarting(elem, starting) {
    if (!elem || (elem.childNodes.length < starting)) {
        return;
    }
    // Calling clearAllStartingNode(elem, elem.childNodes[starting]) doesn't
    // work - the startingNode gets set to void for some reason.
    var curChild = elem.childNodes[starting];
    var nextChild = null;
    while (curChild != null) {
        nextChild = curChild.nextSibling;
        elem.removeChild(curChild);
        curChild = nextChild;
    }
}

function clearAllStartingNode(elem, startingNode) {
    var curChild = startingNode;
    var nextChild = null;
    while (curChild != null) {
        nextChild = curChild.nextSibling;
        elem.removeChild(curChild);
        curChild = nextChild;
    }
}

function getDisplayStyle(isVisible) {
    if (!isVisible) {
        return "none";
    } else {
        return "";
    }
}

function createRow(idNumber) {
    var row = document.createElement("tr");
    row.id = "row" + idNumber;
    var inningTd = document.createElement("td");
    var inningInput = document.createElement("select");
    inningInput.id = "inning" + idNumber;
    for (var i = 1; i <= 15; i++) {
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
    outsInput.id = "outs" + idNumber;
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
    runnerInput.id = "runner" + idNumber;
    for (var i = 1; i <= 8; i++) {
        var runnerOption = document.createElement("option");
        runnerOption.value = i;
        runnerOption.appendChild(document.createTextNode(runnerNames[i]));
        runnerInput.appendChild(runnerOption);
    }
    runnerTd.appendChild(runnerInput);
    row.appendChild(runnerTd);
    return row;
}

function addEntries(numEntries) {
    var situationTBody = document.getElementById('situationTBody');
    clearAllAfterFirstElementType(situationTBody, "tr");
    for (var i = 0; i < numEntries; i++) {
        situationTBody.appendChild(createRow(i));
    }
}

setTimeout('addEntries(10)', 0);
//]]>
