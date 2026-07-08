// SPDX-FileCopyrightText: 2025 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Bootstrap is provided as window.bootstrap by the theme bundle (theme.js),
// which is loaded before this bundle. htmx (also bundled in theme.js) dispatches
// real bubbling DOM events, so plain addEventListener on body is sufficient here.

export function getJsVars() {
  const el = document.getElementById('js_vars')
  if (!el) return {}
  try {
    return JSON.parse(el.textContent)
  }
  catch {
    return {}
  }
}

export function getPage() {
  return document.querySelector('[data-page]')?.dataset.page ?? ''
}

export function initModal() {
  const noteModalElem = document.getElementById('htmx-note-modal')
  if (noteModalElem) {
    const modal = new window.bootstrap.Modal(noteModalElem)
    document.body.addEventListener('htmx:afterSwap', (e) => {
      if (e.detail.target.id === 'dialog') {
        modal.show()
      }
    })
    document.body.addEventListener('htmx:beforeSwap', (e) => {
      if (e.detail.target.id === 'dialog' && !e.detail.xhr.response) {
        modal.hide()
        e.detail.shouldSwap = false
      }
    })
    noteModalElem.addEventListener('hidden.bs.modal', () => {
      document.getElementById('dialog').innerHTML = ''
    })
  }
}

export function initToast() {
  const toastElement = document.getElementById('toast')
  if (toastElement) {
    const toastBody = document.getElementById('toast-body')
    const toast = new window.bootstrap.Toast(toastElement, { delay: 2000 })
    document.body.addEventListener('showMessage', (e) => {
      toastBody.innerText = e.detail.value
      toast.show()
    })
  }
}
