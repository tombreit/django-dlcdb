// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// The buttons next to a form's select that open the selected object or add a
// new one (see theme/related.py and theme/widgets/tom_select.html).
//
// All listeners are delegated at document level, so forms swapped in by HTMX
// need no setup.

// The detail button follows the selection. Its template is the detail URL of
// pk 0; only the path holds the pk, the query holds the URL-encoded ?next=.
function detailHref(template, pk) {
  const [path, query] = template.split('?')
  const href = path.replace('/0/', `/${encodeURIComponent(pk)}/`)
  return query === undefined ? href : `${href}?${query}`
}

document.addEventListener('change', (event) => {
  const select = event.target
  if (select.tagName !== 'SELECT') return
  const link = select.closest('[data-related-links]')?.querySelector('[data-href-template]')
  if (!link) return

  if (select.value) {
    link.href = detailHref(link.dataset.hrefTemplate, select.value)
    link.classList.remove('disabled')
    link.removeAttribute('aria-disabled')
    link.removeAttribute('tabindex')
  }
  else {
    link.removeAttribute('href')
    link.classList.add('disabled')
    link.setAttribute('aria-disabled', 'true')
    link.setAttribute('tabindex', '-1')
  }
})

// The links leave the form, and with it whatever the user typed. The form's
// entries are compared with a snapshot taken when the user first enters it,
// after TomSelect and the page's own scripts have set it up; their change
// events cannot tell setup from input. Files compare by name and size.
const snapshots = new WeakMap()

function entries(form) {
  return JSON.stringify(
    [...new FormData(form)].map(([name, value]) => [
      name,
      value instanceof File ? `${value.name}:${value.size}` : value,
    ]),
  )
}

document.addEventListener('focusin', (event) => {
  const form = event.target.closest('form')
  if (form && !snapshots.has(form) && form.querySelector('[data-related-link]')) {
    snapshots.set(form, entries(form))
  }
})

document.addEventListener('click', (event) => {
  const link = event.target.closest('[data-related-link]')
  const form = link?.closest('form')
  if (!form || !link.hasAttribute('href')) return

  // A form re-rendered after a failed save holds nothing but unsaved input.
  const unsaved = link.hasAttribute('data-unsaved')
    || (snapshots.has(form) && entries(form) !== snapshots.get(form))
  if (unsaved && !window.confirm(link.dataset.confirm)) {
    event.preventDefault()
  }
})
