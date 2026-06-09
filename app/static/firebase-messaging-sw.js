importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "__FCM_API_KEY__",
  projectId: "paceclimate-f395b",
  messagingSenderId: "__FCM_SENDER_ID__",
  appId: "__FCM_APP_ID__",
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  const title = payload.notification.title || "🏃 PaceClimate";
  const body = payload.notification.body || "Time for a run!";
  const options = {
    body: body,
    icon: "/static/icon-192.png",
    badge: "/static/icon-192.png",
    vibrate: [200, 100, 200],
    tag: "paceclimate-" + Date.now(),
    requireInteraction: true,
  };
  self.registration.showNotification(title, options);
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow("/"));
});
