import type { StageNode, StageScene } from './stage'

export type DesktopNode = StageNode & { fallPerSecond: number }
export type DesktopScene = Omit<StageScene, 'nodes'> & { nodes: DesktopNode[] }

/** Continue known constant note motion between Python camera frames.
 * Hands and scoring remain authoritative in Python; stale input is not predicted.
 */
export function sceneBetweenFrames(scene: DesktopScene, elapsed: number, paused: boolean): StageScene {
  const advance = paused ? 0 : Math.max(0, Math.min(elapsed, 0.1))
  return {
    ...scene,
    nodes: scene.nodes.map(node => ({ ...node, yRatio: node.yRatio + node.fallPerSecond * advance })),
  }
}
