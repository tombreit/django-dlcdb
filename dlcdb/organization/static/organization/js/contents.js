// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Settings › Organization (organization/branding.html): a link of the table of
// contents opens the closed card it points to before the browser scrolls there.
// Loaded as the media of BrandingForm.
for (const link of document.querySelectorAll('[data-contents] a[href^="#"]')) {
  link.addEventListener('click', () => {
    document.querySelector(link.hash).open = true
  })
}
