const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCodeImg = require('qrcode');
const axios = require('axios');
const fs = require('fs');

// Auto-detect local Chrome or Edge path on Windows to avoid downloading headless Chrome
function getLocalBrowserPath() {
    const paths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
        'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    ];
    for (const p of paths) {
        if (fs.existsSync(p)) {
            return p;
        }
    }
    return null;
}

const executablePath = getLocalBrowserPath();

// Create the WhatsApp Client using a local auth session to stay logged in
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './.wwebjs_auth'
    }),
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
    },
    puppeteer: {
        headless: false, // Set to false to prevent the "main frame too early" Puppeteer error
        executablePath: executablePath || undefined,
        args: [
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    }
});

// Print the QR Code in the terminal and send to FastAPI
client.on('qr', async (qr) => {
    console.clear();
    console.log('================================================================');
    console.log('🍒 CHERRY DIRECT WHATSAPP BRIDGE');
    console.log('================================================================');
    console.log('Scan the QR code below using your phone\'s WhatsApp to link:');
    console.log('Go to WhatsApp > Linked Devices > Link a Device');
    console.log('----------------------------------------------------------------\n');
    qrcode.generate(qr, { small: true });

    try {
        const qrDataUrl = await QRCodeImg.toDataURL(qr);
        await axios.post('http://localhost:8001/api/whatsapp/qr', { qrDataUrl });
    } catch (e) {
        console.error('Failed to send QR image to local server:', e.message);
    }
});

// Event when connected
client.on('ready', async () => {
    console.log('\n================================================================');
    console.log('✅ CHERRY IS CONNECTED DIRECTLY TO WHATSAPP!');
    console.log('Listening for incoming messages...');
    console.log('================================================================\n');
    try {
        await axios.post('http://localhost:8001/api/whatsapp/status', { status: 'connected' });
    } catch (e) {
        // Ignore errors if local server is starting up
    }
});

// Event when disconnected
client.on('disconnected', async (reason) => {
    console.log('❌ WhatsApp Disconnected:', reason);
    try {
        await axios.post('http://localhost:8001/api/whatsapp/status', { status: 'disconnected' });
    } catch (e) {
        // Ignore
    }
});

// Cache to keep track of agent's own automated replies to prevent loops in self-chats
const recentAgentReplies = new Set();

// Handle incoming and self-created messages
client.on('message_create', async (msg) => {
    // DIAGNOSTIC LOG: Log every event to see what is happening
    console.log(`[DEBUG LOG] Event: message_create | From: ${msg.from} | To: ${msg.to} | FromMe: ${msg.fromMe} | Body: "${msg.body}"`);

    // Only respond to direct private user chats (ends with @c.us), ignore groups, newsletters, broadcasts
    if (!msg.to.endsWith('@c.us') && !msg.from.endsWith('@c.us')) {
        return;
    }

    const selfJid = client.info.wid._serialized;
    const isSelfChat = (msg.from === selfJid && msg.to === selfJid);

    // If it's a message sent to/from someone else:
    // We only auto-reply to INCOMING messages (msg.fromMe === false)
    if (msg.fromMe && !isSelfChat) {
        return;
    }

    // Ignore if this message is our own automated reply to prevent loops
    if (recentAgentReplies.has(msg.body) || recentAgentReplies.has(msg.id.id)) {
        recentAgentReplies.delete(msg.body);
        recentAgentReplies.delete(msg.id.id);
        return;
    }

    // The chat we are communicating in
    const chat = await msg.getChat();
    if (chat.isGroup || chat.isReadOnly) {
        return;
    }

    // Determine the user's phone identifier to save history under (From/To)
    // If it's a self-chat, we use our own number, otherwise the sender's number
    const chatPartner = isSelfChat ? selfJid : msg.from;

    console.log(`[WhatsApp Inbound] From: ${chatPartner} (Self: ${isSelfChat}) | Message: "${msg.body}"`);

    // Let the user know Cherry is thinking
    if (chat && typeof chat.sendStateTyping === 'function') {
        try {
            await chat.sendStateTyping();
        } catch (e) {
            // Ignore
        }
    }

    try {
        // Forward message to Cherry FastAPI backend
        const formData = new URLSearchParams();
        formData.append('From', chatPartner);
        formData.append('Body', msg.body);

        const response = await axios.post('http://localhost:8001/api/webhook/whatsapp', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });

        const reply = response.data.agent_reply;
        if (reply) {
            recentAgentReplies.add(reply);
            const sentMsg = await client.sendMessage(chatPartner, reply);
            recentAgentReplies.add(sentMsg.id.id);
            console.log(`[WhatsApp Outbound] Sent Reply: "${reply}"`);
        } else {
            console.log(`[WhatsApp Outbound] No reply generated by agent.`);
        }
    } catch (error) {
        console.error('❌ Error forwarding message to Cherry agent:', error.message);
        if (!msg.fromMe) {
            msg.reply('Sorry, I had trouble communicating with my local agent server. Make sure the Cherry FastAPI server is running!');
        }
    }
});

client.initialize();
