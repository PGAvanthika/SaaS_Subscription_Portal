/**
 * CYBERVAULT - Main JavaScript Client Logic
 * Handles Security Mode switching, interactive security lab triggers, dynamic toast alerts, and UI updates.
 */

document.addEventListener("DOMContentLoaded", () => {
  initSecurityToggle();
});

function initSecurityToggle() {
  const toggleCheckbox = document.getElementById("securityModeToggle");
  if (!toggleCheckbox) return;

  toggleCheckbox.addEventListener("change", async (e) => {
    const isSecure = e.target.checked;
    const mode = isSecure ? "SECURE" : "VULNERABLE";
    
    try {
      const response = await fetch("/api/toggle-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: mode })
      });

      const data = await response.json();
      if (data.success) {
        showToast(
          isSecure ? "Shield Activated: SECURE MODE Enabled" : "Shield Deactivated: VULNERABLE MODE Enabled",
          isSecure ? "secure" : "vulnerable"
        );

        // Update UI status badges dynamically
        const badge = document.getElementById("securityBadge");
        if (badge) {
          badge.className = `status-badge ${isSecure ? 'secure' : 'vulnerable'}`;
          badge.innerHTML = isSecure ? "🛡️ SECURE MODE" : "⚠️ VULNERABLE MODE";
        }

        // Reload current page if on lab to update demo states
        if (window.location.pathname.includes("/lab") || window.location.pathname.includes("/dashboard")) {
          setTimeout(() => window.location.reload(), 1000);
        }
      }
    } catch (err) {
      console.error("Failed to toggle security mode:", err);
      showToast("Error updating security mode", "vulnerable");
    }
  });
}

function showToast(message, type = "info") {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'secure' ? '✅' : type === 'vulnerable' ? '⚠️' : 'ℹ️'}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function appendTerminalLog(elementId, text, type = "info") {
  const terminal = document.getElementById(elementId);
  if (!terminal) return;
  const line = document.createElement("div");
  line.className = `log-entry log-${type}`;
  const timestamp = new Date().toLocaleTimeString();
  line.innerText = `[${timestamp}] ${text}`;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}
