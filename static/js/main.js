/**
 * SAASFLOW - Enterprise JavaScript Client Logic
 * Handles Security Mode switching, security lab triggers, toast notifications, and UI updates.
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
          isSecure ? "Security Mode: PROTECTED / SECURE" : "Security Mode: EXPOSED / VULNERABLE",
          isSecure ? "secure" : "vulnerable"
        );

        // Update UI status badges dynamically
        const badge = document.getElementById("securityBadge");
        if (badge) {
          badge.className = `status-pill ${isSecure ? 'secure' : 'vulnerable'}`;
          badge.innerHTML = isSecure ? "PROTECTED" : "VULNERABLE";
        }

        // Reload current page if on lab or dashboard to reflect mode updates
        if (window.location.pathname.includes("/lab") || window.location.pathname.includes("/dashboard")) {
          setTimeout(() => window.location.reload(), 800);
        }
      }
    } catch (err) {
      console.error("Failed to toggle security mode:", err);
      showToast("Error updating security mode state", "vulnerable");
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
  
  const icon = type === 'secure' 
    ? `<svg class="icon-svg" viewBox="0 0 24 24" style="color:var(--status-secure);"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>`
    : type === 'vulnerable'
    ? `<svg class="icon-svg" viewBox="0 0 24 24" style="color:var(--status-vuln);"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`
    : `<svg class="icon-svg" viewBox="0 0 24 24" style="color:var(--accent-cyan);"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;

  toast.innerHTML = `
    ${icon}
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
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
