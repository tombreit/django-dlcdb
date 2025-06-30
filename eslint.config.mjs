// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: CC0-1.0

import globals from 'globals'
import pluginJs from '@eslint/js'
import stylistic from '@stylistic/eslint-plugin'

/** @type {import('eslint').Linter.Config[]} */
export default [
  { languageOptions: { globals: globals.browser } },
  stylistic.configs['recommended-flat'],
  {
    plugins: {
      '@stylistic': stylistic,
    },
  },
]
