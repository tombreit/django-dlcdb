// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: CC0-1.0

import globals from 'globals'
import stylistic from '@stylistic/eslint-plugin'

/** @type {import('eslint').Linter.Config[]} */
export default [
  { ignores: ['**/dist/'] },
  { languageOptions: { globals: globals.browser } },
  stylistic.configs.recommended,
]
