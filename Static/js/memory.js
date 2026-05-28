async function loadMemory() {
    const res = await fetch("/memory");
    const memory = await res.json();

    const list = document.getElementById("memoryList");
    list.innerHTML = "";

    for (const category in memory) {
        for (const key in memory[category]) {
            const li = document.createElement("li");
            li.innerText = `${category}: ${key} → ${memory[category][key].value}`;
            list.appendChild(li);
        }
    }
}

loadMemory();
