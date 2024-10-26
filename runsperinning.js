//<![CDATA[

let runsXML = null;
function updateProbabilities() {
    if (!runsXML) {
        // wait for updateRunsXML() to finish, then this will be called again
        return;
    }
    let outs = document.getElementById('outs').value;
    let runners = document.getElementById('runners').value;
    let xpathExpr = `//situation[@outs="${outs}" and @runners="${runners}"]`;
    let result = runsXML.evaluate(xpathExpr, runsXML, null, XPathResult.ANY_TYPE, null);
    let situationNode = result.iterateNext();
    if (situationNode) {
        let outTBody = document.getElementById('outTbody');
        outTBody.innerHTML = '';
        let headerRow = document.createElement('tr');
        let headerTh = document.createElement('th');
        headerRow.appendChild(headerTh);
        headerTh = document.createElement('th');
        headerTh.appendChild(document.createTextNode('Number'));
        headerRow.appendChild(headerTh);
        headerTh = document.createElement('th');
        headerTh.appendChild(document.createTextNode('Probability'));
        headerRow.appendChild(headerTh);
        outTbody.appendChild(headerRow);
        
        // FFV - I can't get these two to play together.
        // 'total' doesn't return anything for IE, while
        // '/situation/total' doesn't for mozilla, and
        // '//total' (bizarrely) returns the first total
        // in the xml document, which is scary.
        let totalNode = runsXML.evaluate('total', situationNode, null, XPathResult.ANY_TYPE, null).iterateNext();
        let total = parseInt(totalNode.innerHTML, 10);

        let totalRow = document.createElement('tr');
        let totalHeader = document.createElement('th');
        totalHeader.appendChild(document.createTextNode('Total'));
        totalRow.appendChild(totalHeader);
        let totalTd = document.createElement('td');
        totalTd.appendChild(document.createTextNode(total));
        totalRow.appendChild(totalTd);
        totalTd = document.createElement('td');
        totalTd.appendChild(document.createTextNode('100.00000%'));
        totalRow.appendChild(totalTd);
        outTbody.appendChild(totalRow);
        let runArray = [];
        let runElems = runsXML.evaluate('count', situationNode, null, XPathResult.ANY_TYPE, null);
        let expectedTotal = 0.0;
        let i = 0;
        let curRunElem = null;
        while (curRunElem = runElems.iterateNext()) {
            let curNum = parseInt(curRunElem.innerHTML, 10);
            expectedTotal += (curNum * i);
            let curProb = (curNum/total) * 100.0; 
            let curRow = document.createElement('tr');
            let curHeader = document.createElement('th');
            curHeader.appendChild(document.createTextNode(i + ' runs'));
            curRow.appendChild(curHeader);
            let curTd = document.createElement('td');
            curTd.appendChild(document.createTextNode(curNum));
            curRow.appendChild(curTd);
            curTd = document.createElement('td');
            curTd.appendChild(document.createTextNode(curProb.toFixed(5) + '%'));
            curRow.appendChild(curTd);
            outTbody.appendChild(curRow);
            i++;
        }
        let expected = (expectedTotal/total);
        let outExpected = document.getElementById('outExpected');
        outExpected.innerHTML = '';
        outExpected.appendChild(document.createTextNode(expected.toFixed(5)));
    }
}

async function updateRunsXML() {
    const response = await fetch("runsperinning.xml");
    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }
    const text = await response.text();
    const parser = new DOMParser();
    runsXML = parser.parseFromString(text, "application/xml");
    updateProbabilities();
}
updateRunsXML();


//]]>
