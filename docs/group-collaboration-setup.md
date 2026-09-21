# Enable shared Japan itinerary editing

The Japan page stays a static site. Firebase supplies Google sign-in and the
private, live group itinerary data.

1. Create a Firebase project and add a **Web app**. Copy its configuration into
   `japan_firebase_config.js`.
2. In **Authentication**, enable the Google provider. Add the deployed Japan
   site domain and `localhost` to Authorized domains.
3. Create a Firestore database in Production mode. Publish `firestore.rules`
   in the Firestore Rules editor or with the Firebase CLI:

   ```bash
   firebase deploy --only firestore:rules
   ```

4. Regenerate and publish `japan.html` with the updated configuration file.
   Open the page, choose **Group plan**, sign in, and initialize the shared
   itinerary before distributing the link. That first account becomes owner.
5. Friends sign in and choose **Request access**. The owner opens Group plan
   and approves each request.

The Firebase web configuration is intentionally public. Do not put a service
account, private key, or any credential in this repository. The deployed
Firestore rules are what restrict group data to approved members.

## Operational notes

- Every shared stop is editable by every approved member, including bookings.
- Location lookup performs one deliberate OpenStreetMap Nominatim search on
  Save; contributors should verify a result or use **Pick on map**.
- The app redraws ordered route connections from stored coordinates. New or
  reordered connections are labelled approximate rather than road directions.
- Firebase's local cache may show pending writes briefly. If a write is
  rejected or an item changed while being edited, the page shows a message and
  keeps the server version authoritative.
