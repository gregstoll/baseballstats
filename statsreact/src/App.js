import './App.css'

import React, {Component} from 'react'
import ReactDOM from 'react-dom'
import ReactSlider from 'react-slider'
import { CSSTransitionGroup } from 'react-transition-group'
import $ from 'jquery';

import 'jquery-ui/themes/base/core.css';
import 'jquery-ui/themes/base/theme.css';
import 'jquery-ui/themes/base/selectable.css';
import 'jquery-ui/ui/core';
import 'jquery-ui/ui/effect';
import 'jquery-ui/ui/effects/effect-highlight.js';


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
        return <td><input type="radio" name="inningRadio" value="{this.props.inning.homeOrVisitor + this.props.inning.num}" defaultChecked={this.props.inning.homeOrVisitor == this.props.chosenInning.homeOrVisitor && this.props.inning.num == this.props.chosenInning.num} onClick={this.handleClick.bind(this)} /></td>;
    }
}
class InningTable extends Component {
    setInning(inning) {
        this.props.setInning(inning);
    }
    render() {
        var i;
        var headers = [];
        for (i = 1; i <= this.props.numInnings; ++i)
        {
            headers.push(<InningHeader key={i} inningNum={i} />);
        }
        var visitorChoices = [];
        for (i = 1; i <= this.props.numInnings; ++i)
        {
            var thisInning = {homeOrVisitor: 'V', num: i};
            visitorChoices.push(<InningChoice key={thisInning.homeOrVisitor + thisInning.num} inning={thisInning} chosenInning={this.props.inning} setInning={this.setInning.bind(this)} />);
        }
        var homeChoices = [];
        for (i = 1; i <= this.props.numInnings; ++i)
        {
            var thisInning = {homeOrVisitor: 'H', num: i};
            homeChoices.push(<InningChoice key={thisInning.homeOrVisitor + thisInning.num} inning={thisInning} chosenInning={this.props.inning} setInning={this.setInning.bind(this)} />);
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
        this.props.setOuts((this.props.outs == 2) ? 0 : this.props.outs + 1);
    }
    getOutsColor(on) {
        return on ? '#ff0000' : '#ffffff';
    }
    render() {
        var WIDTH = 75;
        var HEIGHT = 40;
        var WIDTH_MARGIN = 5;
        var HEIGHT_MARGIN = 5;

        var circleRadius = Math.min(WIDTH - 3 * WIDTH_MARGIN, HEIGHT - 2 * HEIGHT_MARGIN) / 2;
        return <p className="littlespace" style={{"display": "flex", "alignItems": "center"}}><span>Outs:</span>
        <svg width={WIDTH} height={HEIGHT} onClick={this.handleClick.bind(this)}>
            <circle cx={WIDTH/4} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getOutsColor(this.props.outs >= 1)} />
            <circle cx={(3*WIDTH)/4} cy={HEIGHT/2} r={circleRadius} stroke="#a0522d" fill={this.getOutsColor(this.props.outs >= 2)} />
        </svg>
        </p>;
    }
}
class RunnersOnBaseList extends Component {
    handleChange(e) {
        this.props.setRunners(e.target.value);
    }
    render() {
        return <p className="littlespace">Runners on base:&nbsp;
        <select onChange={this.handleChange.bind(this)} value={this.props.runners}>
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
        var visitorScore = '';
        var homeScore = '';
        if (this.props.score < 0) {
            visitorScore = '+' + (-1 * this.props.score);
        } else if (this.props.score > 0) {
            homeScore = '+' + (this.props.score);
        } else {
            visitorScore = "Tie";
            homeScore = "Tie";
        }
        return <table className="scoreTable"><tbody>
            <tr><th>Visitor</th><td>{visitorScore}</td><td><button onClick={this.handleVisitorClick.bind(this)}>+</button></td></tr>
            <tr><th>Home</th><td>{homeScore}</td><td><button onClick={this.handleHomeClick.bind(this)}>+</button></td></tr>
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
        var WIDTH = 200;
        var HEIGHT = 200;

        var first = (this.props.runners - 1) & 1;
        var second = (this.props.runners - 1) & 2;
        var third = (this.props.runners - 1) & 4;
        var baseSize = Math.max(WIDTH*0.1, 10);

        var homeCenter = [WIDTH/2, HEIGHT*0.85];
        var homePoints = [[homeCenter[0], homeCenter[1] + baseSize], [homeCenter[0] + baseSize, homeCenter[1]], [homeCenter[0] + baseSize], [homeCenter[1] - baseSize], [homeCenter[0] - baseSize, homeCenter[1] - baseSize], [homeCenter[0] - baseSize, homeCenter[1]]];

        var firstCenter = [WIDTH*0.85, HEIGHT/2];
        var firstPoints = this.pointsFromCenter(firstCenter, baseSize);

        var secondCenter = [WIDTH/2, HEIGHT*0.15];
        var secondPoints = this.pointsFromCenter(secondCenter, baseSize);

        var thirdCenter = [WIDTH*0.15, HEIGHT/2];
        var thirdPoints = this.pointsFromCenter(thirdCenter, baseSize);
        
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
            <polygon points={firstPoints} strokeWidth="0" fill={this.getBaseColor(first)} onClick={this.toggleFirst.bind(this)} />
            { /* second base */ }
            <polygon points={secondPoints} strokeWidth="0" fill={this.getBaseColor(second)} onClick={this.toggleSecond.bind(this)}/>
            { /* third base */ }
            <polygon points={thirdPoints} strokeWidth="0" fill={this.getBaseColor(third)} onClick={this.toggleThird.bind(this)}/>
        </svg>
        </div>;
    }
}
class YearsSlider extends Component {
    onChange(value) {
        if (this.setYearsEvent != undefined) {
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
            <ReactSlider className="horizontal-slider" orientation="horizontal" withBars={true} defaultValue={[this.state.years[0], this.state.years[1]]} min={MIN_YEAR} max={MAX_YEAR} onChange={this.onChange.bind(this)} />
        </div>
    }
}
class StatsResults extends Component {
    componentDidMount() {
        var node = ReactDOM.findDOMNode(this);
        $('.realOutput', node).effect("highlight");
    }
    componentDidUpdate(prevProps, prevState) {
        var differences = false;
        var properties = Object.keys(this.props);
        for (var i in properties) {
            if (properties[i] != 'years' && this.props[properties[i]] != prevProps[properties[i]]) {
                differences = true;
                break;
            }
        }
        if (differences) {
            var node = ReactDOM.findDOMNode(this);
            $('.realOutput', node).effect("highlight");
        }
    }
    render() {
        var mainDivStyle = {width: '300px', float: 'left'};
        if (!this.props.isPrimary) {
            mainDivStyle.marginTop = '20px';
        }
        if (this.props.isInitial) {
            return <div style={mainDivStyle}/>
        }
        var key = this.props.name;// + Math.random();
        if (this.props.total === 0) {
            key = key + 'none';
            return <div style={mainDivStyle}>
                <CSSTransitionGroup transitionName="outputTransition" transitionAppear={false} transitionLeave={false} >
                <div className="realOutput" key={key}>No data found!</div>
                </CSSTransitionGroup>
                </div>
        }
        var r = this.props;
        var wins = r.wins;
        var percent = (100 * wins) / r.total;
        var displayPercent = Math.round(percent * 100)/100;
        var displayHome = r.isHome; 
        var homeMoneyLine = '';
        var visitorMoneyLine = '';
        if (displayPercent < 50)
        {
            displayPercent = Math.round((100 - displayPercent) * 100)/100;
            wins = r.total - wins;
            displayHome = !displayHome;
        }
        var ml = Math.round((displayPercent/(100 - displayPercent)) * -100);
        var oml = "+" + (-1 * ml);
        if (displayHome) {
            homeMoneyLine = ml;
            visitorMoneyLine = oml;
        } else {
            homeMoneyLine = oml;
            visitorMoneyLine = ml;
        }
        // TODO - refactor leverage stuff
        var leverageDescription = 'Low';
        var leverageClass = 'leverageLow';
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
        var winnerTeamText = displayHome ? "Home" : "Visitor";
        // make this something that always changes
        // this uses CSSTransitionGroup when change from some to no output
        var yearsStyle = r.isPrimary ? {display : 'none'} : {};
        return <div style={mainDivStyle}>
            <CSSTransitionGroup transitionName="outputTransition" transitionAppear={false} transitionEnterTimeout={0} transitionLeaveTimeout={0}>
            <div className="realOutput" key={key}>
            <p className="littlespace" style={yearsStyle}>Years: {r.years[0]} - {r.years[1]}</p>
            <p className="littlespace">Total games: {r.total}</p>
            <p className="littlespace">Wins for {winnerTeamText}: {wins}</p>
            <p className="littlespace">Win percentage: <b>{winnerTeamText} {displayPercent}%</b></p>
            <p className="littlespace">Leverage index: <b className={leverageClass}>{r.leverageIndex} ({leverageDescription})</b></p>
            <p className="littlespace">Home money line: <b>{homeMoneyLine}</b></p>
            <p className="littlespace">Visitor money line: <b>{visitorMoneyLine}</b></p>
            </div>
            </CSSTransitionGroup>
        </div>;
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
        var state = {inning: {homeOrVisitor: 'V', num: 1}, outs: 0, runners: 1, score: 0, years: [MIN_YEAR, MAX_YEAR], pendingRequests: false};
        this.addInitialState(state, 'output', []);
        var i;
        for (i = 0; i < extraYears.length; ++i)
        {
            var localStartYear = extraYears[i][0];
            var localEndYear = extraYears[i][1];
            var transformedYears = transformYears(localStartYear, localEndYear);
            this.addInitialState(state, 'output' + i, transformedYears);
        }
        // parse query hash
        if (window.location.hash) {
            var hash = window.location.hash.substring(1);
            var parts = hash.split(".");
            if (parts.length === 7 || parts.length === 5) {
                var whichTeam = parts[0];
                var scorediff = parseInt(parts[1]);
                var inning = parts[2];
                var outs = parts[3];
                var runners = parts[4];
                var startYear = MIN_YEAR;
                var endYear = MAX_YEAR;
                if (parts.length === 7) {
                    startYear = parseInt(parts[5]);
                    endYear = parseInt(parts[6]);
                    if (isNaN(startYear) || isNaN(endYear)) {
                        startYear = MIN_YEAR;
                        endYear = MAX_YEAR;
                    }
                }

                state.inning.homeOrVisitor = parts[0];
                state.score = parseInt(parts[1]);
                state.inning.num = parseInt(parts[2]);
                state.outs = parseInt(parts[3]);
                state.runners = parseInt(parts[4]);
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
        var s = this.state;
        // update query hash
        var hash = s.inning.homeOrVisitor + "." + s.score + "." + s.inning.num + "." + s.outs + "." + s.runners;
        if (s.years[0] != MIN_YEAR || s.years[1] != MAX_YEAR) {
            hash += "." + s.years[0] + "." + s.years[1];
        }
        window.location.hash = hash;

        // set up progress bar state
        this.setState({'pendingHash' : hash, 'pendingCount': 1 + extraYears.length});

        this.calculateStats(s.inning.homeOrVisitor, s.score, s.inning.num, s.outs, s.runners, s.years[0], s.years[1], 'output', hash);
        var i;
        for (i = 0; i < extraYears.length; ++i)
        {
            var localStartYear = extraYears[i][0];
            var localEndYear = extraYears[i][1];
            var transformedYears = transformYears(localStartYear, localEndYear);
            localStartYear = transformedYears[0];
            localEndYear = transformedYears[1];
            this.calculateStats(s.inning.homeOrVisitor, s.score, s.inning.num, s.outs, s.runners, localStartYear, localEndYear, 'output' + i, hash);
        }
    }
    calculateStats(whichTeam, scorediff, inning, outs, runners, startYear, endYear, name, hash) {
        var isHome = whichTeam === "H";
        if (!isHome)
        {
            scorediff *= -1;
        }
        var stateString = '"' + whichTeam + '",' + inning + ',' + outs + ',' + runners + ',' + scorediff;
        // TODO url
        $.ajax({url: 'https://gregstoll.dyndns.org/~gregstoll/baseball/getcumulativestats.cgi', data: {stateString: stateString, startYear: startYear, endYear: endYear, rand: Math.random()}, dataType: "json", complete: function(xhr, textStatus) {

            var theseResults = this.state['results' + name];
            theseResults.total = parseInt(xhr.responseJSON.total);
            theseResults.wins = parseInt(xhr.responseJSON.wins);
            theseResults.leverageIndex = parseFloat(xhr.responseJSON.leverage);
            theseResults.isHome = isHome;
            theseResults.isInitial = false;
            var newState = {}
            newState['results' + name] = theseResults;
            //this.setState(newState);
            // use the callback for to atomically update pendingCount
            this.setState(function(previousState, currentProps) {
                if (hash === previousState['pendingHash']) {
                    newState['pendingCount'] = newState['pendingCount'] - 1;
                }
                return newState;
            });
        }.bind(this)});
    }
    setInning(newInning) {
        this.setState({inning: newInning}, this.updateCalculations.bind(this));
    }
    setOuts(newOuts) {
        this.setState({outs: newOuts}, this.updateCalculations.bind(this));
    }
    setRunners(newRunners) {
        this.setState({runners: newRunners}, this.updateCalculations.bind(this));
    }
    setScore(newScore) {
        this.setState({score: newScore}, this.updateCalculations.bind(this));
    }
    setYears(newYears) {
        this.setState({years: newYears}, this.updateCalculations.bind(this));
    }
    createStatsResults(isPrimary, name, years) {
        return <StatsResults isPrimary={isPrimary} name={name}
         total={this.state["results" + name].total} wins={this.state["results" + name].wins} leverageIndex={this.state["results" + name].leverageIndex} isHome={this.state["results" + name].isHome} isInitial={this.state["results" + name].isInitial} years={isPrimary ? [] : years} key={name} />
    }
    render() {
        var NUM_INNINGS = 11;
        var primaryStatsResultsList = []
        primaryStatsResultsList.push(this.createStatsResults(true, 'output', []));
        var i;
        var statsResultsList = [];
        for (i = 0; i < extraYears.length; ++i)
        {
            var localStartYear = extraYears[i][0];
            var localEndYear = extraYears[i][1];
            var transformedYears = transformYears(localStartYear, localEndYear);
            statsResultsList.ph(is.eateStatsResults(f6lse, 'output' + i, transformedYears));
        }
        return <div>
            <InningTable numInnings={NUM_INNINGS} inning={this.state.inning} setInning={this.setInning.bind(this)} />
            <div style={{float: 'left'}}>
                <OutsControl outs={this.state.outs} setOuts={this.setOuts.bind(this)} />
                <RunnersOnBaseList runners={this.state.runners} setRunners={this.setRunners.bind(this)} />
                <ScoreTable score={this.state.score} setScore={this.setScore.bind(this)} />
                <YearsSlider years={this.state.years} setYears={this.setYears.bind(this)} />
            </div>
            <div style={{float: 'left', marginLeft: '25px'}}>
                <RunnersOnBaseDiamond runners={this.state.runners} setRunners={this.setRunners.bind(this)} />
            </div>
            <div style={{clear: 'both'}}>
                <IndeterminateProgressBar active={this.state.pendingCount > 0} />
            </div>
            {primaryStatsResultsList}
            <div style={{clear: 'both'}}>
                {statsResultsList}
            </div>
            <div style={{clear: 'both'}} />
        </div>;
    }
}

export default BaseballSituation
