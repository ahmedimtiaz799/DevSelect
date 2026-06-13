/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark:          '#2b2d42',
          muted:         '#5b5d74',
          body:          '#2d3435',
          secondary:     '#475569',
          sidebarActive: '#3d4057',
          userBubble:    '#e8e9ef',
          inputBg:       '#f5f5f5',
          textLoading:   '#808080',
          iconGray:      '#596061',
          scrollbar:     '#aeabab',
          error:         '#b91c1c',
          errorBg:       '#fef2f2',
          warning:       '#92400e',
          warningBg:     '#fffbeb',
          info:          '#334155',
          infoBg:        '#f8fafc',
          success:       '#166534',
          successBg:     '#f0fdf4',
          systemText:    '#6b7280',
          focusRing:     '#6d7c95',
          surfaceSubtle: '#f8fafc',
        },
        page: {
          default: '#f5f5f5',
          auth:    '#ffffff',
          chat:    '#f9f9f9',
        },
        ds: {
          bg: 'var(--ds-bg)',
          surface: 'var(--ds-surface)',
          'surface-subtle': 'var(--ds-surface-subtle)',
          'surface-muted': 'var(--ds-surface-muted)',
          'surface-elevated': 'var(--ds-surface-elevated)',

          sidebar: 'var(--ds-sidebar)',

          'text-strong': 'var(--ds-text-strong)',
          text: 'var(--ds-text)',
          'text-secondary': 'var(--ds-text-secondary)',
          'text-muted': 'var(--ds-text-muted)',
          'text-subtle': 'var(--ds-text-subtle)',
          'text-inverse': 'var(--ds-text-inverse)',

          border: 'var(--ds-border)',
          'border-subtle': 'var(--ds-border-subtle)',
          'border-strong': 'var(--ds-border-strong)',

          accent: 'var(--ds-accent)',
          'accent-hover': 'var(--ds-accent-hover)',
          'accent-soft': 'var(--ds-accent-soft)',

          'button-primary': 'var(--ds-button-primary)',
          'button-primary-hover': 'var(--ds-button-primary-hover)',
          'button-primary-text': 'var(--ds-button-primary-text)',

          'button-secondary': 'var(--ds-button-secondary)',
          'button-secondary-hover': 'var(--ds-button-secondary-hover)',
          'button-secondary-border': 'var(--ds-button-secondary-border)',
          'button-secondary-text': 'var(--ds-button-secondary-text)',

          input: 'var(--ds-input)',
          'user-bubble': 'var(--ds-user-bubble)',

          'icon-muted': 'var(--ds-icon-muted)',
          'focus-ring': 'var(--ds-focus-ring)',

          danger: 'var(--ds-danger)',
          'danger-bg': 'var(--ds-danger-bg)',
          warning: 'var(--ds-warning)',
          'warning-bg': 'var(--ds-warning-bg)',
          success: 'var(--ds-success)',
          'success-bg': 'var(--ds-success-bg)',
          info: 'var(--ds-info)',
          'info-bg': 'var(--ds-info-bg)',

          scrollbar: 'var(--ds-scrollbar)',
          'scrollbar-hover': 'var(--ds-scrollbar-hover)',
        },
        dsAlpha: {
          bg: 'rgb(var(--ds-bg-rgb) / <alpha-value>)',
          surface: 'rgb(var(--ds-surface-rgb) / <alpha-value>)',
          'surface-subtle': 'rgb(var(--ds-surface-subtle-rgb) / <alpha-value>)',
          'surface-muted': 'rgb(var(--ds-surface-muted-rgb) / <alpha-value>)',
          'surface-elevated': 'rgb(var(--ds-surface-elevated-rgb) / <alpha-value>)',

          sidebar: 'rgb(var(--ds-sidebar-rgb) / <alpha-value>)',

          'text-strong': 'rgb(var(--ds-text-strong-rgb) / <alpha-value>)',
          text: 'rgb(var(--ds-text-rgb) / <alpha-value>)',
          'text-secondary': 'rgb(var(--ds-text-secondary-rgb) / <alpha-value>)',
          'text-muted': 'rgb(var(--ds-text-muted-rgb) / <alpha-value>)',
          'text-subtle': 'rgb(var(--ds-text-subtle-rgb) / <alpha-value>)',
          'text-inverse': 'rgb(var(--ds-text-inverse-rgb) / <alpha-value>)',

          border: 'rgb(var(--ds-border-rgb) / <alpha-value>)',
          'border-subtle': 'rgb(var(--ds-border-subtle-rgb) / <alpha-value>)',
          'border-strong': 'rgb(var(--ds-border-strong-rgb) / <alpha-value>)',

          accent: 'rgb(var(--ds-accent-rgb) / <alpha-value>)',
          'accent-hover': 'rgb(var(--ds-accent-hover-rgb) / <alpha-value>)',

          input: 'rgb(var(--ds-input-rgb) / <alpha-value>)',
          'user-bubble': 'rgb(var(--ds-user-bubble-rgb) / <alpha-value>)',

          'icon-muted': 'rgb(var(--ds-icon-muted-rgb) / <alpha-value>)',
          'focus-ring': 'rgb(var(--ds-focus-ring-rgb) / <alpha-value>)',

          danger: 'rgb(var(--ds-danger-rgb) / <alpha-value>)',
          warning: 'rgb(var(--ds-warning-rgb) / <alpha-value>)',
          success: 'rgb(var(--ds-success-rgb) / <alpha-value>)',
          info: 'rgb(var(--ds-info-rgb) / <alpha-value>)',

          scrollbar: 'rgb(var(--ds-scrollbar-rgb) / <alpha-value>)',
          'scrollbar-hover': 'rgb(var(--ds-scrollbar-hover-rgb) / <alpha-value>)',
        },
      },
      fontSize: {
        'hero':     ['72px',  { lineHeight: '72px',   letterSpacing: '-3.6px', fontWeight: '800' }],
        'display':  ['48px',  { lineHeight: '60px',   letterSpacing: '-1.5px', fontWeight: '800' }],
        'price':    ['48px',  { lineHeight: '48px',                            fontWeight: '900' }],
        'badge':    ['12px',  { lineHeight: '16px',   letterSpacing: '1.2px',  fontWeight: '700' }],
        'btn-lg':   ['18px',  { lineHeight: '28px',                            fontWeight: '600' }],
        'btn-md':   ['16px',  { lineHeight: '24px',   letterSpacing: '0.4px',  fontWeight: '700' }],
        'btn-sm':   ['14px',  { lineHeight: '20px',                            fontWeight: '600' }],
        'body-lg':  ['20px',  { lineHeight: '32.5px',                          fontWeight: '400' }],
        'body':     ['18px',  { lineHeight: '32px',                            fontWeight: '400' }],
        'msg':      ['16px',  { lineHeight: '26px',                            fontWeight: '400' }],
        'ui':       ['14px',  { lineHeight: '20px',   letterSpacing: '-0.35px'                  }],
        'search':   ['13px',  { lineHeight: '20px',                            fontWeight: '400' }],
        'logo-chat':['18px',  { lineHeight: '28px',   letterSpacing: '1.8px',  fontWeight: '800' }],
      },
      borderRadius: {
        'pill':   '9999px',
        'card':   '32px',
        'chat':   '18px',
        'input':  '16px',
        'search': '18px',
        'bubble': '18px',
        'btn':    '48px',
      },
      boxShadow: {
        'sm':   '0px 1px 2px 0px rgba(0,0,0,0.05)',
        'card': '0px 2px 12px 0px rgba(0,0,0,0.08)',
      },
      maxWidth: {
        'hero':     '896px',
        'subtitle': '672px',
        'auth':     '384px',
        'chat':     '896px',
        'bubble':   '665.6px',
        'ai-msg':   '748.8px',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
