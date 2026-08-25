

console.log("ðŸ”¥ JS LOADED");

// Get the current technician's service category
let technicianServiceCategory = "{{ technician.service_category }}";
console.log("ðŸ“‹ Technician service category:", technicianServiceCategory);

function openProfileModal() {
    document.getElementById('profileModal').classList.add('show');
}

function closeProfileModal() {
    document.getElementById('profileModal').classList.remove('show');
}

// Close modal when clicking outside
window.onclick = function(event) {
    var modal = document.getElementById('profileModal');
    if (event.target == modal) {
        modal.classList.remove('show');
    }
}

// WebSocket connection
const socket = new WebSocket(
    "ws://" + window.location.host + "/ws/requests/"
);

socket.onopen = function() {
    console.log("WebSocket Connected âœ…");
};

console.log("ðŸ§  Technician Service:", technicianServiceCategory);

socket.onmessage = function(event) {

    try {

        console.log("ðŸ”¥ RAW WS:", event.data);

        const data = JSON.parse(event.data);

        console.log("ðŸ“© WS EVENT:", data);

        // ðŸ”¥ NEW REQUEST
        if (data.content && data.content.type === "new_request") {

            addNotificationCard(data.content);
        }

        // ðŸ”¥ REMOVE REQUEST
        else if (data.type === "notification_removed") {

            removeNotificationByRequest(data.request_id);
        }

    } catch (e) {

        console.error("âŒ WebSocket Error:", e);

    }
};

socket.onerror = function(error) {
    console.log("WebSocket Error:", error);
};

socket.onclose = function(event) {
    console.log("WebSocket closed:", event.code);
};

function acceptRequest(requestId, notificationId) {

    console.log("ðŸš€ Accept clicked:", requestId, notificationId);

    fetch(`/technician/accept-request/${requestId}/`, {

        method: "POST",

        headers: {
            "X-CSRFToken": getCSRFToken(),
            "Content-Type": "application/json"
        }

    })

    .then(res => res.json())

    .then(data => {

        console.log("âœ… RESPONSE:", data);

        if (data.status === "success") {

            const card = document.getElementById(`notification-${notificationId}`);

            if (card) {
                card.remove();
            }

            incrementDashboardCounts();

            alert("âœ… Request Accepted");

        } else {

            alert("âŒ " + (data.message || "Already taken"));

        }

    })

    .catch(err => {

        console.error("âŒ ERROR:", err);

    });
}

function incrementDashboardCounts() {

    const total = document.getElementById('totalJobsCount');
    const assigned = document.getElementById('assignedJobsCount');

    if (total) {
        total.textContent = parseInt(total.textContent) + 1;
    }

    if (assigned) {
        assigned.textContent = parseInt(assigned.textContent) + 1;
    }
}

function dismissNotification(notificationId) {

    fetch(`/technician/dismiss-notification/${notificationId}/`, {

        method: "POST",

        headers: {
            "X-CSRFToken": getCSRFToken(),
            "Content-Type": "application/json"
        }

    })

    .then(res => res.json())

    .then(data => {

        if (data.status === "success") {

            const card = document.getElementById(`notification-${notificationId}`);

            if (card) {
                card.remove();
            }

        }

    })

    .catch(err => {

        console.error(err);

    });
}

function addNotificationCard(data) {

    console.log("ðŸ”¥ ADDING CARD:", data);

    const container = document.getElementById('notificationContainer');

    if (!container) {
        console.error("âŒ notificationContainer NOT FOUND");
        return;
    }

    const card = document.createElement('div');

    card.className = "notification-card";

    card.id = `notification-live-${data.request_id}`;

    card.innerHTML = `
        <div class="notification-title">
            ${data.service_category}
        </div>

        <div class="notification-info">
            <p><b>City:</b> ${data.city}</p>
            <p><b>Date:</b> ${data.preferred_date}</p>
            <p><b>Time:</b> ${data.preferred_time}</p>
            <p><b>Priority:</b> ${data.priority}</p>
        </div>

        <div class="notification-actions">

            <button
                onclick="location.reload()"
                class="notification-btn btn-view">

                View

            </button>

        </div>
    `;

    container.prepend(card);

    updateNotificationCount();
}

function updateNotificationCount() {

    const cards = document.querySelectorAll('.notification-card');

    const countElement = document.getElementById('notificationCount');

    if (countElement) {

        countElement.textContent = cards.length;
    }
}

function removeNotificationByRequest(requestId) {

    const buttons = document.querySelectorAll('[data-request-id]');

    buttons.forEach(button => {

        if (button.dataset.requestId == requestId) {

            const card = button.closest('.notification-card');

            if (card) {
                card.remove();
            }
        }
    });
}

function getCSRFToken() {
    return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
}

function getCookie(name) {

    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {

        const cookies = document.cookie.split(';');

        for (let i = 0; i < cookies.length; i++) {

            const cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === (name + '=')) {

                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));

                break;
            }
        }
    }

    return cookieValue;
}

console.log("ðŸ”¥ THIS FILE IS LOADED");

