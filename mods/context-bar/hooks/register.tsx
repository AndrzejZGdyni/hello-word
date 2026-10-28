import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage } from 'claude-code'

import type { Fill } from '../types'

const PANE = 'context-bar'
const COMMANDS = ['context-bar', 'ctx']
const BAR_CELLS = 20
// Emoji squares are wide: ten fit one line on a phone.
const TEXT_CELLS = 10
const fill = atom({ plugin: 'context-bar', key: 'fill' } as const, null, {
  shape: 'fill-1',
})

const toFill = (c: SessionContextUsage): Fill | null =>
  c.tokens === undefined || c.percent === undefined
    ? null
    : { tokens: c.tokens, window: c.window, percent: c.percent }

const barText = (usage: Fill): string => {
  const percent = Math.min(100, Math.max(0, usage.percent))
  const filled = Math.round((percent / 100) * TEXT_CELLS)
  const tokens = usage.tokens.toLocaleString('en-US')
  const window = usage.window.toLocaleString('en-US')

  return `Context\n${'🟦'.repeat(filled)}${'⬜'.repeat(TEXT_CELLS - filled)} ${percent}%\n${tokens} / ${window} tokens`
}

async function openOrShow($: EngineInterface) {
  const { isPlaced } = await $.ui.open({ id: PANE, title: 'Context' })
  if (isPlaced) return { text: 'Context pane opened.' }

  // This surface draws no pane: answer with the bar itself.
  const { context } = await $.session.usage()
  const usage = toFill(context)
  await update($, fill, () => usage)

  return {
    text: usage === null ? 'Context: no response yet.' : barText(usage),
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    for (const name of COMMANDS) {
      await $.command.register({
        name,
        description: 'Show the context window usage bar in a pane',
      })
    }
    const { context } = await $.session.usage()
    await update($, fill, () => toFill(context))
    void $.ui.open({ id: PANE, title: 'Context' })

    return next(e)
  })

  for (const command of COMMANDS) on('command.run', { command }, $ => openOrShow($))

  on('session.measure', async ($, e, next) => {
    if (e.changed.includes('context')) {
      const usage = toFill(e.context)
      await update($, fill, () => usage)
      $.ui.status(usage === null ? undefined : `Context ${usage.percent}%`)
    }

    return next(e)
  })

  // Plain tool output is not drawn on every surface, so the model is handed the
  // line and asked to close each answer with it; the user never sees the block.
  on('prompt.submit', async ($, e, next) => {
    if (e.command !== undefined || e.origin !== undefined) return next(e)

    const { context } = await $.session.usage()
    const usage = toFill(context)
    if (usage === null) return next(e)
    await update($, fill, () => usage)

    return next({
      ...e,
      context: [
        ...(e.context ?? []),
        `context-bar: end your reply with these three lines, as written, each on its own line and with nothing after them:\n${barText(usage)}`,
      ],
    })
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const usage = await read($, fill)
    if (usage === null || e.props.hasSurvey) return next(e)

    const { Text } = $.ui.resolve(e)
    const percent = Math.min(100, Math.max(0, usage.percent))
    const filled = Math.round((percent / 100) * BAR_CELLS)

    return (
      <Text color="blue">
        {'█'.repeat(filled)}
        {'░'.repeat(BAR_CELLS - filled)} {percent}%
      </Text>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const usage = await read($, fill)

    if (usage === null) {
      return <Text dimColor>No response yet: usage shows after the first turn.</Text>
    }

    const percent = Math.min(100, Math.max(0, usage.percent))
    const filled = Math.round((percent / 100) * BAR_CELLS)

    return (
      <Box flexDirection="column">
        <Text>
          <Text color="blue">{'█'.repeat(filled)}</Text>
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
