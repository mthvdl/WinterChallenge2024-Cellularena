const WIDTH = 1920
const HEIGHT = 1080
const FRAME_DURATION = 1000

const stageEl = document.getElementById('stage')
const statusEl = document.getElementById('status')
const replayPathInput = document.getElementById('replayPath')
const loadEngineBtn = document.getElementById('loadEngineBtn')
const fileInput = document.getElementById('fileInput')
const playPauseBtn = document.getElementById('playPauseBtn')
const prevBtn = document.getElementById('prevBtn')
const nextBtn = document.getElementById('nextBtn')
const speedSel = document.getElementById('speedSel')
const turnRange = document.getElementById('turnRange')

const app = new PIXI.Application({
  width: WIDTH,
  height: HEIGHT,
  antialias: true,
  backgroundColor: 0x000000,
})
stageEl.appendChild(app.view)

const assets = [
  'assets/blue.json',
  'assets/orange.json',
  'assets/green.json',
  'assets/walls.json',
  'assets/Background_2.jpg',
  'assets/HUD.png',
  'assets/Mur_2.png',
  'assets/logo.png',
  'assets/dial_arrow.png',
  'assets/dial_mid.png',
  'assets/dial_side.png',
]

let assetsLoaded = false
let viewModule = null
let states = []
let frameIndex = 0
let frameProgress = 1
let paused = true
let speed = 1

const CONVERT_API_CANDIDATES = [
  '/api/convert-replay',
  'http://127.0.0.1:8010/api/convert-replay',
]

const HEALTH_API_CANDIDATES = [
  '/api/health',
  'http://127.0.0.1:8010/api/health',
]

let resolvedConvertApi = null

async function resolveConvertApiEndpoint() {
  if (resolvedConvertApi) {
    return resolvedConvertApi
  }

  for (let i = 0; i < HEALTH_API_CANDIDATES.length; i += 1) {
    const healthUrl = HEALTH_API_CANDIDATES[i]
    const convertUrl = CONVERT_API_CANDIDATES[i]
    try {
      const response = await fetch(healthUrl, { method: 'GET' })
      if (!response.ok) {
        continue
      }
      const data = await response.json().catch(() => ({}))
      if (data && data.ok) {
        resolvedConvertApi = convertUrl
        return resolvedConvertApi
      }
    } catch {
      // Keep trying remaining candidates.
    }
  }

  // Fallback to default path if no health endpoint is reachable.
  resolvedConvertApi = CONVERT_API_CANDIDATES[0]
  return resolvedConvertApi
}

function setStatus(text) {
  statusEl.textContent = text
}

function loadAssets() {
  if (assetsLoaded) {
    return Promise.resolve()
  }

  return new Promise((resolve, reject) => {
    const loader = PIXI.Loader.shared
    assets.forEach((url) => {
      if (!loader.resources[url]) {
        loader.add(url, url)
      }
    })

    loader.load((_, resources) => {
      const hasError = assets.some((url) => !resources[url])
      if (hasError) {
        reject(new Error('Failed to load one or more viewer assets'))
        return
      }
      assetsLoaded = true
      resolve()
    })

    loader.onError.once((err) => {
      reject(err instanceof Error ? err : new Error(String(err)))
    })
  })
}

function unwrapReplay(raw) {
  if (raw && raw.success) {
    return raw.success
  }
  return raw
}

function extractGraphicsFromView(viewStr) {
  if (typeof viewStr !== 'string') {
    return null
  }
  const splitAt = viewStr.indexOf('\n')
  if (splitAt < 0) {
    return null
  }
  const payload = viewStr.slice(splitAt + 1).trim()
  if (!payload) {
    return null
  }

  try {
    const parsed = JSON.parse(payload)
    return (parsed.global && parsed.global.graphics) || parsed.graphics || null
  } catch {
    return null
  }
}

function parseReplay(rawReplay) {
  const replay = unwrapReplay(rawReplay)

  if (!replay || !Array.isArray(replay.frames) || replay.frames.length === 0) {
    throw new Error('Invalid replay format: missing frames')
  }

  const frames = replay.frames
  const formatA = Object.prototype.hasOwnProperty.call(frames[0], 'data')

  let globalRaw = ''
  const frameRaws = []

  if (formatA) {
    globalRaw = frames[0].data || ''
    for (let i = 1; i < frames.length; i += 1) {
      const raw = frames[i].data
      if (typeof raw === 'string' && raw.trim() !== '') {
        frameRaws.push(raw)
      }
    }
  } else {
    globalRaw = extractGraphicsFromView(frames[0].view) || ''
    for (let i = 1; i < frames.length; i += 2) {
      const a = frames[i]
      const b = frames[i + 1] || {}
      const raw = extractGraphicsFromView(b.view) || extractGraphicsFromView(a.view)
      if (raw) {
        frameRaws.push(raw)
      }
    }
  }

  if (!globalRaw) {
    throw new Error('Could not extract global graphics data from replay')
  }

  if (frameRaws.length === 0) {
    throw new Error('No frame graphics data found in replay')
  }

  const agents = Array.isArray(replay.agents) ? replay.agents : []
  const players = [0, 1].map((idx) => {
    const found = agents.find((a) => Number(a.index) === idx)
    return {
      name: found && found.name ? String(found.name) : `Player ${idx}`,
      avatar: PIXI.Texture.from('assets/logo.png'),
      color: idx === 0 ? 0xfd5901 : 0x33adcc,
      index: idx,
      isMe: false,
      number: idx,
    }
  })

  return { globalRaw, frameRaws, players }
}

function resetPlaybackUi() {
  turnRange.min = '0'
  turnRange.max = String(Math.max(0, states.length - 1))
  turnRange.value = '0'
  playPauseBtn.textContent = paused ? 'Play' : 'Pause'
}

function updateScene() {
  if (!viewModule || states.length === 0) {
    return
  }

  const current = states[frameIndex]
  const previous = frameIndex > 0 ? states[frameIndex - 1] : current
  viewModule.updateScene(previous, current, frameProgress, speed)
  setStatus(`Turn ${frameIndex + 1}/${states.length} | speed ${speed}x | ${paused ? 'paused' : 'playing'}`)
}

async function loadReplayObject(rawReplay) {
  setStatus('Loading assets...')
  await loadAssets()

  const { globalRaw, frameRaws, players } = parseReplay(rawReplay)
  app.stage.removeChildren()

  const viewerApi = window.CellularenaViewer
  viewModule = new viewerApi.ViewModule()
  viewerApi.setRenderer(app.renderer)

  viewModule.handleGlobalData(players, globalRaw)

  // First parse all frames so global tile needs include every organ/event tile.
  // Scene init uses this set to pre-allocate organ sprites per tile.
  viewModule.states = []
  states = frameRaws.map((raw, idx) =>
    viewModule.handleFrameData(
      {
        number: idx,
        frameDuration: FRAME_DURATION,
        date: idx * FRAME_DURATION,
      },
      raw,
    ),
  )

  viewModule.reinitScene(app.stage, { width: WIDTH, height: HEIGHT, oversampling: 1 })

  frameIndex = 0
  frameProgress = 1
  paused = true
  speed = Number(speedSel.value)
  resetPlaybackUi()
  updateScene()
}

async function loadReplayPath(path) {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} while loading ${path}`)
  }
  const json = await response.json()
  await loadReplayObject(json)
}

async function convertReplayViaEngine(rawReplay) {
  const endpoint = await resolveConvertApiEndpoint()

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ replay: rawReplay }),
    })

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.error || `Engine conversion failed with HTTP ${response.status}`)
    }
    if (!data.viewerReplay) {
      throw new Error('Engine conversion succeeded but no viewerReplay was returned')
    }
    return data.viewerReplay
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    throw new Error(
      `${message}. Start: python viewer_server.py --port 8000 (or keep API at http://127.0.0.1:8010)`
    )
  }
}

async function loadReplayPathViaEngine(path) {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} while loading ${path}`)
  }
  const rawReplay = await response.json()
  const viewerReplay = await convertReplayViaEngine(rawReplay)
  await loadReplayObject(viewerReplay)
}

app.ticker.add((delta) => {
  if (viewModule) {
    if (!paused && states.length > 1) {
      frameProgress += (delta / 60) * speed
      if (frameProgress >= 1) {
        frameProgress = 0
        if (frameIndex < states.length - 1) {
          frameIndex += 1
          turnRange.value = String(frameIndex)
        } else {
          paused = true
          frameProgress = 1
          playPauseBtn.textContent = 'Play'
        }
      }
    }

    updateScene()
    viewModule.animateScene(delta)
  }
})

playPauseBtn.addEventListener('click', () => {
  if (!states.length) {
    return
  }
  paused = !paused
  playPauseBtn.textContent = paused ? 'Play' : 'Pause'
  updateScene()
})

prevBtn.addEventListener('click', () => {
  if (!states.length) {
    return
  }
  paused = true
  playPauseBtn.textContent = 'Play'
  frameProgress = 1
  frameIndex = Math.max(0, frameIndex - 1)
  turnRange.value = String(frameIndex)
  updateScene()
})

nextBtn.addEventListener('click', () => {
  if (!states.length) {
    return
  }
  paused = true
  playPauseBtn.textContent = 'Play'
  frameProgress = 1
  frameIndex = Math.min(states.length - 1, frameIndex + 1)
  turnRange.value = String(frameIndex)
  updateScene()
})

speedSel.addEventListener('change', () => {
  speed = Number(speedSel.value)
  updateScene()
})

turnRange.addEventListener('input', () => {
  if (!states.length) {
    return
  }
  paused = true
  playPauseBtn.textContent = 'Play'
  frameIndex = Number(turnRange.value)
  frameProgress = 1
  updateScene()
})

loadEngineBtn.addEventListener('click', async () => {
  const replayPath = replayPathInput.value.trim()
  if (!replayPath) {
    setStatus('Enter a replay path first')
    return
  }

  try {
    setStatus(`Running engine simulation for ${replayPath} ...`)
    await loadReplayPathViaEngine(replayPath)
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    setStatus(`Engine load error: ${message}`)
  }
})

replayPathInput.addEventListener('keydown', async (event) => {
  if (event.key !== 'Enter') {
    return
  }
  event.preventDefault()
  loadEngineBtn.click()
})

fileInput.addEventListener('change', async (event) => {
  const file = event.target.files && event.target.files[0]
  if (!file) {
    return
  }

  try {
    setStatus(`Reading ${file.name} ...`)
    const raw = await file.text()
    const json = JSON.parse(raw)
    setStatus('Simulating replay in engine ...')
    const viewerReplay = await convertReplayViaEngine(json)
    await loadReplayObject(viewerReplay)
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    setStatus(`Replay parse error: ${message}`)
  }
})

setStatus('Use Load Replay to simulate raw/core replay and render without saving viewer files')
