/**
 * BonBon Chat Widget Loader
 * Lightweight script (~2KB) that embeds a chat widget iframe.
 *
 * Usage:
 *   <script src="https://getbonito.com/widget.js"
 *     data-agent-id="YOUR_AGENT_ID"
 *     data-theme="light">
 *   </script>
 */
(function () {
  "use strict";

  // Read config from script tag
  var script =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      return scripts[scripts.length - 1];
    })();

  var agentId = script.getAttribute("data-agent-id");
  if (!agentId) {
    console.error("[BonBon] Missing data-agent-id attribute");
    return;
  }

  var theme = script.getAttribute("data-theme") || "light";
  var baseUrl = script.getAttribute("data-base-url") || script.src.replace(/\/widget\.js.*$/, "");

  // Prevent double-init
  if (document.getElementById("bonbon-widget-root")) return;

  // Create container
  var root = document.createElement("div");
  root.id = "bonbon-widget-root";
  root.style.cssText = "position:fixed;bottom:0;right:0;z-index:2147483647;pointer-events:none;";
  document.body.appendChild(root);

  // Bubble button
  var bubble = document.createElement("button");
  bubble.id = "bonbon-bubble";
  bubble.setAttribute("aria-label", "Open chat");
  bubble.style.cssText =
    "position:fixed;bottom:24px;right:24px;z-index:2147483647;width:56px;height:56px;" +
    "border-radius:50%;border:none;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.15);" +
    "background:#6366f1;display:flex;align-items:center;justify-content:center;" +
    "transition:transform 0.2s;pointer-events:auto;";
  bubble.innerHTML =
    '<svg width="24" height="24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
  bubble.onmouseenter = function () {
    bubble.style.transform = "scale(1.08)";
  };
  bubble.onmouseleave = function () {
    bubble.style.transform = "scale(1)";
  };
  root.appendChild(bubble);

  // Iframe (hidden initially)
  var iframe = document.createElement("iframe");
  iframe.id = "bonbon-iframe";
  iframe.src = baseUrl + "/widget/chat/" + agentId + "?theme=" + theme;
  iframe.style.cssText =
    "position:fixed;bottom:96px;right:24px;z-index:2147483647;width:380px;height:600px;" +
    "max-height:calc(100vh - 120px);border:none;border-radius:16px;" +
    "box-shadow:0 8px 30px rgba(0,0,0,0.12);display:none;pointer-events:auto;" +
    "background:transparent;";
  iframe.setAttribute("allow", "clipboard-write");
  iframe.setAttribute("title", "BonBon Chat Widget");
  root.appendChild(iframe);

  var isOpen = false;

  function toggleWidget() {
    isOpen = !isOpen;
    iframe.style.display = isOpen ? "block" : "none";
    bubble.innerHTML = isOpen
      ? '<svg width="24" height="24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'
      : '<svg width="24" height="24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
    bubble.setAttribute("aria-label", isOpen ? "Close chat" : "Open chat");
  }

  bubble.addEventListener("click", toggleWidget);

  // Listen for messages from iframe
  window.addEventListener("message", function (event) {
    if (!event.data || event.data.source !== "bonbon-widget") return;

    if (event.data.type === "resize") {
      iframe.style.height = event.data.height + "px";
    } else if (event.data.type === "close") {
      if (isOpen) toggleWidget();
    } else if (event.data.type === "accent") {
      bubble.style.background = event.data.color;
    }
  });

  // Mobile responsive
  function handleResize() {
    if (window.innerWidth < 480) {
      iframe.style.width = "100vw";
      iframe.style.height = "100vh";
      iframe.style.bottom = "0";
      iframe.style.right = "0";
      iframe.style.borderRadius = "0";
      iframe.style.maxHeight = "100vh";
    } else {
      iframe.style.width = "380px";
      iframe.style.height = "600px";
      iframe.style.bottom = "96px";
      iframe.style.right = "24px";
      iframe.style.borderRadius = "16px";
      iframe.style.maxHeight = "calc(100vh - 120px)";
    }
  }

  window.addEventListener("resize", handleResize);
  handleResize();
})();
