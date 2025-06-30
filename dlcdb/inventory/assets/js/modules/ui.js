// SPDX-FileCopyrightText: 2025 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

import * as bootstrap from 'bootstrap'
import htmx from 'htmx.org'

export function initModal() {
  const noteModalElem = document.getElementById('htmx-note-modal')
  if (noteModalElem) {
    const modal = new bootstrap.Modal(noteModalElem)
    htmx.on('htmx:afterSwap', (e) => {
      if (e.detail.target.id === 'dialog') {
        modal.show()
      }
    })
    htmx.on('htmx:beforeSwap', (e) => {
      if (e.detail.target.id === 'dialog' && !e.detail.xhr.response) {
        modal.hide()
        e.detail.shouldSwap = false
      }
    })
    htmx.on('hidden.bs.modal', () => {
      document.getElementById('dialog').innerHTML = ''
    })
  }
}

export function initToast() {
  const toastElement = document.getElementById('toast')
  if (toastElement) {
    const toastBody = document.getElementById('toast-body')
    const toast = new bootstrap.Toast(toastElement, { delay: 2000 })
    htmx.on('showMessage', (e) => {
      toastBody.innerText = e.detail.value
      toast.show()
    })
  }
}
