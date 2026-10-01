// Shared deterministic data for the browser experiment and its runnable check.
export const WIDTH = 512;
export const STRIDE = 32;
export const COUNTS = [64, 1024, 4096];
export function makeInstances(count) {
  if (!COUNTS.includes(count)) throw Error('count must be 64, 1024 or 4096');
  const side = Math.sqrt(count), values = new Float32Array(count * 8);
  for (let i = 0; i < count; ++i) {
    const x = i % side, y = Math.floor(i / side);
    values.set([-1 + (x + .5) * 2 / side, 1 - (y + .5) * 2 / side,
      .72 / side, .72 / side, .1 + .6 * x / (side - 1),
      .1 + .6 * y / (side - 1), .25, 1], i * 8);
  }
  return values;
}
export function summarize(values) {
  if (!values.length || values.some(v => !Number.isFinite(v) || v < 0)) throw Error('invalid samples');
  const sorted = [...values].sort((a, b) => a - b);
  const percentile = p => sorted[Math.floor(p * (sorted.length - 1))];
  return {n: sorted.length, p10: percentile(.1), median: percentile(.5), p90: percentile(.9)};
}
