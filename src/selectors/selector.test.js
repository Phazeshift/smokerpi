import { getGraphData } from './selector';

describe('getGraphData', () => {
  test('reads graphData out of the smokerpi slice of the store', () => {
    const graphData = [{ i: 0, t: 20 }];
    const state = { smokerpi: { graphData } };
    expect(getGraphData(state)).toBe(graphData);
  });
});
