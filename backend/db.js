const mysql = require("mysql2/promise");

const db = mysql.createPool({
  host: "localhost",
  user: "root",
  password: process.env.DB_PASSWORD,
  database: "hotdocuser"
});

db.getConnection()
  .then(conn => {
    console.log("✅ DB connected");
    conn.release();
  })
  .catch(err => {
    console.error("❌ DB connection error:", err);
  });

module.exports = db;
