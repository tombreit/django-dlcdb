// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// The settings page's filter (theme/settings.html): it keeps the entries whose
// label, description or hidden search terms contain every typed word, and hides
// the groups left without one. Entries are taken out of their list rather than
// hidden: Bootstrap's list-group draws its borders by :first-child and siblings.
const filter = document.getElementById('settings-filter')
const noMatch = document.getElementById('settings-no-match')
const groups = [...document.querySelectorAll('[data-settings-group]')].map((section) => {
  const list = section.querySelector('.list-group')
  return { section, list, entries: [...list.children] }
})

filter.addEventListener('input', () => {
  const words = filter.value.toLowerCase().split(/\s+/).filter(Boolean)
  let found = 0
  for (const { section, list, entries } of groups) {
    const matching = entries.filter((entry) => {
      const text = `${entry.textContent} ${entry.dataset.searchTerms}`.toLowerCase()
      return words.every(word => text.includes(word))
    })
    list.replaceChildren(...matching)
    section.hidden = matching.length === 0
    found += matching.length
  }
  noMatch.hidden = found > 0
})
