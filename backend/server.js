const express = require("express");
const cors = require("cors");
const mysql = require("mysql2");
const bodyParser = require("body-parser");

require("dotenv").config();

const authRoutes = require("./auth");

const app = express();
app.use(cors());
app.use(bodyParser.json());

app.use("/api", authRoutes);

app.listen(5000, () => {
  console.log("✅ Server running on http://localhost:5000");
});

app.get("/", (req, res) => {
    res.send("Backend is running");
  });