;(function () {

function updateQrSwitch(state) {
    console.log("state: ", state)
    fetch("{% url 'inventory:update-qrtoggle' %}", {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}',
        },
        body: JSON.stringify({ "qrScanner": state })
        })
        .then(response => response.json())
        .then(response => console.log(JSON.stringify(response)))
}

const qrSwitcherCheckbox = document.getElementById('qr-toggle');

qrSwitcherCheckbox.addEventListener('change', function() {
    if (this.checked) {
    console.log('qrSwitcherCheckbox is checked!');
    updateQrSwitch(1)
    } else {
    console.log('qrSwitcherCheckbox is unchecked!');
    updateQrSwitch(0)
    }
});

})()