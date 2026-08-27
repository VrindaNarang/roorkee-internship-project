import { alpha, createTheme, type PaletteMode, type Shadows } from '@mui/material/styles'

// Premium enterprise SaaS theme: minimal green accent, neutral surfaces, soft
// shadows over heavy borders. Supports both light and dark palettes.
const getDesignTokens = (mode: PaletteMode) => ({
  palette: {
    mode,
    primary: {
      main: '#16A34A',
      light: '#22C55E',
      dark: '#15803D',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#475569',
      light: '#64748B',
      dark: '#334155',
    },
    success: { main: '#059669' },
    warning: { main: '#D97706' },
    error: { main: '#DC2626' },
    info: { main: '#2563EB' },
    ...(mode === 'light'
      ? {
          background: {
            default: '#F9FAFB',
            paper: '#FFFFFF',
          },
          text: {
            primary: '#111827',
            secondary: '#6B7280',
          },
          divider: '#E5E7EB',
        }
      : {
          background: {
            default: '#0B0D11',
            paper: '#15181E',
          },
          text: {
            primary: '#F3F4F6',
            secondary: '#9CA3AF',
          },
          divider: '#262B34',
        }),
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      'Helvetica',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: { fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontWeight: 600, letterSpacing: '-0.01em' },
    h4: { fontWeight: 600, letterSpacing: '-0.01em' },
    h5: { fontWeight: 600, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    button: { fontWeight: 600 },
  },
})

const TRANSITION = '150ms cubic-bezier(0.4, 0, 0.2, 1)'
const CARD_RADIUS = 16

export function getAppTheme(mode: PaletteMode) {
  const tokens = getDesignTokens(mode)
  const isLight = mode === 'light'

  const cardShadow = isLight
    ? '0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)'
    : '0 1px 2px rgba(0, 0, 0, 0.24), 0 1px 3px rgba(0, 0, 0, 0.28)'
  const cardHoverShadow = isLight
    ? '0 4px 8px rgba(16, 24, 40, 0.06), 0 8px 16px rgba(16, 24, 40, 0.06)'
    : '0 4px 8px rgba(0, 0, 0, 0.3), 0 8px 16px rgba(0, 0, 0, 0.3)'
  const surfaceHover = isLight ? 'rgba(17, 24, 39, 0.035)' : 'rgba(255, 255, 255, 0.045)'
  const headerTint = isLight ? '#F9FAFB' : '#191D24'

  return createTheme({
    ...tokens,
    shadows: [
      'none',
      cardShadow,
      cardShadow,
      cardHoverShadow,
      cardHoverShadow,
      ...(Array(20).fill(cardHoverShadow) as string[]),
    ] as Shadows,
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          '*': { scrollbarWidth: 'thin' },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            borderRadius: CARD_RADIUS,
          },
          outlined: {
            borderColor: tokens.palette.divider,
            boxShadow: cardShadow,
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            boxShadow: 'none',
            borderBottom: `1px solid ${tokens.palette.divider}`,
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            borderRight: `1px solid ${tokens.palette.divider}`,
            backgroundImage: 'none',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 600,
            borderRadius: 10,
            transition: `transform ${TRANSITION}, box-shadow ${TRANSITION}, background-color ${TRANSITION}`,
          },
          contained: {
            boxShadow: 'none',
            '&:hover': {
              boxShadow: isLight
                ? '0 2px 6px rgba(22, 163, 74, 0.28)'
                : '0 2px 8px rgba(34, 197, 94, 0.35)',
              transform: 'translateY(-1px)',
            },
          },
          outlined: {
            borderColor: tokens.palette.divider,
            '&:hover': {
              borderColor: tokens.palette.primary.main,
              backgroundColor: alpha(tokens.palette.primary.main, isLight ? 0.05 : 0.12),
            },
          },
          text: {
            '&:hover': {
              backgroundColor: alpha(tokens.palette.primary.main, isLight ? 0.06 : 0.14),
            },
          },
        },
      },
      MuiIconButton: {
        styleOverrides: {
          root: {
            transition: `background-color ${TRANSITION}, transform ${TRANSITION}`,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            border: `1px solid ${tokens.palette.divider}`,
            boxShadow: cardShadow,
            borderRadius: CARD_RADIUS,
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 999,
            fontWeight: 600,
          },
        },
      },
      MuiTableHead: {
        styleOverrides: {
          root: {
            backgroundColor: headerTint,
            '& .MuiTableCell-root': {
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              color: tokens.palette.text.secondary,
            },
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderColor: tokens.palette.divider,
          },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            transition: `background-color ${TRANSITION}`,
          },
        },
      },
      MuiTableContainer: {
        styleOverrides: {
          root: {
            borderRadius: CARD_RADIUS,
          },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            transition: `border-color ${TRANSITION}, box-shadow ${TRANSITION}`,
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderWidth: 2,
              borderColor: tokens.palette.primary.main,
            },
          },
          notchedOutline: {
            borderColor: tokens.palette.divider,
          },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            borderRadius: 8,
            fontSize: 12,
          },
        },
      },
      MuiMenu: {
        styleOverrides: {
          paper: {
            borderRadius: 12,
            boxShadow: cardHoverShadow,
            border: `1px solid ${tokens.palette.divider}`,
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            transition: `background-color ${TRANSITION}, color ${TRANSITION}`,
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: {
            height: 3,
            borderRadius: 3,
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 600,
          },
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: {
            borderRadius: 999,
          },
        },
      },
      MuiSkeleton: {
        styleOverrides: {
          root: {
            backgroundColor: surfaceHover,
          },
        },
      },
    },
  })
}
