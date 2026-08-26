import * as PIXI from 'pixi.js'

let _renderer: PIXI.Renderer | null = null
const _destroyList: any[] = []

export function setRenderer(r: PIXI.Renderer): void {
  _renderer = r
}
export function getRenderer(): PIXI.Renderer {
  return _renderer as PIXI.Renderer
}
export function flagForDestructionOnReinit(obj: any): void {
  _destroyList.push(obj)
}
export function flushDestroyList(): void {
  for (const obj of _destroyList) {
    try { obj.destroy?.() } catch (_) {}
  }
  _destroyList.length = 0
}
