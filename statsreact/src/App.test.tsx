import React from 'react';
import ReactDOM from 'react-dom';
import App, { RunsPerInningResult } from './App';

it('renders without crashing', () => {
  const div = document.createElement('div');
  ReactDOM.render(<App />, div);
  ReactDOM.unmountComponentAtNode(div);
});

it('runsPerInningResult_GetExpectedRuns', () => {
  const result = makeSampleRunsPerInningResult();
  expect(result.getExpectedRuns()).toBeCloseTo(197/200);
});

it('runsPerInningResult_ForExactNumberOfRuns_0', () => {
  const result = makeSampleRunsPerInningResult();
  expect(result.getProbabilityForExactNumberOfRuns(0)).toBeCloseTo(1/2);
});

it('runsPerInningResult_ForExactNumberOfRuns_1', () => {
  const result = makeSampleRunsPerInningResult();
  expect(result.getProbabilityForExactNumberOfRuns(1)).toBeCloseTo(1/4);
});

it('runsPerInningResult_ForExactNumberOfRuns_6', () => {
  const result = makeSampleRunsPerInningResult();
  expect(result.getProbabilityForExactNumberOfRuns(6)).toBeCloseTo(1/100);
});

it('runsPerInningResult_ForAtLeastNumberOfRuns_0', () => {
  const result = makeSampleRunsPerInningResult();
  expect(result.getProbabilityForAtLeastNumberOfRuns(0)).toBeCloseTo(1);
});

it('runsPerInningResult_ForAtLeastNumberOfRuns_1', () => {
  const result = makeSampleRunsPerInningResult();
  expect(result.getProbabilityForAtLeastNumberOfRuns(1)).toBeCloseTo(1/2);
});

it('runsPerInningResult_ForAtLeastNumberOfRuns_6', () => {
  const result = makeSampleRunsPerInningResult();
  expect(result.getProbabilityForAtLeastNumberOfRuns(6)).toBeCloseTo(1/100);
});

function makeSampleRunsPerInningResult(): RunsPerInningResult {
  return new RunsPerInningResult(200, [100, 50, 20, 20, 5, 3, 2]);
}