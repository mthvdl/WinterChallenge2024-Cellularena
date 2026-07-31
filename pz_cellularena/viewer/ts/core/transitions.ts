export function bell(t: number): number {
  return Math.sin(t * Math.PI)
}
export function ease(t: number): number {
  return t * t * (3 - 2 * t)
}
export function easeIn(t: number): number {
  return t * t
}
export function easeOut(t: number): number {
  return t * (2 - t)
}
export function elastic(t: number): number {
  if (t <= 0) return 0
  if (t >= 1) return 1
  const c4 = (2 * Math.PI) / 3
  return -Math.pow(2, 10 * t - 10) * Math.sin((t * 10 - 10.75) * c4)
}
