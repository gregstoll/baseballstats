import './App.css'

import React, {Component} from 'react'
import ReactSlider from 'react-slider'
import wgxpath from 'wicked-good-xpath';
import AnimateOnChange from 'react-animate-on-change';

// Needed to initialize document.evaluate() from wicked-good-xpath
wgxpath.install();

const MIN_YEAR = 1957;
const MAX_YEAR = 2018;
const SHOW_BALLS_STRIKES = true;
//TODO?
const extraYears = [];
function transformNonZeroYear(y)
{
    if (y < 0) {
        return MAX_YEAR + y;
    }
    if (y < 1900) {
        return MIN_YEAR + y;
    }
    return y;
}
function transformYears(startYear, endYear)
{
    if (startYear === 0) {
        startYear = MIN_YEAR;
    }
    if (endYear === 0) {
        endYear = MAX_YEAR;
    }
    startYear = transformNonZeroYear(startYear);
    endYear = transformNonZeroYear(endYear);
    return [startYear, endYear];
}

class RunsPerInningResult {
    constructor(totalSituations, countByRuns) {
        this.totalSituations = totalSituations;
        this.countByRuns = countByRuns;
    }
    isEqual(other) {
        if (other === undefined) {
            return false;
        }
        if (this.totalSituations !== other.totalSituations) {
            return false;
        }
        if (this.countByRuns.length !== other.countByRuns.length) {
            return false;
        }
        for (let i = 0; i < this.countByRuns.length; ++i) {
            if (this.countByRuns[i] !== other.countByRuns[i]) {
                return false;
            }
        }
        return true;
    }
    getProbabilityForExactNumberOfRuns(numberOfRuns) {
        return this.countByRuns[numberOfRuns] / this.totalSituations;
    }
    getProbabilityForAtLeastNumberOfRuns(numberOfRuns) {
        let numSituationsBelowNumberOfRuns = 0;
        for (let i = 0; i < numberOfRuns; ++i) {
            numSituationsBelowNumberOfRuns += this.countByRuns[i];
        }
        return 1.0 - (numSituationsBelowNumberOfRuns / this.totalSituations);
    }
    getExpectedRuns() {
        let expected = 0.0;
        // skip the first iteration
        for (let i = 1; i < this.countByRuns.length; ++i) {
            expected += i * (this.countByRuns[i] / this.totalSituations);
        }
        return expected;
    }
}

class InningHeader extends Component {
    render() {
        return <th>{this.props.inningNum}</th>;
    }
}
class InningChoice extends Component {
    handleClick(e) {
        this.props.setInning(this.props.inning);
    }
    render() {
        return <td><input type="radio" name="inningRadio" value="{this.props.inning.homeOrVisitor + this.props.inning.num}" defaultChecked={this.props.inning.homeOrVisitor === this.props.chosenInning.homeOrVisitor && this.props.inning.num === this.props.chosenInning.num} onClick={e => this.handleClick(e)} /></td>;
    }
}
class InningTable extends Component {
    setInning(inning) {
        this.props.setInning(inning);
    }
    render() {
        let headers = [];
        for (let i = 1; i <= this.props.numInnings; ++i)
        {
            headers.push(<InningHeader key={i} inningNum={i} />);
        }
        let visitorChoices = [];
        for (let i = 1; i <= this.props.numInnings; ++i)
        {
            let thisInning = {homeOrVisitor: 'V', num: i};
            visitorChoices.push(<InningChoice key={thisInning.homeOrVisitor + thisInning.num} inning={thisInning} chosenInning={this.props.inning} setInning={i => this.setInning(i)} />);
        }
        let homeChoices = [];
        for (let i = 1; i <= this.props.numInnings; ++i)
        {
            let thisInning = {homeOrVisitor: 'H', num: i};
            homeChoices.push(<InningChoice key={thisInning.homeOrVisitor + thisInning.num} inning={thisInning} chosenInning={this.props.inning} setInning={i => this.setInning(i)} />);
        }
        return <table className="innings">
            <thead>
                <tr>
                    <th></th>
                    {headers}
                </tr>
            </thead>
            <tbody>
                <tr>
                    <th className="sideHeader">V</th>
                    {visitorChoices}
                </tr>
                <tr>
                    <th className="sideHeader">H</th>
                    {homeChoices}
                </tr>
            </tbody>
        </table>;
    }
}
class OutsControl extends Component {
    handleClick(e) {
        this.props.setOuts((this.props.outs === 2) ? 0 : this.props.outs + 1);
    }
    getOutsColor(on) {
        return on ? '#ff0000' : '#ffffff';
    }
    render() {
        const WIDTH = 75;
        const HEIGHT = 40;
        const WIDTH_MARGIN = 5;
        const HEIGHT_MARGIN = 5;

        const circleRadius = Math.min(WIDTH - 3 * WIDTH_MARGIN, HEIGHT - 2 * HEIGHT_MARGIN) / 2;
        return <p className="littlespace" style={{"display": "flex", "alignItems": "center"}}><span>Outs:</span>
        <svg width={WIDTH} height={HEIGHT} onClick={e => this.handleClick(e)}>
            <circle cx={WIDTH/4} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getOutsColor(this.props.outs >= 1)} />
            <circle cx={(3*WIDTH)/4} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getOutsColor(this.props.outs >= 2)} />
        </svg>
        </p>;
    }
}
class BallsStrikesControl extends Component {
    handleBallsClick(e) {
        this.props.setBalls((this.props.balls === 3) ? 0 : (1 + this.props.balls));
    }
    handleStrikesClick(e) {
        this.props.setStrikes((this.props.strikes === 2) ? 0 : (1 + this.props.strikes));
    }
    getBallsColor(on) {
        return on ? '#ff0000' : '#ffffff';
    }
    getStrikesColor(on) {
        return on ? '#ff0000' : '#ffffff';
    }
    render() {
        const STRIKES_WIDTH = 75;
        const BALLS_WIDTH = STRIKES_WIDTH + 40;
        const HEIGHT = 40;
        const WIDTH_MARGIN = 5;
        const HEIGHT_MARGIN = 5;

        const circleRadius = Math.min(STRIKES_WIDTH - 3 * WIDTH_MARGIN, HEIGHT - 2 * HEIGHT_MARGIN) / 2;
        return <table>
            <tr className="littlespace">
                <td style={{"textAlign": "right", "verticalAlign": "middle"}}>Balls:</td>
                <svg width={BALLS_WIDTH} height={HEIGHT} onClick={e => this.handleBallsClick(e)} style={{"verticalAlign": "middle"}}>
                    <circle cx={BALLS_WIDTH/6} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getBallsColor(this.props.balls >= 1)} />
                    <circle cx={(3*BALLS_WIDTH)/6} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getBallsColor(this.props.balls >= 2)} />
                    <circle cx={(5*BALLS_WIDTH)/6} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getBallsColor(this.props.balls >= 3)} />
                </svg>
            </tr>
            <tr className="littlespace">
                <td style={{"textAlign": "right", "verticalAlign": "middle"}}>Strikes:</td>
                <svg width={STRIKES_WIDTH} height={HEIGHT} onClick={e => this.handleStrikesClick(e)} style={{"verticalAlign": "middle"}}>
                <circle cx={STRIKES_WIDTH/4} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getStrikesColor(this.props.strikes >= 1)} />
                <circle cx={(3*STRIKES_WIDTH)/4} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getStrikesColor(this.props.strikes >= 2)} />
            </svg>
            </tr>
        </table>;
    }
}
class RunnersOnBaseList extends Component {
    handleChange(e) {
        this.props.setRunners(e.target.value);
    }
    render() {
        return <p className="littlespace">Runners on base:&nbsp;
        <select onChange={e => this.handleChange(e)} value={this.props.runners}>
            <option value="1">none</option>
            <option value="2">1st</option>
            <option value="3">2nd</option>
            <option value="4">1st &amp; 2nd</option>
            <option value="5">3rd</option>
            <option value="6">1st &amp; 3rd</option>
            <option value="7">2nd &amp; 3rd</option>
            <option value="8">loaded</option>
        </select>
        </p>;
    }
}
class ScoreTable extends Component {
    handleVisitorClick() {
        this.props.setScore(this.props.score - 1);
    }
    handleHomeClick() {
        this.props.setScore(this.props.score + 1);
    }
    render() {
        let visitorScore = '';
        let homeScore = '';
        if (this.props.score < 0) {
            visitorScore = '+' + (-1 * this.props.score);
        } else if (this.props.score > 0) {
            homeScore = '+' + (this.props.score);
        } else {
            visitorScore = "Tie";
            homeScore = "Tie";
        }
        return <table className="scoreTable"><tbody>
            <tr><th>Visitor</th><td>{visitorScore}</td><td><button onClick={e => this.handleVisitorClick()}>+</button></td></tr>
            <tr><th>Home</th><td>{homeScore}</td><td><button onClick={e => this.handleHomeClick()}>+</button></td></tr>
        </tbody></table>;
    }
}
class RunnersOnBaseDiamond extends Component {
    getBaseColor(on) {
        return on ? '#ff0000' : '#eeeeee';
    }
    pointsFromCenter(center, baseSize) {
        return [[center[0], center[1] + baseSize], [center[0] + baseSize, center[1]], [center[0], center[1] - baseSize], [center[0] - baseSize, center[1]]];
    }
    toggleFirst(e) {
        this.props.setRunners(((this.props.runners - 1) ^ 1) + 1);
    }
    toggleSecond(e) {
        this.props.setRunners(((this.props.runners - 1) ^ 2) + 1);
    }
    toggleThird(e) {
        this.props.setRunners(((this.props.runners - 1) ^ 4) + 1);
    }
    render() {
        const WIDTH = 200;
        const HEIGHT = 200;

        const first = (this.props.runners - 1) & 1;
        const second = (this.props.runners - 1) & 2;
        const third = (this.props.runners - 1) & 4;
        const baseSize = Math.max(WIDTH*0.1, 10);

        const homeCenter = [WIDTH/2, HEIGHT*0.85];
        const homePoints = [[homeCenter[0], homeCenter[1] + baseSize], [homeCenter[0] + baseSize, homeCenter[1]], [homeCenter[0] + baseSize], [homeCenter[1] - baseSize], [homeCenter[0] - baseSize, homeCenter[1] - baseSize], [homeCenter[0] - baseSize, homeCenter[1]]];

        const firstCenter = [WIDTH*0.85, HEIGHT/2];
        const firstPoints = this.pointsFromCenter(firstCenter, baseSize);

        const secondCenter = [WIDTH/2, HEIGHT*0.15];
        const secondPoints = this.pointsFromCenter(secondCenter, baseSize);

        const thirdCenter = [WIDTH*0.15, HEIGHT/2];
        const thirdPoints = this.pointsFromCenter(thirdCenter, baseSize);
        
        return <div>
         <svg width={WIDTH} height={HEIGHT}>
            <rect x="0" y="0" width={WIDTH} height={HEIGHT} fill="#006400" />
            <line x1={WIDTH/2} y1={HEIGHT*0.85} x2={WIDTH*0.85} y2={HEIGHT/2} strokeWidth="5" stroke="#a0522d" />
            <line x1={WIDTH*0.85} y1={HEIGHT/2} x2={WIDTH/2} y2={HEIGHT*0.15} strokeWidth="5" stroke="#a0522d" />
            <line x1={WIDTH/2} y1={HEIGHT*0.15} x2={WIDTH*0.15} y2={HEIGHT/2} strokeWidth="5" stroke="#a0522d" />
            <line x1={WIDTH*0.15} y1={HEIGHT/2} x2={WIDTH/2} y2={HEIGHT*0.85} strokeWidth="5" stroke="#a0522d" />
            { /* home plate */ }
            <polygon points={homePoints} strokeWidth="0" fill={this.getBaseColor(false)} />
            { /* first base */ }
            <polygon points={firstPoints} strokeWidth="0" fill={this.getBaseColor(first)} onClick={e => this.toggleFirst(e)} />
            { /* second base */ }
            <polygon points={secondPoints} strokeWidth="0" fill={this.getBaseColor(second)} onClick={e => this.toggleSecond(e)}/>
            { /* third base */ }
            <polygon points={thirdPoints} strokeWidth="0" fill={this.getBaseColor(third)} onClick={e => this.toggleThird(e)}/>
        </svg>
        </div>;
    }
}
class YearsSlider extends Component {
    onChange(value) {
        if (this.setYearsEvent !== undefined) {
            window.clearTimeout(this.setYearsEvent);
        }
        // update view here
        // We don't want to wait for the AJAX request to be sent
        // (which will take at least this.TIMEOUT ms) to update the text
        // here, so store it in our state instead of props.
        this.setState({years: [value[0], value[1]]});
        this.setYearsEvent = window.setTimeout(function() { this.doActualChange(value)}.bind(this), this.TIMEOUT);
    }
    doActualChange(value) {
        this.setYearsEvent = undefined;
        this.props.setYears([value[0], value[1]]);
    }
    componentDidMount() {
        // delay before triggering setYears
        this.TIMEOUT = 500;
        this.setYearsEvent = undefined;
    }
    componentWillMount() {
        this.setState({years: this.props.years});
    }
    componentWillReceiveProps(nextProps) {
        this.setState({years: nextProps.years});
    }
    render() {
        return <div>
            <p className="littlespace">Years to include: {this.state.years[0]} - {this.state.years[1]}</p>
            <ReactSlider className="horizontal-slider" orientation="horizontal" withBars={true} defaultValue={[this.state.years[0], this.state.years[1]]} min={MIN_YEAR} max={MAX_YEAR} onChange={val => this.onChange(val)} />
        </div>
    }
}

class RunsPerInningResultComponent extends Component {
    constructor(props) {
        super(props);
        this.state = {'flash': false};
    }
    componentDidUpdate(prevProps, prevState) {
        let differences = false;
        if (prevProps === undefined || prevProps.result === undefined) {
            differences = !(this.props === undefined || this.props.result === undefined);
        }
        else {
            differences = !this.props.result.isEqual(prevProps.result);
        }
        if (differences) {
            this.setState({"flash": true});
        }
    }
    makeDisplayPercent(probability) {
        return ((Math.round(probability * 10000) / 100).toFixed(2) + "%");
    }
    makeDisplayRuns(runs) {
        return runs.toFixed(2);
    }
    render() {
        if (this.props.result === undefined) {
            return <div/>;
        }
        return <AnimateOnChange
                    baseClassName="pulsar"
                    animationClassName="pulsarFlash"
                    animate={this.state.flash}
                    customTag="div">
            <div>
                <p className="littlespace">Expected runs: {this.makeDisplayRuns(this.props.result.getExpectedRuns())}</p>
                <table className="runsPerInning"><tbody>
                <tr><th>0 runs:</th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForExactNumberOfRuns(0))}</td></tr>
                <tr><th>1 run:</th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForExactNumberOfRuns(1))}</td><th>1+ runs: </th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForAtLeastNumberOfRuns(1))}</td></tr>
                <tr><th>2 runs:</th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForExactNumberOfRuns(2))}</td><th>2+ runs: </th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForAtLeastNumberOfRuns(2))}</td></tr>
                <tr><th>3 runs:</th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForExactNumberOfRuns(3))}</td><th>3+ runs: </th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForAtLeastNumberOfRuns(3))}</td></tr>
                <tr><th>4 runs:</th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForExactNumberOfRuns(4))}</td><th>4+ runs: </th><td>{this.makeDisplayPercent(this.props.result.getProbabilityForAtLeastNumberOfRuns(4))}</td></tr>
                </tbody></table></div>
        </AnimateOnChange>;
    }
}
class StatsResults extends Component {
    constructor(props) {
        super(props);
        this.state = {'flash': false};
    }
    componentDidMount() {
        this.setState({"flash": true});
    }
    componentDidUpdate(prevProps, prevState) {
        let differences = false;
        let properties = Object.keys(this.props);
        for (var i in properties) {
            if (properties[i] !== 'years' && this.props[properties[i]] !== prevProps[properties[i]]) {
                differences = true;
                break;
            }
        }
        if (differences) {
            this.setState({"flash": true});
        }
    }
    render() {
        let mainDivStyle = {width: '300px'};
        if (!this.props.isPrimary) {
            mainDivStyle.marginTop = '20px';
            mainDivStyle.cssFloat = 'left';
        }
        if (this.props.isInitial) {
            return <div style={mainDivStyle}/>
        }
        let key = this.props.name;// + Math.random();
        if (this.props.total === 0) {
            key = key + 'none';
            return <AnimateOnChange
                    baseClassName="pulsar"
                    animationClassName="pulsarFlash"
                    animate={this.state.flash}
                    customTag="div">
                <div style={mainDivStyle}>
                    <div className="realOutput" key={key}>No data found!</div>
                </div>
            </AnimateOnChange>;
        }
        const r = this.props;
        let wins = r.wins;
        const percent = (100 * wins) / r.total;
        let displayPercent = Math.round(percent * 100)/100;
        let displayHome = r.isHome; 
        let homeMoneyLine = '';
        let visitorMoneyLine = '';
        if (displayPercent < 50)
        {
            displayPercent = Math.round((100 - displayPercent) * 100)/100;
            wins = r.total - wins;
            displayHome = !displayHome;
        }
        let ml = Math.round((displayPercent/(100 - displayPercent)) * -100);
        let oml = "+" + (-1 * ml);
        if (displayHome) {
            homeMoneyLine = ml;
            visitorMoneyLine = oml;
        } else {
            homeMoneyLine = oml;
            visitorMoneyLine = ml;
        }
        // TODO - refactor leverage stuff
        let leverageDescription = 'Low';
        let leverageClass = 'leverageLow';
        if (r.leverageIndex >= 3.0) {
            leverageDescription = 'Very High';
            leverageClass = 'leverageVeryHigh';
        } else if (r.leverageIndex >= 1.6) {
            leverageDescription = 'High';
            leverageClass = 'leverageHigh';
        } else if (r.leverageIndex >= 0.8) {
            leverageDescription = 'Medium';
            leverageClass = 'leverageMedium';
        }
        leverageClass = 'leverageIndex ' + leverageClass;
        const winnerTeamText = displayHome ? "Home" : "Visitor";
        // make this something that always changes
        const yearsStyle = r.isPrimary ? {display : 'none'} : {};
        return <AnimateOnChange
                    baseClassName="pulsar"
                    animationClassName="pulsarFlash"
                    animate={this.state.flash}
                    customTag="div">
            <div className="realOutput" key={key}>
                <p className="littlespace" style={yearsStyle}>Years: {r.years[0]} - {r.years[1]}</p>
                <p className="littlespace">Total games: {r.total}</p>
                <p className="littlespace">Wins for {winnerTeamText}: {wins}</p>
                <p className="littlespace">Win percentage: <b>{winnerTeamText} {displayPercent}%</b></p>
                <p className="littlespace">Leverage index: <b className={leverageClass}>{r.leverageIndex} ({leverageDescription})</b></p>
                <p className="littlespace">Home money line: <b>{homeMoneyLine}</b></p>
                <p className="littlespace">Visitor money line: <b>{visitorMoneyLine}</b></p>
            </div>
        </AnimateOnChange>;
    }
}
class IndeterminateProgressBar extends Component {
    render() {
        return <progress style={{display: this.props.active ? '' : 'none'}} />;
    }
}
class BaseballSituation extends Component {
    addInitialState(state, name, years) {
        state['results' + name] = {total: 0, wins: 0, leverageIndex: 0, isHome: false, isInitial: true, years: years};
    }
    constructor(props) {
        super(props);
        const state = {inning: {homeOrVisitor: 'V', num: 1}, outs: 0, runners: 1, score: 0, years: [MIN_YEAR, MAX_YEAR], balls: 0, strikes: 0, pendingRequests: false, pendingCount: 0};
        this.addInitialState(state, 'output', []);
        for (let i = 0; i < extraYears.length; ++i)
        {
            const localStartYear = extraYears[i][0];
            const localEndYear = extraYears[i][1];
            const transformedYears = transformYears(localStartYear, localEndYear);
            this.addInitialState(state, 'output' + i, transformedYears);
        }
        // parse query hash
        if (window.location.hash) {
            let hash = window.location.hash.substring(1);
            let parts = hash.split(".");
            if (parts.length === 9 || parts.length === 7 || parts.length === 5) {
                let whichTeam = parts[0];
                let scorediff = parseInt(parts[1]);
                let outs = parseInt(parts[3], 10);
                let runners = parseInt(parts[4], 10);
                let balls = 0;
                let strikes = 0;
                if (parts.length >= 7) {
                    balls = parseInt(parts[5], 10);
                    strikes = parseInt(parts[6], 10);
                }
                let startYear = MIN_YEAR;
                let endYear = MAX_YEAR;
                if (parts.length === 9) {
                    startYear = parseInt(parts[7]);
                    endYear = parseInt(parts[8]);
                    if (isNaN(startYear) || isNaN(endYear)) {
                        startYear = MIN_YEAR;
                        endYear = MAX_YEAR;
                    }
                }

                state.inning.homeOrVisitor = whichTeam;
                state.score = scorediff;
                state.inning.num = parseInt(parts[2]);
                state.outs = outs;
                state.runners = runners;
                state.balls = balls;
                state.strikes = strikes;
                state.years[0] = startYear;
                state.years[1] = endYear;
            }
        }
        this.state = state;
    }
    componentDidMount() {
        this.updateCalculations();
    }
    updateCalculations() {
        let s = this.state;
        // update query hash
        let hash = s.inning.homeOrVisitor + "." + s.score + "." + s.inning.num + "." + s.outs + "." + s.runners + "." + s.balls + "." + s.strikes;
        if (s.years[0] !== MIN_YEAR || s.years[1] !== MAX_YEAR) {
            hash += "." + s.years[0] + "." + s.years[1];
        }
        window.location.hash = hash;

        // set up progress bar state
        this.setState({'pendingHash' : hash, 'pendingCount': 1 + extraYears.length});

        this.calculateStats(s.inning.homeOrVisitor, s.score, s.inning.num, s.outs, s.runners, s.balls, s.strikes, s.years[0], s.years[1], 'output', hash);
        for (let i = 0; i < extraYears.length; ++i)
        {
            let localStartYear = extraYears[i][0];
            let localEndYear = extraYears[i][1];
            const transformedYears = transformYears(localStartYear, localEndYear);
            localStartYear = transformedYears[0];
            localEndYear = transformedYears[1];
            this.calculateStats(s.inning.homeOrVisitor, s.score, s.inning.num, s.outs, s.runners, s.balls, s.strikes, localStartYear, localEndYear, 'output' + i, hash);
        }
    }
    calculateStats(whichTeam, scorediff, inning, outs, runners, balls, strikes, startYear, endYear, name, hash) {
        const isHome = whichTeam === "H";
        if (!isHome)
        {
            scorediff *= -1;
        }
        let stateString = `"${whichTeam}",${inning},${outs},${runners},${scorediff}`;
        if (!SHOW_BALLS_STRIKES) {
            balls = 0;
            strikes = 0;
        }
        let ballsStrikesState = `${balls},${strikes}`
        // TODO url
        let url = `https://gregstoll.dyndns.org/~gregstoll/baseball.test/getcumulativestats.cgi?stateString=${encodeURIComponent(stateString)}&ballsStrikesState=${encodeURIComponent(ballsStrikesState)}&startYear=${startYear}&endYear=${endYear}&rand=${Math.random()}`;
        fetch(url).then(response => {
            return response.json();
        }).then(json => {
            let theseResults = this.state['results' + name];
            theseResults.total = parseInt(json.total);
            theseResults.wins = parseInt(json.wins);
            theseResults.leverageIndex = parseFloat(json.leverage);
            theseResults.isHome = isHome;
            theseResults.isInitial = false;
            let newState = {}
            newState['results' + name] = theseResults;
            //this.setState(newState);
            // use the callback for to atomically update pendingCount
            this.setState(function(previousState, currentProps) {
                if (hash === previousState['pendingHash']) {
                    newState['pendingCount'] = previousState['pendingCount'] - 1;
                }
                return newState;
            });
        });
        if (!this.state['runsPerInningData'])
        {
            //TODO url
            let FILENAME = SHOW_BALLS_STRIKES ? "runsperinningballsstrikes.xml" : "runsperinning.xml";
            fetch(`https://gregstoll.dyndns.org/~gregstoll/baseball.test/${FILENAME}`).then(response => {
                return response.text();
            }).then(xmlText => {
                let xml = (new DOMParser()).parseFromString(xmlText, "text/xml");
                this.setState({runsPerInningData: xml});
                this.updateRunsPerInning(xml);
            });
        }
        else
        {
            this.updateRunsPerInning();
        }
    }
    updateRunsPerInning(responseXML) {
        const outs = this.state.outs;
        const runners = this.state.runners;
        const balls = this.state.balls;
        const strikes = this.state.strikes;
        //TODO - this seems hacky?
        let runsPerInningData = this.state.runsPerInningData !== undefined ? this.state.runsPerInningData : responseXML;
        let ballsStrikesXPath = SHOW_BALLS_STRIKES ? `[@balls=${balls}][@strikes=${strikes}]` : '';
        let situationElement = runsPerInningData.evaluate(`//situation[@outs=${outs}][@runners=${runners}]${ballsStrikesXPath}[1]`, this.state.runsPerInningData, null, XPathResult.ANY_UNORDERED_NODE_TYPE, null).singleNodeValue;
        let situationChildren = situationElement.childNodes;
        let total = 0;
        let countByRuns = [];
        for(let i = 0; i < situationChildren.length; ++i) {
            let situationChild = situationChildren[i];
            if (situationChild.localName === "total") {
                total = parseInt(situationChild.innerHTML, 10);
            }
            else {
                let runs = parseInt(situationChild.getAttribute('runs'), 10);
                while (countByRuns.length <= runs) {
                    countByRuns.push(0);
                }
                countByRuns[runs] = parseInt(situationChild.innerHTML, 10);
            }
        }
        this.setState({runsPerInning: new RunsPerInningResult(total, countByRuns)});
    }
    setInning(newInning) {
        this.setState({inning: newInning}, () => this.updateCalculations());
    }
    setOuts(newOuts) {
        this.setState({outs: newOuts}, () => this.updateCalculations());
    }
    setRunners(newRunners) {
        this.setState({runners: newRunners}, () => this.updateCalculations());
    }
    setScore(newScore) {
        this.setState({score: newScore}, () => this.updateCalculations());
    }
    setYears(newYears) {
        this.setState({years: newYears}, () => this.updateCalculations());
    }
    setBalls(newBalls) {
        this.setState({balls: newBalls}, () => this.updateCalculations());
    }
    setStrikes(newStrikes) {
        this.setState({strikes: newStrikes}, () => this.updateCalculations());
    }
    createStatsResults(isPrimary, name, years) {
        return <StatsResults isPrimary={isPrimary} name={name}
         total={this.state["results" + name].total} wins={this.state["results" + name].wins} leverageIndex={this.state["results" + name].leverageIndex} isHome={this.state["results" + name].isHome} isInitial={this.state["results" + name].isInitial} years={isPrimary ? [] : years} key={name} />
    }
    render() {
        const NUM_INNINGS = 11;
        let primaryStatsResultsList = []
        primaryStatsResultsList.push(this.createStatsResults(true, 'output', []));
        let statsResultsList = [];
        for (let i = 0; i < extraYears.length; ++i)
        {
            const localStartYear = extraYears[i][0];
            const localEndYear = extraYears[i][1];
            const transformedYears = transformYears(localStartYear, localEndYear);
            statsResultsList.push(this.createStatsResults(false, 'output' + i, transformedYears));
        }
        return <div>
            <InningTable numInnings={NUM_INNINGS} inning={this.state.inning} setInning={inning => this.setInning(inning)} />
            <div style={{float: 'left'}}>
                <OutsControl outs={this.state.outs} setOuts={outs => this.setOuts(outs)} />
                <RunnersOnBaseList runners={this.state.runners} setRunners={run => this.setRunners(run)} />
                <ScoreTable score={this.state.score} setScore={score => this.setScore(score)} />
                { SHOW_BALLS_STRIKES && <BallsStrikesControl balls={this.state.balls} strikes={this.state.strikes} setBalls={balls => this.setBalls(balls)} setStrikes={strikes => this.setStrikes(strikes)} /> }
                <YearsSlider years={this.state.years} setYears={years => this.setYears(years)} />
            </div>
            <div style={{float: 'left', marginLeft: '25px'}}>
                <RunnersOnBaseDiamond runners={this.state.runners} setRunners={run => this.setRunners(run)} />
            </div>
            <div style={{clear: 'both', float: 'left'}}>
                <IndeterminateProgressBar active={this.state.pendingCount > 0} />
                {primaryStatsResultsList}
            </div>
            <div style={{float: 'left'}}>
                <RunsPerInningResultComponent result={this.state.runsPerInning} flash={this.state.flash}  />
            </div>
            <div style={{clear: 'both'}}>
                {statsResultsList}
            </div>
            <div style={{clear: 'both'}} />
        </div>;
    }
}

export default BaseballSituation
