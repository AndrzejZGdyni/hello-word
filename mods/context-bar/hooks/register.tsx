import { atom, read, update } from 'claude-code'
import type { Register, SessionContextUsage } from 'claude-code'

import type { Fill } from '../types'

const PANE = 'context-bar'
const BAR_CELLS = 20
const fill = atom({ plugin: 'context-bar', key: 'fill' } as const, null, {
  shape: 'fill-1',
})

const toFill = (c: SessionContextUsage): Fill | null =>
  c.tokens === undefined || c.percent === undefined
    ? null
    : { tokens: c.tokens, window: c.window, percent: c.percent }

const barText = (usage: Fill): string => {
  const percent = Math.min(100, Math.max(0, usage.percent))
  const filled = Math.round((percent / 100) * BAR_CELLS)

  return `${'█'.repeat(filled)}${'░'.repeat(BAR_CELLS - filled)} ${percent}% (${usage.tokens.toLocaleString('en-US')} / ${usage.window.toLocaleString('en-US')} tokens)`
}

const colorFor = (percent: number) =>
  percent >= 85 ? 'red' : percent >= 60 ? 'yellow' : 'green'

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'context-bar',
      description: 'Show the context window usage bar in a pane',
    })
    const { context } = await $.session.usage()
    await update($, fill, () => toFill(context))
    void $.ui.open({ id: PANE, title: 'Context' })

    return next(e)
  })

  on('command.run', { command: 'context-bar' }, async $ => {
    const { isPlaced } = await $.ui.open({ id: PANE, title: 'Context' })
    if (isPlaced) return { text: 'Context pane opened.' }

    // This surface draws no pane: answer with the bar itself.
    const { context } = await $.session.usage()
    const usage = toFill(context)
    await update($, fill, () => usage)

    return {
      text: usage === null ? 'Context: no response yet.' : `Context: ${barText(usage)}`,
    }
  })

  on('session.measure', async ($, e, next) => {
    if (e.changed.includes('context')) {
      const usage = toFill(e.context)
      await update($, fill, () => usage)
      $.ui.status(usage === null ? undefined : `Context ${usage.percent}%`)
    }

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const usage = await read($, fill)

    if (usage === null) {
      return <Text dimColor>No response yet: usage shows after the first turn.</Text>
    }

    const percent = Math.min(100, Math.max(0, usage.percent))
    const filled = Math.round((percent / 100) * BAR_CELLS)
    const color = colorFor(percent)

    return (
      <Box flexDirection="column">
        <Text>
          <Text color={color}>{'█'.repeat(filled)}</Text>
          <Text dimColor>{'░'.repeat(BAR_CELLS - filled)}</Text>
          {` ${percent}%`}
        </Text>
        <Text dimColor>
          {usage.tokens.toLocaleString('en-US')} / {usage.window.toLocaleString('en-US')} tokens
        </Text>
        {percent >= 85 && <Text color="red">Context nearly full: consider /compact.</Text>}
      </Box>
    )
  })
}
