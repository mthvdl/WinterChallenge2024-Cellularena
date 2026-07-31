export function randInt(a: number, b?: number): number {
  if (b === undefined) return Math.floor(Math.random() * a)
  return Math.floor(Math.random() * (b - a) + a)
}
export function lerp(a: number, b: number, u: number): number {
  return a + (b - a) * u
}
export function unlerp(a: number, b: number, v: number): number {
  if (a === b) return 0
  return Math.max(0, Math.min(1, (v - a) / (b - a)))
}
export function unlerpUnclamped(a: number, b: number, v: number): number {
  if (a === b) return 0
  return (v - a) / (b - a)
}
export function lerpAngle(start: number, end: number, amount: number): number {
  return lerp(start, end, amount)
}
export function lerpPosition(
  from: { x: number; y: number },
  to: { x: number; y: number },
  p: number
): { x: number; y: number } {
  return { x: lerp(from.x, to.x, p), y: lerp(from.y, to.y, p) }
}
export function lerpColor(start: number, end: number, amount: number): number {
  const sr = (start >> 16) & 0xff, sg = (start >> 8) & 0xff, sb = start & 0xff
  const er = (end   >> 16) & 0xff, eg = (end   >> 8) & 0xff, eb = end   & 0xff
  return (
    (Math.round(lerp(sr, er, amount)) << 16) |
    (Math.round(lerp(sg, eg, amount)) <<  8) |
     Math.round(lerp(sb, eb, amount))
  )
}
export function pushAll<T>(self: { push: (item: T) => void }, arr: T[]): void {
  arr.forEach(item => self.push(item))
}
export function fitAspectRatio(
  srcWidth: number, srcHeight: number,
  maxWidth: number, maxHeight: number,
  padding: number = 0
): number {
  return Math.min((maxWidth - padding * 2) / srcWidth, (maxHeight - padding * 2) / srcHeight)
}
export function paddingString(word: string, width: number, char: string): string {
  return word.padStart(width, char)
}
