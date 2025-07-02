// SPDX-FileCopyrightText: 2025 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

import TomSelect from 'tom-select'

export function initInventorizeRoomDetail() {
  // Page-specific code for inventorize_room_detail only
  // TODO: Move this to a separate module
  function inventorizeRoomDetail() {
    // Initialize TomSelect on the "device" field
    const deviceSelect = document.getElementById('id_device')
    if (deviceSelect) {
      new TomSelect(deviceSelect, {
        create: false,
        maxItems: 1,
        closeAfterSelect: true,
      })
    }

    // Filter table functionality
    const devicesTable = document.querySelector('#devices-table tbody')
    const devicesTableSearchInput = document.querySelector('#search-table-input')
    const devicesTableSearchButton = document.getElementById('search-table-button')

    // Display current device count in the search button
    function updateDeviceTableCounter() {
      if (!devicesTableSearchButton || !devicesTable) return
      const rows = Array.from(devicesTable.rows)
      const visibleRows = rows.filter(row => row.style.display !== 'none')
      // Find the <i> inside the button and set the counter as a badge
      let counterSpan = devicesTableSearchButton.querySelector('.table-counter-badge')
      if (!counterSpan) {
        counterSpan = document.createElement('span')
        counterSpan.className = 'table-counter-badge badge bg-secondary ms-2'
        devicesTableSearchButton.appendChild(counterSpan)
      }
      counterSpan.textContent = visibleRows.length
    }

    if (devicesTable && devicesTableSearchInput && devicesTableSearchButton) {
      function filterDeviceTable() {
        const query = devicesTableSearchInput.value.toLowerCase()
        const rows = devicesTable.rows

        for (const row of rows) {
          let matchInRow = false
          for (const cell of row.cells) {
            let cellContent = cell.textContent || cell.innerText
            cellContent = cellContent.toLowerCase()
            if (cellContent.includes(query)) {
              matchInRow = true
              break
            }
          }
          row.style.display = matchInRow ? 'table-row' : 'none'
        }
        updateDeviceTableCounter()
      }
      devicesTableSearchInput.addEventListener('keyup', filterDeviceTable)
      // Initial counter update
      updateDeviceTableCounter()
    }

    // Keyboard shortcut: Ctrl+Alt+S to submit the inventory form
    const inventoryForm = document.getElementById('inventory-save-form-alt-s')
    if (inventoryForm) {
      document.addEventListener('keydown', function (e) {
        if (e.ctrlKey && e.altKey && (e.key === 's' || e.key === 'S')) {
          // Only trigger if the form is visible and not in a modal/hidden
          if (document.activeElement.tagName !== 'TEXTAREA' && document.activeElement.tagName !== 'INPUT') {
            e.preventDefault()
            if (inventoryForm.requestSubmit) {
              inventoryForm.requestSubmit()
            }
            else {
              inventoryForm.submit()
            }
          }
        }
      })
    }
  }

  // Check if we're on the inventorize_room_detail page via a data attribute
  if (document.body.dataset.page === 'inventorize-room-detail') {
    inventorizeRoomDetail()
  }
}
