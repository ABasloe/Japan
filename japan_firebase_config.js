/*
 * Firebase web configuration for the shared Japan itinerary.
 *
 * Replace every REPLACE_* value with the Web app configuration shown in
 * Firebase Console → Project settings → Your apps. These values identify the
 * Firebase project; Firestore rules in firestore.rules protect the data.
 */
window.JAPAN_FIREBASE_CONFIG = {
  apiKey: "AIzaSyCeJNnvCDd80qQOjzSfYVAwCnlZaoINv2k",
  authDomain: "laam-673db.firebaseapp.com",
  projectId: "laam-673db",
  storageBucket: "laam-673db.firebasestorage.app",
  messagingSenderId: "354920262931",
  appId: "1:354920262931:web:2808a4da1e9233ca513ee6",
  measurementId: "G-6B9GJMZRB4"
};

// Change only when intentionally starting a separate shared group itinerary.
window.JAPAN_TRIP_ID = "japan-family-trip";

const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);