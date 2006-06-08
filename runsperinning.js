//<![CDATA[

var runsXML = null;
// Taken from http://www.wrox.com/WileyCDA/Section/id-291861.html
if (!Element.selectNodes) {
    Element.prototype.selectNodes = function (sXPath) {
        var oEvaluator = new XPathEvaluator();
        var oResult = oEvaluator.evaluate(sXPath, this, null, 
        XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);    
        
        var aNodes = new Array;
        
        if (oResult != null) {
            var oElement = oResult.iterateNext();
            while(oElement) {
                aNodes.push(oElement);
                oElement = oResult.iterateNext();
            }
        }
        return aNodes;
    };
}

function getDOMText(nodes) {
    var toReturn = "";
    for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].nodeType == Node.TEXT_NODE) {
            toReturn = toReturn + nodes[i].nodeValue;
        }
    }
    return toReturn;
}

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
    // Calling clearAllStartingNode(elem, elem.childNodes[starting]) doesn''t
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

function processResponse(originalRequest) {
    var outs = $F('outs');
    var runners = $F('runners');
    if (runsXML == null) {
        runsXML = originalRequest.responseXML.documentElement;
    }
    var docElem = runsXML;
    var elems = docElem.selectNodes('situation[@outs="' + outs + '" and @runners="' + runners + '"]');
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
        var total = parseInt(getDOMText(element.selectNodes('total')[0].childNodes));
        var totalRow = document.createElement('tr');
        var totalHeader = document.createElement('th');
        totalHeader.appendChild(document.createTextNode('Total'));
        totalRow.appendChild(totalHeader);
        var totalTd = document.createElement('td');
        totalTd.appendChild(document.createTextNode(total));
        totalRow.appendChild(totalTd);
        var totalTd = document.createElement('td');
        totalTd.appendChild(document.createTextNode('100.00000'));
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
            curTd.appendChild(document.createTextNode(curProb.toFixed(5)));
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
