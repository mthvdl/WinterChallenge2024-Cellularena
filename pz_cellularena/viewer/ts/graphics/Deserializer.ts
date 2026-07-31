import { EventDto, FrameDataDTO, GlobalData, GlobalDataDTO, OrganDto, TileDto } from '../types.js'

function splitLine (str: string) {
  return str.length === 0 ? [] : str.split(' ')
}

export function parseData (unsplit: string, globalData: GlobalData): FrameDataDTO {
  const raw = unsplit.split('\n')
  let idx = 0
  const storage: number[][] = []
  const messages: Record<number, string>[] = []

  for (let playerIdx = 0; playerIdx < globalData.playerCount; ++playerIdx) {
    const playerStorage: number[] = []
    const playerMessages:Record<number, string> = {}
    raw[idx++].split(' ').forEach(x => playerStorage.push(+x))
    storage.push(playerStorage)
    const messageCount = +raw[idx++]
    for (let i = 0; i < messageCount; ++i) {
      const message = raw[idx++].split(' ')
      const organId = +message[0]
      const text = message.slice(1).join(' ')
      playerMessages[organId] = text
    }
    messages.push(playerMessages)
  }

  const events: EventDto[] = []
  const eventCount = +raw[idx++]
  for (let i = 0; i < eventCount; ++i) {
    const type = +raw[idx++]
    const start = +raw[idx++]
    const end = +raw[idx++]
    const playerIdx = +raw[idx++]
    const id = +raw[idx++]
    const organType = raw[idx++]
    const direction = raw[idx++]
    const coords = raw[idx++].split('_').map(xy => parseCoord(xy))

    const animData = { start, end }

    events.push({
      playerIdx,
      id,
      type,
      animData,
      coord: coords[0],
      target: coords[1],
      coords,
      organType,
      direction
    })
  }

  return {
    events,
    storage,
    messages
  }
}


export function parseGlobalData (unsplit: string): GlobalDataDTO {
  const raw = unsplit.split('\n')
  let idx = 0
  let line = raw[idx++].split(' ')
  const width = +line[0]
  const height = +line[1]
  const tiles: TileDto[] = []
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const line = raw[idx++].split(' ')
      const obstacle = line[0] === '1'
      const protein = line[1]
      tiles.push({ obstacle, protein })
    }
  }

  const organs: OrganDto[][] = []

  for (let playerIdx = 0; playerIdx < 2; ++playerIdx) {
    const playerOrgans: OrganDto[] = []

    const organCount = +raw[idx++]
    for (let i = 0; i < organCount; i++) {
      const rawOrgan = raw[idx++].split(' ')
      let oIdx = 0
      const organ: OrganDto = {
        id: +rawOrgan[oIdx++],
        pos: { x: +rawOrgan[oIdx++], y: +rawOrgan[oIdx++] },
        type: rawOrgan[oIdx++],
        direction: rawOrgan[oIdx++],
        parentId: +rawOrgan[oIdx++],
        playerIdx
      }
      playerOrgans.push(organ)
    }
    organs.push(playerOrgans)
  }

  return {
    width,
    height,
    organs,
    tiles
  }
}

function parseCoord (coord: string) {
  const [x, y] = coord.split(' ').map(x => +x)
  return { x, y }
}