import { AnimatedSprite, systems } from 'pixi.js'

export type ContainerConsumer = (layer: PIXI.Container) => void

/**
 * Given by the SDK
 */
export interface FrameInfo {
  number: number
  frameDuration: number
  date: number
}
/**
 * Given by the SDK
 */
export interface CanvasInfo {
  width: number
  height: number
  oversampling: number
}
/**
 * Given by the SDK
 */
export interface PlayerInfo {
  name: string
  avatar: PIXI.Texture
  color: number
  index: number
  isMe: boolean
  number: number
  type?: string
}


/*
* Particle systems
*/
export interface Effect {
  busy: boolean
  display: PIXI.DisplayObject
}
export interface SpriteEffect {
  busy: boolean
  display: PIXI.Sprite
}
export interface AnimatedEffect extends Effect {
  display: AnimatedSprite
}

export interface Organ {
  sprite: PIXI.Sprite
  container: PIXI.Container
  tail: PIXI.Sprite
}

export interface CoordDto {
  x: number
  y: number
}

export interface OrganDto {
  id: number
  pos: CoordDto
  type: string
  direction: string
  parentId?: number

  /* generated locally */
  playerIdx: number
}

export interface FrameDataDTO {
  storage: number[][]
  events: EventDto[]
  messages: Record<number, string>[]
}

export interface FrameData extends FrameDataDTO, FrameInfo {
  previous: FrameData
  tiles: Tile[]
  organs: OrganDto[][]
  organById: Record<number, OrganDto>
  organByTileIdx: Record<number, OrganDto>,
  rootTileIdxByTileIdx: Record<number, number>
}

export interface TileDto {
  obstacle: boolean
  protein: string
}
export interface Tile extends TileDto {
  organ: OrganDto
}

export interface GlobalDataDTO {
  width: number
  height: number
  tiles: TileDto[]
  organs: OrganDto[][]
}

export interface GlobalData extends GlobalDataDTO {
  players: PlayerInfo[]
  playerCount: number
  tileIdxInNeedOfOrgan: Set<number>
}

export interface AnimData {
  start: number
  end: number
}

export interface EventDto {
  type: number
  animData: AnimData
  playerIdx: number
  id: number
  coord: CoordDto
  target: CoordDto
  organType: string
  direction: string
  coords: CoordDto[]
}