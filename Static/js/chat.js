const chat = document.getElementById("chat");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

sendBtn.onclick = sendMessage;
input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    chat.innerHTML += `<div class="user">${text}</div>`;
    input.value = "";

    const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    });

    const data = await res.json();

    chat.innerHTML += `<div class="orion">${data.reply}</div>`;
    document.getElementById("modeBadge").innerText = "Mode: " + data.mode;

    chat.scrollTop = chat.scrollHeight;
}
