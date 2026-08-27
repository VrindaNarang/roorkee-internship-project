import type { PaletteMode } from '@mui/material'

// Validated categorical palette (CVD-safe adjacent ordering) — see the
// dataviz skill's references/palette.md. Order is fixed; never cycle/reassign.
const CATEGORICAL_LIGHT = [
  '#2a78d6', // blue
  '#1baf7a', // aqua
  '#eda100', // yellow
  '#008300', // green
  '#4a3aa7', // violet
  '#e34948', // red
  '#e87ba4', // magenta
  '#eb6834', // orange
]

const CATEGORICAL_DARK = [
  '#3987e5',
  '#199e70',
  '#c98500',
  '#008300',
  '#9085e9',
  '#e66767',
  '#d55181',
  '#d95926',
]

export function getCategoricalPalette(mode: PaletteMode): string[] {
  return mode === 'dark' ? CATEGORICAL_DARK : CATEGORICAL_LIGHT
}

export function getCategoricalColor(index: number, mode: PaletteMode): string {
  const palette = getCategoricalPalette(mode)
  return palette[index % palette.length]
}

// Single-hue sequential blue, used for ranked-magnitude bars (one measure
// across many categories, not per-category identity).
export function getSequentialColor(mode: PaletteMode): string {
  return mode === 'dark' ? '#3987e5' : '#2a78d6'
}

export function getGridColor(mode: PaletteMode): string {
  return mode === 'dark' ? '#2c2c2a' : '#e1e0d9'
}
