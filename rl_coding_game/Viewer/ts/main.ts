/**
 * main.ts – Entry point bundled by esbuild into view/viewer.js
 *
 * Exports a single CellularenaViewer object used by view/index.html.
 */
import { ViewModule } from './graphics/ViewModule.js'
import { setRenderer } from './core/rendering.js'
import type { PlayerInfo, CanvasInfo, FrameData } from './types.js'

export { ViewModule, setRenderer }
