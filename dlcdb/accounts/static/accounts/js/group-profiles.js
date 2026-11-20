// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// The group profiles' buttons (accounts/groups/detail.html), loaded as the
// media of GroupForm: a button ticks its profile's permissions in the group
// form; Save keeps them, like any tick.
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-profile-permissions]')
  if (!button) return

  const checkboxes = button.dataset.profilePermissions.split(',')
    .map(pk => document.getElementById(`permission-${pk}`))
    .filter(Boolean)
  for (const checkbox of checkboxes) checkbox.checked = true
  // The permissions card starts closed: open it, to show the ticks.
  const card = checkboxes[0]?.closest('details.card')
  if (card) card.open = true

  // The ticks are unsaved input, though the button sits outside the form: its
  // leaving links ask first (theme/assets/js/related-links.js).
  checkboxes[0]?.form.querySelectorAll('[data-related-link]').forEach(link => link.setAttribute('data-unsaved', ''))
})
