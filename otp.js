// frontend/js/otp.js
const inputs = document.querySelectorAll(".otp-input");
const form = document.getElementById("otpForm");

// Auto-focus between OTP boxes
inputs.forEach((input, index) => {
  input.addEventListener("keyup", (e) => {
    if (e.key >= 0 && e.key <= 9) {
      if (index < inputs.length - 1) inputs[index + 1].focus();
    } else if (e.key === "Backspace" && index > 0) {
      inputs[index - 1].focus();
    }
  });
});

// Handle OTP form submit
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const otp = Array.from(inputs).map(input => input.value).join("");
  const email = localStorage.getItem("userEmail");

  if (!otp || otp.length !== 6) {
    alert("Please enter a valid 6-digit OTP");
    return;
  }

  try {
    const res = await fetch("http://localhost:5000/api/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, otp })
    });

    const data = await res.json();

    if (res.ok && data.success) {
      alert("✅ " + data.message);
      window.location.href = "index.html"; // redirect to homepage
    } else {
      alert("❌ " + data.message);
    }
  } catch (err) {
    console.error("OTP error:", err);
    alert("⚠️ Unable to connect to server");
  }
});
