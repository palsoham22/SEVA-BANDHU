



/////////////////////////////////////////////////////
// MAP
/////////////////////////////////////////////////////

const map = L.map('map').setView([22.5726, 88.3639], 13);

L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
        attribution: '© OpenStreetMap contributors'
    }
).addTo(map);

/////////////////////////////////////////////////////
// TECHNICIAN MARKER
/////////////////////////////////////////////////////

const technicianIcon = L.icon({

    iconUrl:
    'https://cdn-icons-png.flaticon.com/512/744/744465.png',

    iconSize: [40, 40],

    iconAnchor: [20, 20]

});

const technicianMarker = L.marker(

    [0, 0],

    {

        icon: technicianIcon,

        zIndexOffset: 1000

    }

)

.addTo(map)

.bindPopup("🚗 Technician");

/////////////////////////////////////////////////////
// CUSTOMER LOCATION
/////////////////////////////////////////////////////

const customerLat = parseFloat(
    "{{ service_request.customer_latitude }}"
);

const customerLng = parseFloat(
    "{{ service_request.customer_longitude }}"
);

/////////////////////////////////////////////////////
// CUSTOMER MARKER
/////////////////////////////////////////////////////

const customerMarker = L.marker(

    [customerLat, customerLng]

)

.addTo(map)

.bindPopup("🏠 Customer Location");

/////////////////////////////////////////////////////
// ROUTE CONTROL
/////////////////////////////////////////////////////

let routeControl = L.Routing.control({
createMarker: function() {

    return null;

},
    waypoints: [
L.latLng(22.5726, 88.3639),
L.latLng(customerLat, customerLng)
    ],

    routeWhileDragging: false,

    addWaypoints: false,

    draggableWaypoints: false,

    fitSelectedRoutes: true,

    show: false

})

.addTo(map);
/////////////////////////////////////////////////////
// ETA + DISTANCE
/////////////////////////////////////////////////////

routeControl.on(

    'routesfound',

    function(e) {

        const route =
        e.routes[0];

        const distance =
        (
            route.summary.totalDistance / 1000
        ).toFixed(2);

        const time =
        Math.round(
            route.summary.totalTime / 60
        );

        document.getElementById(
            'journey-info'
        ).innerHTML =

        `🚗 ${time} mins away • 📍 ${distance} km remaining`;

    }

);
/////////////////////////////////////////////////////
// WEBSOCKET
/////////////////////////////////////////////////////

const wsProtocol =
    window.location.protocol === "https:"
    ? "wss://"
    : "ws://";

const socket = new WebSocket(

    wsProtocol +
    window.location.host +
    '/ws/tracking/{{ service_request.id }}/'

);

/////////////////////////////////////////////////////
// SOCKET CONNECTED
/////////////////////////////////////////////////////

socket.onopen = function() {

   document.getElementById(
    'tracking-status'
).innerHTML =

'🟢 Technician Connected';
};

/////////////////////////////////////////////////////
// RECEIVE LIVE GPS
/////////////////////////////////////////////////////

socket.onmessage = function(event) {

    try {

        const data = JSON.parse(event.data);

        console.log("📩 LIVE DATA:", data);

        /////////////////////////////////////////////////////
        // LIVE LOCATION UPDATE
        /////////////////////////////////////////////////////

        if (data.type === "location_update") {

            const lat = parseFloat(data.latitude);

            const lng = parseFloat(data.longitude);

            console.log("📍 MOVING TO:", lat, lng);

            /////////////////////////////////////////////////////
            // MOVE MARKER
            /////////////////////////////////////////////////////

            technicianMarker.setLatLng([lat, lng]);

            routeControl.setWaypoints([

                L.latLng(lat, lng),
L.latLng(customerLat, customerLng)

            ]);

            /////////////////////////////////////////////////////
            // MOVE MAP CAMERA
            /////////////////////////////////////////////////////

            map.panTo([lat, lng]);

            /////////////////////////////////////////////////////
            // UPDATE TEXT
            /////////////////////////////////////////////////////

            
        }

    } catch (e) {

        console.error("❌ Tracking Error:", e);

    }
};

/////////////////////////////////////////////////////
// SOCKET ERRORS
/////////////////////////////////////////////////////

socket.onerror = function(error) {

    console.error("❌ SOCKET ERROR:", error);

};

socket.onclose = function() {

    document.getElementById(
    'tracking-status'
).innerHTML =

'🔴 Technician Disconnected';
};

