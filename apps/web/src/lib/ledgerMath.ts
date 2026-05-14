export function round2(n: number) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function computeStake(multiplier: number) {
  return round2(2 * multiplier);
}

export function computeEstimatedPayout(spValues: number[], multiplier: number) {
  const product = spValues.reduce((acc, sp) => acc * sp, 1);
  return round2(2 * multiplier * product);
}
