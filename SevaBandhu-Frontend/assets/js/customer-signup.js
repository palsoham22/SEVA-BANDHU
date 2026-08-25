

function getCookie(name) {

    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {

        const cookies = document.cookie.split(';');

        for (let i = 0; i < cookies.length; i++) {

            const cookie = cookies[i].trim();

            if (

                cookie.substring(

                    0,

                    name.length + 1

                ) === (name + '=')

            ) {

                cookieValue = decodeURIComponent(

                    cookie.substring(
                        name.length + 1
                    )
                );

                break;

            }

        }

    }

    return cookieValue;
}

window.verifyEmail = async function() {
    const email = document.getElementById("email").value;

    if (!email) {
        alert("Please enter email first");
        return;
    }

    const statusEl = document.getElementById("verify-status");
    statusEl.innerText = "⏳ Sending verification email...";

    try {
        const response = await fetch("/send-verification-email/", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (response.ok && data.status === "success") {
            statusEl.innerText = data.message || "📩 Verification email sent successfully.";
            document.getElementById("verify-btn").disabled = true;
            document.getElementById("verify-btn").innerText = "Sent";
        } else {
            statusEl.innerText = data.message || "❌ Failed to send verification email.";
        }
    } catch (error) {
        console.error(error);
        statusEl.innerText = error?.message || "❌ Failed to send verification email.";
    }
}

