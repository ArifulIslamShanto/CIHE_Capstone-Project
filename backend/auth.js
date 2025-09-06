const express = require("express");
const crypto = require("crypto");
const db = require("./db");
const sendMail = require("./mailer");

const router = express.Router();

// 🔹 Login route
router.post("/login", async (req, res) => {
  const { email, password } = req.body;

  try {
    const [users] = await db.query("SELECT * FROM users WHERE email=? AND password=?", [email, password]);
    if (users.length === 0) return res.status(401).json({ success: false, message: "Invalid credentials" });

    const otp = crypto.randomInt(100000, 999999).toString();
    const expiry = new Date(Date.now() + 5 * 60 * 1000);

    await db.query("INSERT INTO otp (email, otp, otp_expiry) VALUES (?, ?, ?)", [email, otp, expiry]);
    await sendMail(email, "Your HotDoc OTP", `Your OTP is: ${otp}. It expires in 5 minutes.`);

    res.json({ success: true, message: "OTP sent to your email" });

  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, message: "Server error" });
  }
});

// 🔹 OTP verify route
router.post("/verify-otp", async (req, res) => {
  const { email, otp } = req.body;

  try {
    const [rows] = await db.query("SELECT * FROM otp WHERE email=? ORDER BY id DESC LIMIT 1", [email]);
    if (rows.length === 0) return res.status(400).json({ success: false, message: "No OTP found" });

    const record = rows[0];
    if (record.otp !== otp) return res.status(400).json({ success: false, message: "Invalid OTP" });
    if (new Date() > record.otp_expiry) return res.status(400).json({ success: false, message: "OTP expired" });

    res.json({ success: true, message: "OTP verified successfully" });

  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, message: "Server error" });
  }
});

module.exports = router;
