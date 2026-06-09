importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js");

let messaging = null;

self.addEventListener("message", function(event) {
  if (event.data && event.data.type === "FCM_CONFIG") {
    firebase.initializeApp(event.data.config);
    messaging = firebase.messaging();

    messaging.onBackgroundMessage(function(payload) {
      var title = payload.notification.title;
      var options = {
        body: payload.notification.body,
        icon: "/static/icon-192.png",
        badge: "/static/icon-192.png",
        data: payload.data || {},
      };
      self.registration.showNotification(title, options);
    });
  }
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow("/"));
});
