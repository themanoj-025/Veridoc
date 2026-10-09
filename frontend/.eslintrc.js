// ESLint 8 eslintrc-style config assembled directly from @next/eslint-plugin-next.
// Replaces the old "extends": "next/core-web-vitals" which is no longer resolvable:
// eslint-config-next@16 is exports-only (no main entry) and its plugin objects
// crash eslintrc's schema validator when embedded. Only rule maps are spread;
// plugin objects are referenced by string name. Matches the original intent
// (core-web-vitals = @next/next recommended + core-web-vitals rules, react-hooks).

const nextPlugin = require('@next/eslint-plugin-next');

module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  plugins: ['@next/next', 'react-hooks'],
  settings: {
    react: { version: 'detect' },
  },
  rules: {
    ...nextPlugin.configs.recommended.rules,
    ...nextPlugin.configs['core-web-vitals'].rules,
    // Exactly what next/core-web-vitals enables for react-hooks (v7's
    // recommended block adds aggressive new rules like set-state-in-effect
    // that the original config never enforced)
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    // Project-specific relaxations (carried over from the old eslintrc.json)
    'react/no-unescaped-entities': 'off',
    '@next/next/no-page-custom-font': 'off',
  },
  ignorePatterns: ['node_modules/', '.next/', 'out/', 'playwright-report/', 'test-results/'],
};
