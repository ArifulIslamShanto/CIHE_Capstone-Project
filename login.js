// frontend/js/login.js
document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  const form = document.getElementById("loginForm");
  const cameraBox = document.getElementById("camera-box");

  form.addEventListener("submit", function(e) {
    e.preventDefault();  // Stop default form submission
    cameraBox.style.display = "block";  // Show camera feed
  });

  try {
    const res = await fetch("http://localhost:5000/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok && data.success) {
      alert("✅ " + data.message);

      // Save email for OTP verification step
      localStorage.setItem("userEmail", email);

      // Redirect to OTP page
      window.location.href = "otp.html";
    } else {
      alert("❌ " + data.message);
    }
  } catch (err) {
    console.error("Login error:", err);
    alert("⚠️ Unable to connect to server");
  }
});
