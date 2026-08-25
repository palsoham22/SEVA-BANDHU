

/////////////////////////////////////////////////////
// WEBSOCKET
/////////////////////////////////////////////////////

let trackingWatchId = null;
let trackingSocket = null;
let trackingStarted = false;

function startJourney(jobId) {

    fetch(`/technician/start-tracking/${jobId}/`, {

        method: "POST",

        headers: {
            "X-CSRFToken": getCSRFToken(),
            "Content-Type": "application/json"
        }

    })

    .then(res => res.json())

    .then(data => {

    if (data.status === "success") {

        alert("ðŸš€ Journey Started");

        /////////////////////////////////////////////////////
        // FORCE GPS ACCESS FIRST
        /////////////////////////////////////////////////////

        navigator.geolocation.getCurrentPosition(

            (position) => {

                console.log(
                    "âœ… GPS PERMISSION GRANTED"
                );

                /////////////////////////////////////////////////////
                // NOW START LIVE TRACKING
                /////////////////////////////////////////////////////

                startLiveTracking(jobId);

            },

            (error) => {

                console.error(
                    "âŒ GPS PERMISSION DENIED:",
                    error
                );

                alert(
                    "Please allow location permission."
                );
            }

        );

    }

    });

}

function startLiveTracking(jobId) {

    const wsProtocol =
    window.location.protocol === "https:"
    ? "wss://"
    : "ws://";

trackingSocket = new WebSocket(
    wsProtocol +
    window.location.host +
    `/ws/tracking/${jobId}/`
);

    trackingSocket.onopen = function() {

        console.log("âœ… TRACKING SOCKET CONNECTED");

        trackingWatchId = navigator.geolocation.watchPosition(

            (position) => {

                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                console.log("ðŸ“ LIVE LOCATION:", lat, lng);

                if (trackingSocket.readyState !== WebSocket.OPEN) {

                    console.log("âŒ SOCKET NOT READY");

                    return;
                }

                trackingSocket.send(JSON.stringify({

                    type: 'live_location',

                    request_id: jobId,

                    latitude: lat,

                    longitude: lng

                }));

            },

            (error) => console.error("âŒ GPS ERROR:", error),

            {
                enableHighAccuracy: true,
                maximumAge: 1000,
                timeout: 10000
            }

        );

    };

}

/////////////////////////////////////////////////////
// GET CSRF TOKEN
/////////////////////////////////////////////////////

function getCSRFToken() {

    return document.querySelector(
        '[name=csrfmiddlewaretoken]'
    ).value;

}

