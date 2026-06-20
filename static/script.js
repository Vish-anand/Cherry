document.addEventListener("DOMContentLoaded", () => {
    // Navigation Tabs mapping
    const tabBtns = document.querySelectorAll(".tab-trigger");
    const tabContents = document.querySelectorAll(".tools-tab-content");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            
            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(`tab-${tabId}`).classList.add("active");

            if (tabId === "workspace") {
                loadWorkspaceTree();
            } else if (tabId === "doc-bank") {
                loadDocuments();
            }
        });
    });

    // Autogrow text area logic for chat input
    const chatInput = document.getElementById("chat-input");
    chatInput.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
    });

    // Chat Attachment Management
    const chatFileUpload = document.getElementById("chat-file-upload");
    const attachPreview = document.getElementById("attach-preview");
    const previewFilename = document.getElementById("preview-filename");
    const clearAttachBtn = document.getElementById("clear-attach-btn");
    let activeAttachment = null;

    chatFileUpload.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            activeAttachment = e.target.files[0];
            previewFilename.textContent = activeAttachment.name;
            attachPreview.style.display = "flex";
        }
    });

    clearAttachBtn.addEventListener("click", () => {
        activeAttachment = null;
        chatFileUpload.value = "";
        attachPreview.style.display = "none";
    });

    // Chat Message Ingestion & Run
    const sendBtn = document.getElementById("send-btn");
    const chatMessages = document.getElementById("chat-messages");
    let activeEventSource = null;

    async function sendChatMessage() {
        const text = chatInput.value.trim();
        if (!text && !activeAttachment) return;
        
        chatInput.value = "";
        chatInput.style.height = "auto"; // Reset height
        
        // Append user message
        appendMessage("user", text, activeAttachment ? activeAttachment.name : null);
        
        let attachmentPath = null;
        if (activeAttachment) {
            const formData = new FormData();
            formData.append("file", activeAttachment);
            
            appendStatus("Uploading attachment...");
            try {
                const res = await fetch("/api/documents/upload", {
                    method: "POST",
                    body: formData
                });
                await res.json();
                attachmentPath = `incoming/${activeAttachment.name}`;
                appendStatus("Attachment uploaded. Running agent...");
            } catch (err) {
                appendMessage("system", `Failed to upload attachment: ${err.message}`);
                return;
            }
            
            activeAttachment = null;
            chatFileUpload.value = "";
            attachPreview.style.display = "none";
        }

        // Start SSE stream
        const encodedPrompt = encodeURIComponent(text);
        const conversationId = "default";
        let url = `/api/chat?prompt=${encodedPrompt}&conversation_id=${conversationId}`;
        if (attachmentPath) {
            url += `&attachment_rel_path=${encodeURIComponent(attachmentPath)}`;
        }

        if (activeEventSource) {
            activeEventSource.close();
        }

        const stepsContainer = document.createElement("div");
        stepsContainer.className = "agent-steps-group";
        chatMessages.appendChild(stepsContainer);

        activeEventSource = new EventSource(url);
        
        activeEventSource.onmessage = (event) => {
            const step = JSON.parse(event.data);
            
            if (step.type === "status") {
                updateLiveStatus(step.content);
            } else if (step.type === "thought") {
                appendStepCard(stepsContainer, "thought", "Thought", step.content);
            } else if (step.type === "action") {
                const argsStr = JSON.stringify(step.input, null, 2);
                appendStepCard(stepsContainer, "action", `Action: ${step.tool}`, `Arguments:\n${argsStr}`);
            } else if (step.type === "observation") {
                appendStepCard(stepsContainer, "observation", "Observation", step.content);
            } else if (step.type === "final_answer") {
                appendMessage("assistant", step.content);
                updateLiveStatus("Cherry is Active");
                activeEventSource.close();
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else if (step.type === "error") {
                appendMessage("system", `Engine Error: ${step.content}`);
                updateLiveStatus("Cherry is Active");
                activeEventSource.close();
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        };

        activeEventSource.onerror = () => {
            updateLiveStatus("Cherry is Active");
            activeEventSource.close();
        };
    }

    sendBtn.addEventListener("click", sendChatMessage);
    chatInput.addEventListener("keypress", (e) => {
        // Submit on Enter, line break on Shift+Enter
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    function appendMessage(role, content, filename = null) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `msg-bubble ${role}`;
        
        const avatar = role === "user" ? "U" : "🍒";
        let attachmentHtml = "";
        if (filename) {
            attachmentHtml = `<div style="margin-top:0.4rem; padding:0.25rem 0.5rem; background:rgba(255,255,255,0.05); font-size:0.8rem; border-radius:6px;"><i class="fa-solid fa-file"></i> ${filename}</div>`;
        }

        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-text">
                <div>${content.replace(/\n/g, '<br>')}</div>
                ${attachmentHtml}
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendStatus(content) {
        updateLiveStatus(content);
    }

    function updateLiveStatus(text) {
        // Just print status text on dashboard indicators
        console.log(`Cherry Status: ${text}`);
    }

    function appendStepCard(container, type, title, content) {
        const card = document.createElement("div");
        card.className = "react-step";
        
        card.innerHTML = `
            <div class="step-header ${type}">
                <i class="fa-solid ${type === 'thought' ? 'fa-lightbulb' : type === 'action' ? 'fa-gears' : 'fa-list-check'}"></i>
                <span>${title}</span>
            </div>
            <div class="step-body">${content}</div>
        `;
        container.appendChild(card);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // ==========================================
    // DOCUMENT BANK TAB
    // ==========================================
    const directDocUpload = document.getElementById("direct-doc-upload");
    const docSearch = document.getElementById("doc-search");
    const documentsContainer = document.getElementById("documents-container");
    const filterPills = document.querySelectorAll(".pill");
    let activeCategory = "all";

    directDocUpload.addEventListener("change", async (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const res = await fetch("/api/documents/upload", {
                    method: "POST",
                    body: formData
                });
                await res.json();
                loadDocuments();
            } catch (err) {
                alert(`Upload failed: ${err.message}`);
            }
        }
    });

    async function loadDocuments(query = "") {
        let url = "/api/documents";
        if (query) {
            url = `/api/documents/search?query=${encodeURIComponent(query)}`;
        } else if (activeCategory !== "all") {
            url = `/api/documents?category=${activeCategory}`;
        }

        try {
            const res = await fetch(url);
            const docs = await res.json();
            renderDocuments(docs);
        } catch (err) {
            console.error("Error loading documents:", err);
        }
    }

    function renderDocuments(docs) {
        documentsContainer.innerHTML = "";
        if (docs.length === 0) {
            documentsContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-folder-open"></i>
                    <p>No documents found matching the filters.</p>
                </div>
            `;
            return;
        }

        docs.forEach(doc => {
            const card = document.createElement("div");
            card.className = `modern-doc-card ${doc.category}`;
            
            const meta = doc.metadata || {};
            const date = meta.date_issued || "Unknown";
            const summary = meta.summary || "No summary extracted.";
            const amount = meta.amount_due_or_paid ? `$${meta.amount_due_or_paid.toFixed(2)}` : "N/A";
            const name = meta.primary_name || "N/A";

            let iconClass = "fa-file-lines";
            if (doc.category === "bills") iconClass = "fa-file-invoice-dollar";
            else if (doc.category === "education") iconClass = "fa-graduation-cap";
            else if (doc.category === "identity") iconClass = "fa-id-card";
            else if (doc.category === "receipts") iconClass = "fa-receipt";

            card.innerHTML = `
                <div class="modern-doc-header">
                    <i class="fa-solid ${iconClass}"></i>
                    <h4>${doc.filename}</h4>
                </div>
                <div class="modern-doc-meta">
                    <div><strong>Category:</strong> <span>${doc.category}</span></div>
                    <div><strong>Party:</strong> <span>${name}</span></div>
                    <div><strong>Date:</strong> <span>${date}</span></div>
                    <div><strong>Amount:</strong> <span>${amount}</span></div>
                </div>
                <div class="modern-doc-summary">${summary}</div>
                <a class="modern-doc-btn" href="/static/documents/${doc.category}/${doc.filename}" target="_blank">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Open Document
                </a>
            `;
            documentsContainer.appendChild(card);
        });
    }

    docSearch.addEventListener("keyup", (e) => {
        loadDocuments(e.target.value.trim());
    });

    filterPills.forEach(btn => {
        btn.addEventListener("click", () => {
            filterPills.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activeCategory = btn.getAttribute("data-cat");
            loadDocuments();
        });
    });

    // ==========================================
    // WHATSAPP MOCK SIMULATOR
    // ==========================================
    const waTextInput = document.getElementById("wa-text-input");
    const waSendBtn = document.getElementById("wa-send-btn");
    const waFileUpload = document.getElementById("wa-file-upload");
    const phoneChatLogs = document.getElementById("phone-chat-logs");
    const webhookResponseDisplay = document.getElementById("webhook-response-display");
    let activeWaFile = null;

    waFileUpload.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            activeWaFile = e.target.files[0];
            document.querySelector(".wa-add-btn").style.color = "var(--accent-cherry)";
        }
    });

    async function sendWaMessage() {
        const text = waTextInput.value.trim();
        if (!text && !activeWaFile) return;

        waTextInput.value = "";
        
        const inboundDiv = document.createElement("div");
        inboundDiv.className = "wa-msg inbound";
        
        if (activeWaFile) {
            if (activeWaFile.type.startsWith("image/")) {
                const url = URL.createObjectURL(activeWaFile);
                inboundDiv.innerHTML = `<img src="${url}"><p>${text}</p>`;
            } else {
                inboundDiv.innerHTML = `<p><i class="fa-solid fa-file"></i> ${activeWaFile.name}</p><p>${text}</p>`;
            }
        } else {
            inboundDiv.innerHTML = `<p>${text}</p>`;
        }
        
        phoneChatLogs.appendChild(inboundDiv);
        phoneChatLogs.scrollTop = phoneChatLogs.scrollHeight;

        const formData = new FormData();
        formData.append("From", "whatsapp:+919876543210");
        formData.append("Body", text);
        if (activeWaFile) {
            formData.append("media", activeWaFile);
        }

        activeWaFile = null;
        document.querySelector(".wa-add-btn").style.color = "#8696a0";
        waFileUpload.value = "";

        webhookResponseDisplay.textContent = "Delivering POST payload to webhook endpoint /api/webhook/whatsapp...";
        
        try {
            const res = await fetch("/api/webhook/whatsapp", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            
            webhookResponseDisplay.textContent = JSON.stringify(data, null, 2);
            
            const outboundDiv = document.createElement("div");
            outboundDiv.className = "wa-msg outbound";
            outboundDiv.innerHTML = `<p>${data.agent_reply || "Webhook payload successfully parsed."}</p>`;
            phoneChatLogs.appendChild(outboundDiv);
            phoneChatLogs.scrollTop = phoneChatLogs.scrollHeight;

            if (data.steps && data.steps.length > 0) {
                const waStepsGroup = document.createElement("div");
                waStepsGroup.className = "agent-steps-group";
                
                const waHeader = document.createElement("div");
                waHeader.className = "msg-bubble system";
                waHeader.innerHTML = `
                    <div class="msg-avatar">🍒</div>
                    <div class="msg-text">
                        <strong>Cherry:</strong> Webhook request executed agent reasoning steps.
                    </div>
                `;
                chatMessages.appendChild(waHeader);
                chatMessages.appendChild(waStepsGroup);
                
                data.steps.forEach(step => {
                    if (step.type === "thought") {
                        appendStepCard(waStepsGroup, "thought", "Thought", step.content);
                    } else if (step.type === "action") {
                        appendStepCard(waStepsGroup, "action", `Action: ${step.tool}`, JSON.stringify(step.input, null, 2));
                    } else if (step.type === "observation") {
                        appendStepCard(waStepsGroup, "observation", "Observation Output", step.content);
                    }
                });
                
                loadDocuments();
            }
        } catch (err) {
            webhookResponseDisplay.textContent = `Webhook delivery failed: ${err.message}`;
        }
    }

    waSendBtn.addEventListener("click", sendWaMessage);
    waTextInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendWaMessage();
    });

    // ==========================================
    // WORKSPACE TREE EXPLORER
    // ==========================================
    const workspaceTree = document.getElementById("workspace-tree");
    const refreshWorkspaceBtn = document.getElementById("refresh-workspace-btn");

    async function loadWorkspaceTree() {
        workspaceTree.innerHTML = "Loading files...";
        try {
            const res = await fetch("/api/workspace/files");
            const files = await res.json();
            
            workspaceTree.innerHTML = "";
            if (files.length === 0) {
                workspaceTree.innerHTML = "Workspace is empty.";
                return;
            }
            
            files.forEach(filepath => {
                const item = document.createElement("div");
                item.className = "workspace-item";
                
                const ext = filepath.split('.').pop().toLowerCase();
                let iconClass = "fa-file";
                let classType = "file";
                if (["py"].includes(ext)) { iconClass = "fa-file-code"; classType = "py"; }
                else if (["html"].includes(ext)) { iconClass = "fa-file-code"; classType = "html"; }
                else if (["css"].includes(ext)) { iconClass = "fa-file-code"; classType = "css"; }
                else if (["js"].includes(ext)) { iconClass = "fa-file-code"; classType = "js"; }
                else if (["jpg", "jpeg", "png", "webp"].includes(ext)) { iconClass = "fa-file-image"; }
                else if (ext === "pdf") { iconClass = "fa-file-pdf"; }
                
                item.className = `workspace-item ${classType}`;
                item.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${filepath}</span>`;
                workspaceTree.appendChild(item);
            });
        } catch (err) {
            workspaceTree.innerHTML = `Error loading workspace files: ${err.message}`;
        }
    }

    refreshWorkspaceBtn.addEventListener("click", loadWorkspaceTree);

    loadDocuments();
});
