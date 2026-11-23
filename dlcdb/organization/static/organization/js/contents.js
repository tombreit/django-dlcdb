// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Settings › Organization (organization/branding.html): its cards start closed.
// A link of the table of contents opens the card it points to before the
// browser scrolls there, and so does the page's own #card. Loaded as the media
// of BrandingForm.
const openCard = (id) => {
  const card = document.getElementById(id)
  if (card instanceof HTMLDetailsElement) {
    card.open = true
  }
}

openCard(location.hash.slice(1))
for (const link of document.querySelectorAll('[data-contents] a[href^="#"]')) {
  link.addEventListener('click', () => openCard(link.hash.slice(1)))
}
