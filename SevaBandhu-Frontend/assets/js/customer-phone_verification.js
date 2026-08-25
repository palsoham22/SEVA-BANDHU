

import { initializeApp }
from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";

import {

    getAuth,

    RecaptchaVerifier,

    signInWithPhoneNumber

}
from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
/////////////////////////////////////////////////////
// FIREBASE CONFIG
/////////////////////////////////////////////////////

const firebaseConfig = {
    apiKey: "{{ firebase_config.api_key|escapejs }}",
    authDomain: "{{ firebase_config.auth_domain|escapejs }}",
    projectId: "{{ firebase_config.project_id|escapejs }}",
    storageBucket: "{{ firebase_config.storage_bucket|escapejs }}",
    messagingSenderId: "{{ firebase_config.messaging_sender_id|escapejs }}",
    appId: "{{ firebase_config.app_id|escapejs }}"
};

/////////////////////////////////////////////////////
// INITIALIZE
/////////////////////////////////////////////////////

const app = initializeApp(firebaseConfig);

const auth = getAuth(app);

window.recaptchaVerifier =
new RecaptchaVerifier(

    auth,

    'recaptcha-container',

    {
        size: 'invisible'
    }

);

window.sendOTP = function() {

    const phoneNumber =
        document.getElementById(
            "phone"
        ).value;

    const appVerifier =
        window.recaptchaVerifier;

    signInWithPhoneNumber(

        auth,

        phoneNumber,

        appVerifier

    )

    .then((confirmationResult) => {

        window.confirmationResult =
            confirmationResult;

        alert("OTP Sent Ã°Å¸ËœÅ½Ã°Å¸â€Â¥");

    })

    .catch((error) => {

        alert(error.message);

    });
}

window.verifyOTP = function() {

    const code =
        document.getElementById(
            "otp"
        ).value;

    window.confirmationResult.confirm(code)

    .then((result) => {

        alert("Phone Verified Ã°Å¸ËœÅ½Ã°Å¸â€Â¥");

        const phone = document.getElementById('phone').value || '';
        const csrftoken = getCookie('csrftoken');

        fetch('/customer/phone-verify-complete/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({
                phone: phone
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.href = '/customer/login/';
            } else {
                alert('Verification succeeded locally but server update failed: ' + (data.message || ''));
            }
        })
        .catch(err => {
            console.error(err);
            alert('Verification succeeded locally but server update failed. Redirecting to login.');
            window.location.href = '/customer/login/';
        });

    })

    .catch((error) => {

        alert('Invalid OTP');

    });
}

/////////////////////////////////////////////////////
// CHECK AUTH USER
/////////////////////////////////////////////////////


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
