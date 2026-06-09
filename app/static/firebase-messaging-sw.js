importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "__FCM_API_KEY__",
  projectId: "paceclimate-f395b",
  messagingSenderId: "__FCM_SENDER_ID__",
  appId: "__FCM_APP_ID__",
});

const messaging = firebase.messaging();
var lastPayload = null;

messaging.onBackgroundMessage(function(payload) {
  lastPayload = payload;
  var title = payload.notification.title || "🏃 PaceClimate";
  var body = payload.notification.body || "Time for a run!";
  var options = {
    body: body,
    icon: "/static/icon-192.png",
    badge: "/static/icon-192.png",
    vibrate: [200, 100, 200],
    tag: "paceclimate-" + Date.now(),
    requireInteraction: true,
    actions: [
      { action: "log", title: "🏃 Log Run" },
      { action: "snooze", title: "⏰ Snooze 15" },
    ],
  };
  self.registration.showNotification(title, options);
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  if (event.action === "log") {
    event.waitUntil(clients.openWindow("/?log=1"));
  } else if (event.action === "snooze") {
    var payload = lastPayload;
    setTimeout(function() {
      var title = (payload && payload.notification && payload.notification.title) || "🏃 Time for a run!";
      var body = (payload && payload.notification && payload.notification.body) || "Your reminder is back!";
      self.registration.showNotification(title, {
        body: body + " (snoozed)",
        icon: "/static/icon-192.png",
        badge: "/static/icon-192.png",
        vibrate: [200, 100, 200],
        tag: "paceclimate-snoozed-" + Date.now(),
        requireInteraction: true,
        actions: [
          { action: "log", title: "🏃 Log Run" },
        ],
      });
    }, 15 * 60 * 1000);
  } else {
    event.waitUntil(clients.openWindow("/"));
  }
});
