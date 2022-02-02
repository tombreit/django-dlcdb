{% load static %}

// Constants
const uuidFormField = document.getElementById('id_uuids');
const QRCODE_PREFIX = String("{{ qrcode_prefix }}");
const API_URL_DEVICE = '{{ request.scheme }}://{{ request.get_host }}/api/v2/devices/'
const STATE_BUTTON_PREFIX = 'state-btn-'
const ROW_UUID_PREFIX = 'tr-uuid-'

// helper functions
function isDlcdbQrCode(qrstring) {
    console.log("isDlcdbQrCoded")
    let re = new RegExp("^DLCDB[RD][0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
    return re.test(qrstring)
}

function getInfix(qrstring) {
    console.log("getInfix")
    let len_prefix = QRCODE_PREFIX.length
    console.log("len_prefix: " + len_prefix)

    let infix = qrstring.substring(len_prefix, len_prefix + 1)
    console.log("infix: " + infix)
    return infix
}

function getUnprefixedUuid(uuid) {
    console.log("getUnprefixedUuid")
    let re = new RegExp("^" + QRCODE_PREFIX + "[RD]")
    let result = uuid.replace(re, '')
    console.log("getUnprefixedUuid: " + result)
    return result
}

function QrCode(qrstring) {
    // check if result from scanner is a valid DLCDB QR code
    if ( !isDlcdbQrCode(qrstring)) return false

    this.uuid = getUnprefixedUuid(qrstring)
    this.infix = getInfix(qrstring)
    this.raw = qrstring

    return this
}


/// START JS DEVICE

// Result dict uuids_states_dict holds uuids and their correspondig states, e.g.:
// uuids_states_dict = {
//   uuid1: found,
//   uuid2: notfound,
//   uuid3: found,
//   ...
// }

const uuids_states_map = new Map();

// DEVICE: Constants
const DEVICE_STATE_UNKNOWN = "dev_state_unknown";
const DEVICE_STATE_FOUND = "dev_state_found";
const DEVICE_STATE_ADDED = "dev_state_added";
const DEVICE_STATE_NOTFOUND = "dev_state_notfound";


function getDeviceByUuid(uuid) {
    // console.log("getDeviceByUuid")
    let apiDeviceQuery = API_URL_DEVICE + uuid
    console.log("apiDeviceQuery: " + apiDeviceQuery)

    fetch(apiDeviceQuery)
    .then((response) => response.json())
    .then((data) => {
        console.log("fetch(apiDeviceQuery): ", data);
        addNewDeviceRow(data)
        // We do not trigger dev_state_found automatically, user must push button
        // manageUuid({uuid: uuid, state: DEVICE_STATE_ADDED});
    })
    .catch(function(error) {
        alert("fetch error: " + error)
        console.warn(error);
    })  
}

// DEVICE: live collection of matched elements
var btns = document.getElementsByClassName('state-trigger');
for (let btn of btns) {
    btn.addEventListener('click', btnClick, false);
}

// function update_found_devices_count(count) {
//     let count_elem = document.getElementById("found_devices_count")
//     count_elem.classList.add("blink");
//     count_elem.textContent = count;
// }

function btnClick() {
    console.log("=== btnClick =========")
    let this_btn = this;

    // If the clicked element doesn't have the right selector, bail
    if (!this_btn.classList.contains('state-trigger')) return;
    event.preventDefault();

    let this_btn_iconelem = this_btn.querySelector('.fas');
    let uuid = this_btn.id.replace(STATE_BUTTON_PREFIX, '')
    let row = this_btn.closest(".inventory_row")

    console.log("this_btn.id: " + uuid)

    if (row.classList.contains(DEVICE_STATE_ADDED)) {
        row.classList.remove(DEVICE_STATE_ADDED, "table-info")
        row.classList.add(DEVICE_STATE_FOUND, "table-success")
        this_btn_iconelem.className = "fas fa-check-square";
        manageUuid({uuid: uuid, state: DEVICE_STATE_FOUND_UNEXPECTED});
    } else if (row.classList.contains(DEVICE_STATE_UNKNOWN)) {
        row.classList.remove(DEVICE_STATE_UNKNOWN, "table-default")
        row.classList.add(DEVICE_STATE_FOUND, "table-success")
        this_btn_iconelem.className = "fas fa-check-square";
        manageUuid({uuid: uuid, state: DEVICE_STATE_FOUND});
    } else if (row.classList.contains(DEVICE_STATE_FOUND)) {
        row.classList.remove(DEVICE_STATE_FOUND, "table-success")
        row.classList.add(DEVICE_STATE_NOTFOUND, "table-danger")
        this_btn_iconelem.className = "fas fa-times-circle";
        manageUuid({uuid: uuid, state: DEVICE_STATE_NOTFOUND});
    } else if (row.classList.contains(DEVICE_STATE_NOTFOUND)) {
        row.classList.remove(DEVICE_STATE_NOTFOUND, "table-danger")
        row.classList.add(DEVICE_STATE_UNKNOWN, "table-default")
        this_btn_iconelem.className = "fas fa-question-circle";
        manageUuid({uuid: uuid, state: DEVICE_STATE_UNKNOWN});
    } else {
        console.log("[btnClick] This should never happen!")
    }
}

// function markRow({ uuid, state }) {
//     let search_id = ROW_UUID_PREFIX + uuid
//     let row = document.getElementById(search_id)

//     if ((row) && (state == DEVICE_STATE_FOUND)) {
//         console.log("row: " + row)
//         row.classList.remove(DEVICE_STATE_NOTFOUND, DEVICE_STATE_UNKNOWN)
//         row.classList.add(DEVICE_STATE_FOUND)
//     } else if ((row) && (state == DEVICE_STATE_NOTFOUND)) {
//         row.classList.remove(DEVICE_STATE_FOUND, DEVICE_STATE_UNKNOWN)
//         row.classList.add(DEVICE_STATE_NOTFOUND)
//     } else if ((row) && (state == DEVICE_STATE_FOUND_UNEXPECTED)) {
//         row.classList.remove(DEVICE_STATE_FOUND_UNEXPECTED)
//         row.classList.add(DEVICE_STATE_FOUND)
//     } else {
//         console.log("Not yet in this room!")
//         let newDevice = getDeviceByUuid(uuid)
//         console.log("Adding newDevice: ", newDevice)
//     }
// }

function deviceRowTemplate(device){
    return `
        <tr id="${ROW_UUID_PREFIX}${device.uuid}" class="inventory_row ${DEVICE_STATE_UNKNOWN} table-info">
            <td>
                ${device.edv_id}
                <br>
                <span class="badge badge-pill badge-warning small">
                    ADDED
                </span>
            </td>
            <td>
                ${device.manufacturer}, ${device.series}
            </td>
            <td>
                <button 
                    type="button"
                    class="state-trigger btn btn-outline-secondary" 
                    id="${STATE_BUTTON_PREFIX}${device.uuid}"
                >
                    <i class="fas fa-question-circle {# fa-plus-square #}"></i>
                </button>
            </td>
            <td>
            </td>
            <td>
                <abbr title="Not Implemented">501</abbr>
            </td>
        </tr>
    `;
 }

function addNewDeviceRow(device) {
    console.log("[addNewDeviceRow] for device: ", device)
    // console.log(typeof device)
    // console.log(device.length)

    // If no device is selected, do nothing
    if(device.length) {
        alert("Select device first...")
        return;
    }

    let tableTbody = document.getElementById("devices-table-tbody");
    let newRow = deviceRowTemplate(device)
    tableTbody.insertAdjacentHTML( 'afterbegin', newRow )

    let query = STATE_BUTTON_PREFIX + device.uuid
    // console.log(query)
    let stateButton = document.getElementById(query);
    // console.log("stateButton: ", stateButton)
    stateButton.addEventListener('click', btnClick, false);

    $('#id_device').val(null).trigger('change');

}

function manageUuid({ uuid, state }) {
    console.log("uuidFormField: " + uuidFormField.getAttribute('value'))
    console.log("manageUuid: uuid: " + uuid + " state: " + state);

    if (( state == DEVICE_STATE_FOUND ) || ( state == DEVICE_STATE_NOTFOUND) || ( state == DEVICE_STATE_UNKNOWN)) {
        uuids_states_map.set(uuid, state);
        // markRow({uuid: uuid, state: state});
        // update_found_devices_count(uuids_states_map.size);

        let serialized_uuids_states_map = JSON.stringify(Object.fromEntries(uuids_states_map));
        uuidFormField.setAttribute('value', serialized_uuids_states_map);
    } else {
        alert("[manageUuid] This should never happen! uuid: " + uuid + " state: " + state + "Please contact t.breitner@csl.mpg.de");
    }
}

// Add new device via form
const addDeviceButton = document.querySelector("#add-device-button");

addDeviceButton.addEventListener("click", function(event) {
    let select2SelectedOption = $('#id_device').select2('data')[0].id;
    // console.log("select2SelectedOption: ", select2SelectedOption)
    console.log("[addDeviceButton] adding device: ", select2SelectedOption)
    let newDevice = getDeviceByUuid(select2SelectedOption)
    event.preventDefault();
}, false);

/// END JS DEVICE


/// START JS ROOM
$('#switch_room_modal .modal-footer button').on('click', function (event) {
    let clicked_button = $(event.target); // The clicked button
    let parent = clicked_button.closest(".modal")
    let uuid = parent[0].dataset.uuid

    if (clicked_button[0].id === "change_room") {
        location = "{% url 'inventory:inventorize-room' '99999999-9999-9999-9999-999999999999' %}".replace(/99999999-9999-9999-9999-999999999999/, uuid.toString());
    }
});

function gotoRoom(uuid) {
    const el = document.querySelector('#switch_room_modal');
    el.dataset.uuid = uuid; 
    $('#switch_room_modal').modal('show');
}

/// END JS ROOM


// SCANNER
{% comment %}
import QrScanner from "{% static 'inventory/qr-scanner.min.js' %}";
QrScanner.WORKER_PATH = "{% static 'inventory/qr-scanner-worker.min.js' %}";

const video = document.getElementById('qr-video');
const camHasCamera = document.getElementById('cam-has-camera');
const camQrResult = document.getElementById('cam-qr-result');
const camQrResultTimestamp = document.getElementById('cam-qr-result-timestamp');

function setResult(label, result) {
    label.textContent = result;
    camQrResultTimestamp.textContent = new Date().toString();
    label.style.color = 'teal';
    clearTimeout(label.highlightTimeout);
    label.highlightTimeout = setTimeout(() => label.style.color = 'inherit', 100);
}

// SCANNER Continous Web Cam Scanning
QrScanner.hasCamera().then(hasCamera => camHasCamera.textContent = hasCamera);

const qrScanner = new QrScanner(video, result => {
    // console.log('[i] Raw decoded qr code:', result);

    result = result.trim();
    let QrObj = new QrCode(result)
    if (!QrObj) return;

    if (QrObj.infix === 'D') {
        // Trigger DEVICE related tasks
        manageUuid({uuid: QrObj.uuid, state: DEVICE_STATE_FOUND});
    } else if (QrObj.infix === 'R') {
        // Trigger ROOM related tasks
        console.log("triggering openRoom...")
        gotoRoom(QrObj.uuid);
    } else {
        alert("INFIX NOT GIVEN OR NOT KNOWN!")
        return;
    }

});
qrScanner.start();
{% endcomment %}
