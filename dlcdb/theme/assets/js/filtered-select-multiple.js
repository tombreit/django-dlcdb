// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// The two lists of theme.widgets.FilteredSelectMultipleWidget, available and
// chosen. A bundle of its own, loaded only through the widget's Media.

import { FilteredSelectMultiple, bootstrap5Theme } from 'filtered-select-multiple-widget'

const theme = {
  ...bootstrap5Theme,
  // Below md the lists stack, with the buttons in a row between them.
  container: 'd-flex flex-column flex-md-row gap-3',
  // Both panes get column, besides their own class.
  column: 'd-flex flex-column flex-fill',
  controls: 'd-flex flex-row flex-wrap flex-md-column justify-content-center gap-2',
  button: `${bootstrap5Theme.button} text-nowrap`,
}

document.querySelectorAll('select[data-filtered-select-multiple]').forEach((select) => {
  // The widget's texts, translated by Django.
  const text = JSON.parse(select.dataset.filteredSelectMultiple)
  new FilteredSelectMultiple(select, { theme, text })
})
