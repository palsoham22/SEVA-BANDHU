

/////////////////////////////////////////////////////
// FIREBASE IMPORTS
/////////////////////////////////////////////////////

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";

import {
    getAuth,
    GoogleAuthProvider,
    signInWithPopup
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

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
// INITIALIZE FIREBASE
/////////////////////////////////////////////////////

const app = initializeApp(firebaseConfig);

const auth = getAuth(app);

const provider = new GoogleAuthProvider();

/////////////////////////////////////////////////////
// GOOGLE SIGNUP BUTTON
/////////////////////////////////////////////////////

window.googleSignup = async function() {

    try {

        const result = await signInWithPopup(auth, provider);

        const user = result.user;

        console.log("Ã¢Å“â€¦ GOOGLE USER:", user);

        const name = user.displayName;
        const email = user.email;
        const photo = user.photoURL;

        localStorage.setItem("google_name", name);
        localStorage.setItem("google_email", email);
        localStorage.setItem("google_photo", photo);

        alert("Google Login Success Ã°Å¸ËœÅ½Ã°Å¸â€Â¥");

    } catch (error) {

        console.error("Ã°Å¸â€Â¥ FULL FIREBASE ERROR:", error);

        alert(error.message);
    }
};

