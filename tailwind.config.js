/** Tailwind CSS configuration for the standalone CLI build (scripts/build_css.py).

The palette mirrors the design tokens previously inlined in the two base
templates; edit it here rather than in templates.
*/
module.exports = {
  darkMode: 'class',
  future: {
    hoverOnlyWhenSupported: true,
  },
  content: [
    './templates/**/*.html',
    // PostForm applies Tailwind classes to its widgets from Python.
    './blog/forms.py',
  ],
  theme: {
    extend: {
      colors: {
        "secondary-container": "#acbfff",
        "surface-container-lowest": "#ffffff",
        "primary-fixed": "#dbe1ff",
        "error-container": "#ffdad6",
        "tertiary-container": "#bc4800",
        "on-tertiary-fixed-variant": "#7d2d00",
        "inverse-surface": "#2e3039",
        "on-primary-container": "#eeefff",
        "outline": "#737686",
        "primary-container": "#2563eb",
        "tertiary": "#943700",
        "on-primary-fixed-variant": "#003ea8",
        "secondary": "#495c95",
        "on-error-container": "#93000a",
        "on-surface": "#191b23",
        "tertiary-fixed-dim": "#ffb596",
        "on-secondary-fixed": "#00174b",
        "on-secondary-container": "#394c84",
        "surface-bright": "#faf8ff",
        "primary": "#004ac6",
        "secondary-fixed-dim": "#b4c5ff",
        "surface-container-high": "#e7e7f3",
        "secondary-fixed": "#dbe1ff",
        "surface-container-highest": "#e1e2ed",
        "surface-container-low": "#f3f3fe",
        "error": "#ba1a1a",
        "on-tertiary-container": "#ffede6",
        "surface-variant": "#e1e2ed",
        "inverse-primary": "#b4c5ff",
        "background": "#faf8ff",
        "on-primary-fixed": "#00174b",
        "surface": "#faf8ff",
        "outline-variant": "#c3c6d7",
        "on-secondary": "#ffffff",
        "surface-dim": "#d9d9e5",
        "on-tertiary": "#ffffff",
        "on-background": "#191b23",
        "on-error": "#ffffff",
        "on-tertiary-fixed": "#360f00",
        "on-secondary-fixed-variant": "#31447b",
        "surface-container": "#ededf9",
        "tertiary-fixed": "#ffdbcd",
        "surface-tint": "#0053db",
        "primary-fixed-dim": "#b4c5ff",
        "on-primary": "#ffffff",
        "on-surface-variant": "#434655",
        "inverse-on-surface": "#f0f0fb"
      },
      fontFamily: {
        headline: ['Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        label: ['Inter', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '1rem',
        lg: '2rem',
        xl: '3rem',
        full: '9999px',
      },
    },
  },
  plugins: [],
};
