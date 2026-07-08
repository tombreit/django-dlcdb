// SPDX-FileCopyrightText: 2024 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

import { getJsVars } from './ui.js'

function updateQrSwitch(state) {
  const qrToggleUrl = getJsVars().qrToggleUrl
  const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value
  fetch(qrToggleUrl, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken,
    },
    body: JSON.stringify({ qrScanner: state }),
  })
    .then(response => response.json())
    .then(response => console.log(JSON.stringify(response)))
}

export function initQrToggle() {
  const qrSwitcherCheckbox = document.getElementById('qr-toggle')

  if (qrSwitcherCheckbox) {
    qrSwitcherCheckbox.addEventListener('change', function () {
      if (this.checked) {
        console.log('qrSwitcherCheckbox is checked!')
        updateQrSwitch(1)
      }
      else {
        console.log('qrSwitcherCheckbox is unchecked!')
        updateQrSwitch(0)
      }
      if (confirm('Reload page to apply QR toggle changes?')) {
        location.reload()
      }
    })
  }
}
