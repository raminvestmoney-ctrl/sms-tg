import "dotenv/config";
import makeWASocket, {
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
} from "@whiskeysockets/baileys";
import express from "express";
import bodyParser from "body-parser";
import pino from "pino";
import pkg from "pg";
import fs from "fs";
import path from "path";

const { Pool } = pkg;

// ══════════════════════════════════════════
//  SETTINGS
// ══════════════════════════════════════════
const TARGET_GROUP_NAME = process.env.TARGET_GROUP_NAME || "Ep fresh account";
const PORT = process.env.WA_PORT || 5001;
const AUTH_FOLDER = "./auth_info_baileys";

// PostgreSQL connection (add DATABASE_URL to Railway env variables)
const pool = process.env.DATABASE_URL ? new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
}) : null;

// ══════════════════════════════════════════

const app = express();
app.use(bodyParser.json());
const logger = pino({ level: "silent" });

let sock = null;
let targetGroupJid = null;
let isReady = false;
let qrCodeString = null;
let reconnectAttempts = 0;

// ── DATABASE SESSION FUNCTIONS ──────────────────────────────────
async function initDB() {
  if (!pool) return;
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS wa_session (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);
    console.log("✅ Database ready for session storage");
  } catch (err) {
    console.error("❌ DB init error:", err.message);
  }
}

async function saveSessionToDB() {
  if (!pool) return;
  try {
    if (!fs.existsSync(AUTH_FOLDER)) return;
    const files = fs.readdirSync(AUTH_FOLDER);
    const sessionData = {};
    for (const file of files) {
      const content = fs.readFileSync(path.join(AUTH_FOLDER, file), "utf8");
      sessionData[file] = content;
    }
    await pool.query(`
      INSERT INTO wa_session (id, data, updated_at)
      VALUES ('main', $1, NOW())
      ON CONFLICT (id) DO UPDATE SET data = $1, updated_at = NOW()
    `, [JSON.stringify(sessionData)]);
    console.log("💾 Session saved to database");
  } catch (err) {
    console.error("❌ Session save error:", err.message);
  }
}

async function loadSessionFromDB() {
  if (!pool) return false;
  try {
    const result = await pool.query("SELECT data FROM wa_session WHERE id = 'main'");
    if (result.rows.length === 0) return false;

    const sessionData = JSON.parse(result.rows[0].data);
    if (!fs.existsSync(AUTH_FOLDER)) fs.mkdirSync(AUTH_FOLDER, { recursive: true });

    for (const [filename, content] of Object.entries(sessionData)) {
      fs.writeFileSync(path.join(AUTH_FOLDER, filename), content);
    }
    console.log("📂 Session loaded from database");
    return true;
  } catch (err) {
    console.error("❌ Session load error:", err.message);
    return false;
  }
}

// ── FIND GROUP JID ──────────────────────────────────────────────
async function findGroupJid(groupName) {
  try {
    const groups = await sock.groupFetchAllParticipating();
    for (const [jid, group] of Object.entries(groups)) {
      if (group.subject === groupName) {
        console.log(`✅ Found group: "${groupName}" → JID: ${jid}`);
        return jid;
      }
    }
    console.error(`❌ Group "${groupName}" not found!`);
    console.log("📋 Available groups:");
    for (const [jid, group] of Object.entries(groups)) {
      console.log(`   - "${group.subject}"`);
    }
    return null;
  } catch (err) {
    console.error("❌ Error fetching groups:", err.message);
    return null;
  }
}

// ── START WHATSAPP CONNECTION ───────────────────────────────────
async function startWAConnection() {
  try {
    // Load session from DB before connecting
    await loadSessionFromDB();

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_FOLDER);
    const { version } = await fetchLatestBaileysVersion();

    sock = makeWASocket({
      version,
      logger,
      auth: {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore(state.keys, logger),
      },
      printQRInTerminal: false,
      browser: ["WA-Cloud-Bot", "Chrome", "1.0.0"],
      syncFullHistory: false,
      connectTimeoutMs: 60000,
      retryRequestDelayMs: 2000,
    });

    sock.ev.on("creds.update", async () => {
      await saveCreds();
      await saveSessionToDB(); // Save to DB every time creds update
    });

    sock.ev.on("connection.update", async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        qrCodeString = qr;
        isReady = false;
        console.log("\n📱 QR CODE READY — Visit /qr in browser to scan\n");
      }

      if (connection === "open") {
        console.log("✅ WhatsApp connected successfully!");
        isReady = true;
        qrCodeString = null;
        reconnectAttempts = 0;

        // Save session immediately on connect
        await saveSessionToDB();

        // Find target group
        setTimeout(async () => {
          targetGroupJid = await findGroupJid(TARGET_GROUP_NAME);
          if (!targetGroupJid) {
            console.warn(`⚠️  Group "${TARGET_GROUP_NAME}" not found. Check TARGET_GROUP_NAME env variable.`);
          }
        }, 3000);
      }

      if (connection === "close") {
        isReady = false;
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

        console.log(`⚠️  Connection closed. Status: ${statusCode}. Reconnect: ${shouldReconnect}`);

        if (shouldReconnect) {
          reconnectAttempts++;
          const delay = Math.min(5000 * reconnectAttempts, 30000); // Max 30s delay
          console.log(`🔄 Reconnecting in ${delay/1000}s... (attempt ${reconnectAttempts})`);
          setTimeout(startWAConnection, delay);
        } else {
          console.log("🚪 Logged out! Visit /qr to scan QR code again.");
          // Clear session from DB on logout
          if (pool) {
            await pool.query("DELETE FROM wa_session WHERE id = 'main'");
          }
          if (fs.existsSync(AUTH_FOLDER)) {
            fs.rmSync(AUTH_FOLDER, { recursive: true });
          }
          setTimeout(startWAConnection, 3000);
        }
      }
    });

  } catch (err) {
    console.error("❌ startWAConnection error:", err.message);
    setTimeout(startWAConnection, 10000);
  }
}

// ── SEND CODE TO GROUP ──────────────────────────────────────────
async function sendCodeToGroup(formattedMsg) {
  if (!isReady || !sock) throw new Error("WhatsApp not connected yet.");

  if (!targetGroupJid) {
    targetGroupJid = await findGroupJid(TARGET_GROUP_NAME);
    if (!targetGroupJid) throw new Error(`Group "${TARGET_GROUP_NAME}" not found.`);
  }

  await sock.sendMessage(targetGroupJid, { text: formattedMsg });
  console.log(`✅ Message sent to group "${TARGET_GROUP_NAME}"`);
  return true;
}

// ══════════════════════════════════════════
//  EXPRESS ROUTES
// ══════════════════════════════════════════

app.post("/send_code", async (req, res) => {
  const data = req.body;
  if (!data) return res.status(400).json({ status: "no data" });

  const code = data.code;
  const message = data.message || "No message body";
  const sender = data.sender || "Unknown";

  if (!code) {
      // Fallback: Try re-extracting from message if code is missing
      const match = message.match(/\b(\d{4,8})\b/);
      if (!match) {
          console.log(`⏭️  No code found in message: ${message.slice(0, 50)}`);
          return res.status(200).json({ status: "no_code" });
      }
      data.code = match[1];
  }

  console.log(`📩 Forwarding code: ${data.code} from ${sender}`);

  // Format the message nicely for WhatsApp
  const formattedMsg = `📩 *New Code Received!*\n` +
                       `━━━━━━━━━━━━━━━━━━━━\n` +
                       `📱 *From:* ${sender}\n` +
                       `🎯 *Code:* *${data.code}*\n` +
                       `━━━━━━━━━━━━━━━━━━━━\n` +
                       `💬 *Message:*\n` +
                       `_${message}_`;

  try {
    await sendCodeToGroup(formattedMsg);
    return res.status(200).json({ status: "sent", code: data.code });
  } catch (err) {
    console.error(`❌ Send failed: ${err.message}`);
    return res.status(500).json({ status: "failed", error: err.message });
  }
});

app.get("/qr", (req, res) => {
  if (isReady) return res.send(`
    <html><body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#f0f0f0">
    <div style="text-align:center">
      <h2>✅ WhatsApp is connected!</h2>
      <p>Bot is running and ready to send codes.</p>
      <a href="/test" style="background:#25D366;color:white;padding:10px 20px;border-radius:8px;text-decoration:none">Test Send Code</a>
    </div></body></html>
  `);

  if (!qrCodeString) return res.send(`
    <html><body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#f0f0f0">
    <div style="text-align:center">
      <h2>⏳ Generating QR code...</h2>
      <p>Please wait, refreshing automatically...</p>
    </div>
    <script>setTimeout(()=>location.reload(), 3000)</script>
    </body></html>
  `);

  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>WhatsApp QR</title>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    </head>
    <body style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#f0f0f0">
      <h2>📱 Scan with WhatsApp</h2>
      <p>Settings → Linked Devices → Link a Device</p>
      <div id="qrcode" style="background:white;padding:20px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.1)"></div>
      <p style="color:#888;margin-top:20px">Page auto-refreshes every 25s</p>
      <script>
        new QRCode(document.getElementById("qrcode"), {
          text: ${JSON.stringify(qrCodeString)},
          width: 280,
          height: 280
        });
        setTimeout(() => location.reload(), 25000);
      </script>
    </body>
    </html>
  `);
});

app.get("/", (req, res) => {
  res.json({
    status: isReady ? "connected ✅" : "not connected ❌",
    group: TARGET_GROUP_NAME,
    groupJid: targetGroupJid || "searching...",
    qrAvailable: !!qrCodeString,
    reconnectAttempts,
    message: !isReady ? "Visit /qr to scan QR code" : "Ready to receive codes!"
  });
});

app.get("/test", async (req, res) => {
  try {
    await sendCodeToGroup("123456");
    res.json({ status: "test sent ✅", code: "123456", group: TARGET_GROUP_NAME });
  } catch (err) {
    res.status(500).json({ status: "failed ❌", error: err.message });
  }
});

// ── START ──────────────────────────────────────────────────────
async function main() {
  await initDB();

  app.listen(PORT, () => {
    console.log("=".repeat(50));
    console.log("  🚀 WA Cloud Bot Started!");
    console.log(`  🌐 Port: ${PORT}`);
    console.log(`  🎯 Target Group: "${TARGET_GROUP_NAME}"`);
    console.log(`  💾 DB Session: ${pool ? "enabled ✅" : "disabled ⚠️"}`);
    console.log("=".repeat(50));
  });

  await startWAConnection();
}

main();
