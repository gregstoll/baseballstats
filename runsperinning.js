//<![CDATA[

var runsXML = null;
var isIE = null;

function processResponse(originalRequest) {
    var outs = $F('outs');
    var runners = $F('runners');
    if (runsXML == null) {
        runsXML = originalRequest.responseXML.documentElement;
    }
    var docElem = runsXML;
    var xpath = getXPathFromXML(docElem);
    var xpathExpr = '//situation[@outs="' + outs + '" and @runners="' + runners + '"]';
    var elems = xpath.selectNodes(xpathExpr);
    if (elems.length > 0) {
        clearAll($('outTbody'));
        var headerRow = document.createElement('tr');
        var headerTh = document.createElement('th');
        headerRow.appendChild(headerTh);
        headerTh = document.createElement('th');
        headerTh.appendChild(document.createTextNode('Number'));
        headerRow.appendChild(headerTh);
        headerTh = document.createElement('th');
        headerTh.appendChild(document.createTextNode('Probability'));
        headerRow.appendChild(headerTh);
        $('outTbody').appendChild(headerRow);
        
        var element = elems[0];
        var elementXPath = getXPathFromXML(element);
        // FFV - I can''t get these two to play together.
        // 'total' doesn''t return anything for IE, while
        // '/situation/total' doesn''t for mozilla, and
        // '//total' (bizarrely) returns the first total
        // in the xml document, which is scary.
        xpathExpr = getNestedXPathExpression('situation', 'total');
        var total = parseInt(getDOMText(elementXPath.selectNodes(xpathExpr)[0].childNodes));

        var totalRow = document.createElement('tr');
        var totalHeader = document.createElement('th');
        totalHeader.appendChild(document.createTextNode('Total'));
        totalRow.appendChild(totalHeader);
        var totalTd = document.createElement('td');
        totalTd.appendChild(document.createTextNode(total));
        totalRow.appendChild(totalTd);
        var totalTd = document.createElement('td');
        totalTd.appendChild(document.createTextNode('100.00000%'));
        totalRow.appendChild(totalTd);
        $('outTbody').appendChild(totalRow);
        var runArray = new Array();
        var runElems = element.selectNodes('count');
        var expectedTotal = 0.0;
        for (var i = 0; i < runElems.length; i++) {
            var curRunElem = runElems[i];
            var curNum = parseInt(getDOMText(curRunElem.childNodes));
            expectedTotal += (curNum * i);
            var curProb = (curNum/total) * 100.0; 
            var curRow = document.createElement('tr');
            var curHeader = document.createElement('th');
            curHeader.appendChild(document.createTextNode(i + ' runs'));
            curRow.appendChild(curHeader);
            var curTd = document.createElement('td');
            curTd.appendChild(document.createTextNode(curNum));
            curRow.appendChild(curTd);
            var curTd = document.createElement('td');
            curTd.appendChild(document.createTextNode(curProb.toFixed(5) + '%'));
            curRow.appendChild(curTd);
            $('outTbody').appendChild(curRow);
        }
        var expected = (expectedTotal/total);
        clearAll($('outExpected'));
        $('outExpected').appendChild(document.createTextNode(expected.toFixed(5)));
    }
}

function updateProbabilities() {
    if (runsXML == null) {
        doRequest('runsperinning.xml', true, processResponse, 'GET', null);
    } else {
        processResponse(null);
    }
}

function doRequest(url, async, callback, method, postData) {
    var xmlhttp = new Ajax.Request(
        url,
        {
            method: method,
            parameters: '',
            onComplete: callback 
        });
}

updateProbabilities();

//]]>
