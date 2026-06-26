document.addEventListener("DOMContentLoaded", () => {
    let activeConversationId = localStorage.getItem("activeConversationId") || "default";

    // Agent Settings Modal Logic
    const settingsBtn = document.getElementById("settings-btn");
    const settingsModal = document.getElementById("settings-modal");
    const settingsCloseBtn = document.getElementById("settings-close-btn");
    const settingsCancelBtn = document.getElementById("settings-cancel-btn");
    const settingsSaveBtn = document.getElementById("settings-save-btn");

    const modelInput = document.getElementById("settings-model");
    const tempInput = document.getElementById("settings-temperature");
    const tempDisplay = document.getElementById("temp-val-display");
    const userNameInput = document.getElementById("settings-user-name");
    const systemPromptInput = document.getElementById("settings-system-prompt");

    let currentUserName = "Vishnu";

    async function loadUserProfile() {
        try {
            const res = await fetch("/api/profile");
            const data = await res.json();
            if (data && data.name) {
                currentUserName = data.name;
                const nameHeader = document.querySelector(".user-info h4");
                const avatarDiv = document.querySelector(".user-avatar");
                if (nameHeader) nameHeader.textContent = currentUserName;
                if (avatarDiv) avatarDiv.textContent = currentUserName.charAt(0).toUpperCase();
            }
        } catch (err) {
            console.error("Error loading user profile:", err);
        }
    }

    function loadSettingsIntoInputs() {
        modelInput.value = localStorage.getItem("settings_model") || "";
        const savedTemp = localStorage.getItem("settings_temperature") || "0.7";
        tempInput.value = savedTemp;
        tempDisplay.textContent = savedTemp;
        systemPromptInput.value = localStorage.getItem("settings_system_prompt") || "";
        if (userNameInput) {
            userNameInput.value = currentUserName;
        }
    }

    if (settingsBtn && settingsModal) {
        settingsBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            loadSettingsIntoInputs();
            settingsModal.style.display = "flex";
        });

        const userProfile = document.querySelector(".user-profile");
        if (userProfile) {
            userProfile.addEventListener("click", (e) => {
                loadSettingsIntoInputs();
                settingsModal.style.display = "flex";
            });
        }

        const sidebarFooter = document.querySelector(".sidebar-footer");
        if (sidebarFooter) {
            sidebarFooter.addEventListener("click", (e) => {
                if (e.target.closest("#settings-btn")) return;
                loadSettingsIntoInputs();
                settingsModal.style.display = "flex";
            });
        }

        const closeSettingsModal = () => {
            settingsModal.style.display = "none";
        };

        if (settingsCloseBtn) settingsCloseBtn.addEventListener("click", closeSettingsModal);
        if (settingsCancelBtn) settingsCancelBtn.addEventListener("click", closeSettingsModal);

        settingsModal.addEventListener("click", (e) => {
            if (e.target === settingsModal) {
                closeSettingsModal();
            }
        });

        if (tempInput && tempDisplay) {
            tempInput.addEventListener("input", (e) => {
                tempDisplay.textContent = e.target.value;
            });
        }

        if (settingsSaveBtn) {
            settingsSaveBtn.addEventListener("click", async () => {
                localStorage.setItem("settings_model", modelInput.value.trim());
                localStorage.setItem("settings_temperature", tempInput.value);
                localStorage.setItem("settings_system_prompt", systemPromptInput.value.trim());
                
                const newName = userNameInput ? userNameInput.value.trim() : "";
                if (newName) {
                    try {
                        await fetch("/api/profile", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ name: newName })
                        });
                        await loadUserProfile();
                    } catch (err) {
                        console.error("Error saving profile name:", err);
                    }
                }
                closeSettingsModal();
            });
        }
    }

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
            } else if (tabId === "voice-chat") {
                loadVoiceConfig();
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
        const conversationId = activeConversationId;
        let url = `/api/chat?prompt=${encodedPrompt}&conversation_id=${conversationId}`;
        if (attachmentPath) {
            url += `&attachment_rel_path=${encodeURIComponent(attachmentPath)}`;
        }
        const voiceChatToggle = document.getElementById("voice-chat-toggle");
        if (voiceChatToggle && voiceChatToggle.checked) {
            url += `&voice_mode=true`;
        }

        const savedModel = localStorage.getItem("settings_model") || "";
        const savedTemp = localStorage.getItem("settings_temperature") || "";
        const savedSystemPrompt = localStorage.getItem("settings_system_prompt") || "";

        if (savedModel) {
            url += `&model=${encodeURIComponent(savedModel)}`;
        }
        if (savedTemp) {
            url += `&temperature=${encodeURIComponent(savedTemp)}`;
        }
        if (savedSystemPrompt) {
            url += `&system_instruction=${encodeURIComponent(savedSystemPrompt)}`;
        }

        if (activeEventSource) {
            activeEventSource.close();
        }

        // Create thinking indicator
        const thinkingDiv = document.createElement("div");
        thinkingDiv.className = "msg-bubble assistant";
        thinkingDiv.id = "cherry-thinking-indicator";
        thinkingDiv.innerHTML = `
            <div class="msg-avatar">🍒</div>
            <div class="msg-text">
                <div class="thinking-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(thinkingDiv);

        // ── Single live steps dropdown ─────────────────────────
        // Created immediately; steps are appended live.
        // Header updates from "Working…" to summary on final answer.
        const liveDropdown = document.createElement("div");
        liveDropdown.className = "steps-dropdown-wrapper";

        const liveIcon  = document.createElement("i");
        liveIcon.className = "fa-solid fa-circle-notch fa-spin";

        const liveLabel = document.createElement("span");
        liveLabel.className = "steps-toggle-label";
        liveLabel.textContent = "Working…";

        const liveChevron = document.createElement("i");
        liveChevron.className = "fa-solid fa-chevron-down steps-chevron";

        const liveToggle = document.createElement("button");
        liveToggle.className = "steps-dropdown-toggle working";
        liveToggle.append(liveIcon, liveLabel, liveChevron);

        const liveBody = document.createElement("div");
        liveBody.className = "steps-dropdown-body";
        liveBody.style.display = "none";  // collapsed by default; user taps to open

        liveToggle.addEventListener("click", () => {
            const isOpen = liveBody.style.display !== "none";
            liveBody.style.display = isOpen ? "none" : "block";
            liveToggle.classList.toggle("open", !isOpen);
        });

        liveDropdown.appendChild(liveToggle);
        liveDropdown.appendChild(liveBody);
        chatMessages.insertBefore(liveDropdown, thinkingDiv);

        activeEventSource = new EventSource(url);
        
        activeEventSource.onmessage = (event) => {
            const step = JSON.parse(event.data);
            
            if (step.type === "status") {
                updateLiveStatus(step.content);
                if (step.content === "Cherry is speaking...") {
                    if (typeof startVoiceVisualizer === "function") {
                        startVoiceVisualizer();
                    }
                }

            } else if (step.type === "thought") {
                liveLabel.textContent = "Thinking…";
                appendStepToLiveBody(liveBody, "thought", "Thought", step.content);

            } else if (step.type === "action") {
                const argsStr = JSON.stringify(step.input, null, 2);
                liveLabel.textContent = `Running: ${step.tool}`;
                appendStepToLiveBody(liveBody, "action", `Action: ${step.tool}`, `Arguments:\n${argsStr}`);

            } else if (step.type === "observation") {
                liveLabel.textContent = "Processing result…";
                appendStepToLiveBody(liveBody, "observation", "Observation", step.content);

            } else if (step.type === "final_answer") {
                thinkingDiv.remove();
                if (typeof stopVoiceVisualizer === "function") {
                    stopVoiceVisualizer();
                }

                // Convert to summary state
                const totalSteps   = liveBody.querySelectorAll(".step-card-inner").length;
                const totalActions = liveBody.querySelectorAll(".step-card-inner.action").length;

                if (totalSteps > 0) {
                    // Swap spinner for circle-nodes icon
                    liveIcon.className = "fa-solid fa-circle-nodes";
                    liveLabel.textContent = totalActions > 0
                        ? `${totalActions} action${totalActions > 1 ? "s" : ""} taken · ${totalSteps} step${totalSteps > 1 ? "s" : ""}`
                        : `${totalSteps} reasoning step${totalSteps > 1 ? "s" : ""}`;
                    liveToggle.classList.remove("working");
                    // Collapse it after completion
                    liveBody.style.display = "none";
                    liveToggle.classList.remove("open");
                } else {
                    // No visible steps — remove the dropdown entirely
                    liveDropdown.remove();
                }

                appendMessage("assistant", step.content);
                updateLiveStatus("Cherry is Active");
                activeEventSource.close();
                chatMessages.scrollTop = chatMessages.scrollHeight;
                loadUserProfile();
                loadConversations();

            } else if (step.type === "error") {
                thinkingDiv.remove();
                liveDropdown.remove();
                if (typeof stopVoiceVisualizer === "function") {
                    stopVoiceVisualizer();
                }
                appendMessage("system", `Engine Error: ${step.content}`);
                updateLiveStatus("Cherry is Active");
                activeEventSource.close();
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        };

        activeEventSource.onerror = () => {
            thinkingDiv.remove();
            liveDropdown.remove();
            if (typeof stopVoiceVisualizer === "function") {
                stopVoiceVisualizer();
            }
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

        let renderedContent = content;
        if (typeof marked !== 'undefined') {
            try {
                marked.setOptions({
                    breaks: true,
                    gfm: true
                });
                renderedContent = marked.parse(content);
            } catch (e) {
                console.error("Failed to parse markdown:", e);
                renderedContent = `<div>${content.replace(/\n/g, '<br>')}</div>`;
            }
        } else {
            renderedContent = `<div>${content.replace(/\n/g, '<br>')}</div>`;
        }

        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-text">
                <div class="markdown-body">${renderedContent}</div>
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

    function buildStepsDropdown(steps) {
        const stepCount = steps.length;
        const actionCount = steps.filter(s => s.type === "action").length;
        const label = actionCount > 0
            ? `${actionCount} action${actionCount > 1 ? 's' : ''} taken · ${stepCount} step${stepCount > 1 ? 's' : ''}`
            : `${stepCount} reasoning step${stepCount > 1 ? 's' : ''}`;

        const wrapper = document.createElement("div");
        wrapper.className = "steps-dropdown-wrapper";

        const toggle = document.createElement("button");
        toggle.className = "steps-dropdown-toggle";
        toggle.innerHTML = `
            <i class="fa-solid fa-circle-nodes"></i>
            <span>${label}</span>
            <i class="fa-solid fa-chevron-down steps-chevron"></i>
        `;

        const body = document.createElement("div");
        body.className = "steps-dropdown-body";
        body.style.display = "none";

        steps.forEach(step => {
            const card = document.createElement("div");
            card.className = `step-card-inner ${step.type}`;
            const icon = step.type === 'thought' ? 'fa-lightbulb' : step.type === 'action' ? 'fa-gears' : 'fa-list-check';
            card.innerHTML = `
                <div class="step-card-header">
                    <i class="fa-solid ${icon}"></i>
                    <span>${step.title}</span>
                </div>
                <pre class="step-card-body">${escapeHtml(step.content)}</pre>
            `;
            body.appendChild(card);
        });

        toggle.addEventListener("click", () => {
            const isOpen = body.style.display !== "none";
            body.style.display = isOpen ? "none" : "block";
            toggle.classList.toggle("open", !isOpen);
        });

        wrapper.appendChild(toggle);
        wrapper.appendChild(body);
        return wrapper;
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    // Legacy appendStepCard kept for WhatsApp tab compatibility
    function appendStepCard(container, type, title, content) {
        const card = document.createElement("div");
        card.className = `step-card-inner ${type}`;
        const icon = type === 'thought' ? 'fa-lightbulb' : type === 'action' ? 'fa-gears' : 'fa-list-check';
        card.innerHTML = `
            <div class="step-card-header">
                <i class="fa-solid ${icon}"></i>
                <span>${title}</span>
            </div>
            <pre class="step-card-body">${escapeHtml(content)}</pre>
        `;
        container.appendChild(card);
    }

    // Append a step card to the live dropdown body in real time
    function appendStepToLiveBody(bodyEl, type, title, content) {
        const card = document.createElement("div");
        card.className = `step-card-inner ${type}`;
        const icon = type === 'thought' ? 'fa-lightbulb' : type === 'action' ? 'fa-gears' : 'fa-list-check';
        card.innerHTML = `
            <div class="step-card-header">
                <i class="fa-solid ${icon}"></i>
                <span>${title}</span>
            </div>
            <pre class="step-card-body">${escapeHtml(content)}</pre>
        `;
        bodyEl.appendChild(card);
        // If body is open, scroll chat to show new step
        if (bodyEl.style.display !== "none") {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
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

    function getGreetingHtml(name) {
        const displayName = name || "there";
        return `
            <div class="msg-bubble system">
                <div class="msg-avatar">🍒</div>
                <div class="msg-text">
                    Hi ${displayName}! How can I help you today?
                </div>
            </div>
        `;
    }

    async function loadChatHistory() {
        chatMessages.innerHTML = "";
        try {
            const res = await fetch(`/api/chat/history?conversation_id=${activeConversationId}`);
            const history = await res.json();
            if (history && history.length > 0) {
                history.forEach(msg => {
                    appendMessage(msg.role, msg.content);
                });
            } else {
                chatMessages.innerHTML = getGreetingHtml(currentUserName);
            }
        } catch (err) {
            console.error("Error loading chat history:", err);
            chatMessages.innerHTML = getGreetingHtml(currentUserName);
        }
    }

    async function resetChat() {
        if (confirm("Are you sure you want to clear the chat history?")) {
            try {
                await fetch(`/api/chat/history?conversation_id=${activeConversationId}`, {
                    method: "DELETE"
                });
                loadChatHistory();
            } catch (err) {
                console.error("Error resetting chat:", err);
            }
        }
    }
    window.resetChat = resetChat;

    const sessionList = document.getElementById("session-list");
    const newChatBtn = document.getElementById("new-chat-btn");

    async function loadConversations() {
        try {
            const res = await fetch("/api/conversations");
            const conversations = await res.json();
            
            if (conversations.length === 0) {
                await fetch("/api/conversations", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ id: "default", title: "Default Session" })
                });
                activeConversationId = "default";
                localStorage.setItem("activeConversationId", "default");
                loadConversations();
                return;
            }

            const activeExists = conversations.some(c => c.id === activeConversationId);
            if (!activeExists) {
                activeConversationId = conversations[0].id;
                localStorage.setItem("activeConversationId", activeConversationId);
            }

            renderConversationList(conversations);
        } catch (err) {
            console.error("Error loading conversations:", err);
        }
    }

    function showConfirmModal(message, onConfirm) {
        const overlay = document.createElement("div");
        overlay.style.position = "fixed";
        overlay.style.top = "0";
        overlay.style.left = "0";
        overlay.style.width = "100vw";
        overlay.style.height = "100vh";
        overlay.style.backgroundColor = "rgba(0, 0, 0, 0.6)";
        overlay.style.backdropFilter = "blur(4px)";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.style.zIndex = "1000";
        
        const modal = document.createElement("div");
        modal.style.backgroundColor = "var(--bg-panel)";
        modal.style.border = "1px solid var(--border-color)";
        modal.style.borderRadius = "12px";
        modal.style.padding = "1.5rem";
        modal.style.maxWidth = "400px";
        modal.style.width = "90%";
        modal.style.boxShadow = "0 20px 40px rgba(0, 0, 0, 0.6)";
        modal.style.display = "flex";
        modal.style.flexDirection = "column";
        modal.style.gap = "1rem";
        
        modal.innerHTML = `
            <div style="font-size: 0.95rem; line-height: 1.5; color: var(--text-main);">${message}</div>
            <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem;">
                <button id="modal-cancel-btn" style="background: none; border: 1px solid var(--border-color); color: var(--text-muted); padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 500;">Cancel</button>
                <button id="modal-confirm-btn" style="background-color: var(--accent-cherry); border: none; color: white; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 500;">Delete</button>
            </div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        modal.querySelector("#modal-cancel-btn").addEventListener("click", () => {
            overlay.remove();
        });
        
        modal.querySelector("#modal-confirm-btn").addEventListener("click", () => {
            overlay.remove();
            onConfirm();
        });
    }

    function renderConversationList(conversations) {
        sessionList.innerHTML = "";
        conversations.forEach(conv => {
            const item = document.createElement("div");
            item.className = `session-item ${conv.id === activeConversationId ? 'active' : ''}`;
            item.setAttribute("data-id", conv.id);
            
            const pinIndicator = conv.pinned ? ` <i class="fa-solid fa-thumbtack pinned-icon" style="font-size: 0.75rem; margin-left: 0.4rem;"></i>` : "";

            item.innerHTML = `
                <span class="session-title">${conv.title}${pinIndicator}</span>
                <div class="session-menu-container">
                    <button class="session-menu-btn"><i class="fa-solid fa-ellipsis-vertical"></i></button>
                    <div class="session-menu-dropdown">
                        <button class="menu-action-share"><i class="fa-solid fa-share-nodes"></i> Share conversation</button>
                        <button class="menu-action-pin"><i class="fa-solid fa-thumbtack"></i> ${conv.pinned ? 'Unpin' : 'Pin'}</button>
                        <button class="menu-action-rename"><i class="fa-solid fa-pen"></i> Rename</button>
                        <button class="menu-action-delete"><i class="fa-solid fa-trash"></i> Delete</button>
                    </div>
                </div>
            `;

            item.addEventListener("click", (e) => {
                if (e.target.closest(".session-menu-container")) return;
                selectConversation(conv.id);
            });

            const menuContainer = item.querySelector(".session-menu-container");
            const menuBtn = item.querySelector(".session-menu-btn");
            
            menuBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                document.querySelectorAll(".session-menu-container").forEach(c => {
                    if (c !== menuContainer) c.classList.remove("open");
                });
                menuContainer.classList.toggle("open");
            });

            item.querySelector(".menu-action-share").addEventListener("click", (e) => {
                e.stopPropagation();
                menuContainer.classList.remove("open");
                alert("Share link copied to clipboard!");
            });

            item.querySelector(".menu-action-rename").addEventListener("click", (e) => {
                e.stopPropagation();
                menuContainer.classList.remove("open");
                
                const titleSpan = item.querySelector(".session-title");
                const currentTitle = conv.title;
                
                const input = document.createElement("input");
                input.type = "text";
                input.className = "session-rename-input";
                input.value = currentTitle;
                
                input.style.width = "100%";
                input.style.background = "var(--bg-input)";
                input.style.border = "1px solid var(--accent-cherry)";
                input.style.color = "var(--text-main)";
                input.style.borderRadius = "4px";
                input.style.padding = "0.2rem 0.4rem";
                input.style.fontSize = "0.85rem";
                input.style.outline = "none";
                
                titleSpan.replaceWith(input);
                input.focus();
                input.select();
                
                let isSaving = false;
                
                async function saveRename() {
                    if (isSaving) return;
                    isSaving = true;
                    const newTitle = input.value.trim();
                    if (newTitle && newTitle !== currentTitle) {
                        try {
                            await fetch(`/api/conversations/${conv.id}`, {
                                method: "PUT",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ title: newTitle })
                            });
                            loadConversations();
                        } catch (err) {
                            console.error("Error renaming:", err);
                            input.replaceWith(titleSpan);
                        }
                    } else {
                        input.replaceWith(titleSpan);
                    }
                }
                
                input.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        saveRename();
                    } else if (e.key === "Escape") {
                        isSaving = true;
                        input.replaceWith(titleSpan);
                    }
                });
                
                input.addEventListener("blur", () => {
                    setTimeout(saveRename, 100);
                });
            });

            item.querySelector(".menu-action-pin").addEventListener("click", async (e) => {
                e.stopPropagation();
                menuContainer.classList.remove("open");
                try {
                    await fetch(`/api/conversations/${conv.id}`, {
                        method: "PUT",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ pinned: !conv.pinned })
                    });
                    loadConversations();
                } catch (err) {
                    console.error("Error pinning/unpinning conversation:", err);
                }
            });

            item.querySelector(".menu-action-delete").addEventListener("click", (e) => {
                e.stopPropagation();
                menuContainer.classList.remove("open");
                
                showConfirmModal(
                    `Are you sure you want to delete the chat "${conv.title}"?`,
                    async () => {
                        try {
                            await fetch(`/api/conversations/${conv.id}`, {
                                method: "DELETE"
                            });
                            if (conv.id === activeConversationId) {
                                localStorage.removeItem("activeConversationId");
                            }
                            loadConversations().then(() => {
                                selectConversation(activeConversationId);
                            });
                        } catch (err) {
                            console.error("Error deleting conversation:", err);
                        }
                    }
                );
            });

            sessionList.appendChild(item);
        });
    }

    function selectConversation(id) {
        activeConversationId = id;
        localStorage.setItem("activeConversationId", id);
        
        document.querySelectorAll(".session-item").forEach(item => {
            if (item.getAttribute("data-id") === id) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
        
        loadChatHistory();
    }

    newChatBtn.addEventListener("click", async () => {
        const id = "chat_" + Date.now();
        const title = "New Chat";
        try {
            await fetch("/api/conversations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id, title })
            });
            activeConversationId = id;
            localStorage.setItem("activeConversationId", id);
            await loadConversations();
            selectConversation(id);
        } catch (err) {
            console.error("Error creating new chat:", err);
        }
    });

    // ==========================================
    // WHATSAPP CONNECTION BRIDGE CONTROL PANEL
    // ==========================================
    const waStatusText = document.getElementById("wa-status-text");
    const waQrContainer = document.getElementById("wa-qr-container");
    const waQrImg = document.getElementById("wa-qr-img");
    const waStartBtn = document.getElementById("wa-start-btn");
    const waStopBtn = document.getElementById("wa-stop-btn");
    let waPollInterval = null;

    async function checkWhatsappStatus() {
        try {
            const res = await fetch("/api/whatsapp/status");
            const data = await res.json();

            if (data.running) {
                waStartBtn.style.display = "none";
                waStopBtn.style.display = "inline-block";
                
                if (data.status === "scanning") {
                    if (data.qr) {
                        waStatusText.innerHTML = 'Status: <span style="color: #ff9f0a; font-weight: bold;">Scan QR Code Below 📱</span>';
                        waQrImg.src = data.qr;
                        waQrContainer.style.display = "flex";
                    } else {
                        waQrContainer.style.display = "none";
                        waStatusText.innerHTML = 'Status: <span style="color: #ff9f0a;">Starting WhatsApp Client...</span>';
                    }
                } else if (data.status === "connected") {
                    waStatusText.innerHTML = 'Status: <span style="color: #25d366; font-weight: bold;">Connected & Active ✅</span>';
                    waQrContainer.style.display = "none";
                }
            } else {
                waStatusText.innerHTML = 'Status: <span style="color: var(--text-muted);">Disconnected ❌</span>';
                waQrContainer.style.display = "none";
                waStartBtn.style.display = "inline-block";
                waStopBtn.style.display = "none";
            }
        } catch (err) {
            console.error("Error fetching WhatsApp status:", err);
        }
    }

    if (waStartBtn && waStopBtn) {
        waStartBtn.addEventListener("click", async () => {
            waStatusText.innerHTML = 'Status: <span style="color: #ff9f0a;">Initializing...</span>';
            waStartBtn.disabled = true;
            try {
                await fetch("/api/whatsapp/start", { method: "POST" });
                setTimeout(checkWhatsappStatus, 500);
            } catch (err) {
                console.error(err);
            } finally {
                waStartBtn.disabled = false;
            }
        });

        waStopBtn.addEventListener("click", async () => {
            waStatusText.innerHTML = 'Status: <span style="color: var(--text-muted);">Stopping...</span>';
            waStopBtn.disabled = true;
            try {
                await fetch("/api/whatsapp/stop", { method: "POST" });
                setTimeout(checkWhatsappStatus, 500);
            } catch (err) {
                console.error(err);
            } finally {
                waStopBtn.disabled = false;
            }
        });

        // Poll status every 2 seconds while the settings modal is open
        const observer = new MutationObserver(() => {
            if (settingsModal.style.display === "flex") {
                checkWhatsappStatus();
                if (!waPollInterval) {
                    waPollInterval = setInterval(checkWhatsappStatus, 2000);
                }
            } else {
                if (waPollInterval) {
                    clearInterval(waPollInterval);
                    waPollInterval = null;
                }
            }
        });
        observer.observe(settingsModal, { attributes: true, attributeFilter: ["style"] });
    }

    document.addEventListener("click", () => {
        document.querySelectorAll(".session-menu-container").forEach(c => {
            c.classList.remove("open");
        });
    });

    // ==========================================
    // PANEL COLLAPSE TOGGLES
    // ==========================================
    const cherryApp      = document.querySelector(".cherry-app");
    const mainBody       = document.querySelector(".main-body");
    const sidebarBtn     = document.getElementById("sidebar-toggle-btn");
    const toolsBtn       = document.getElementById("tools-toggle-btn");
    const toolsSection   = document.getElementById("tools-section");
    const resizeHandle   = document.getElementById("resize-handle");

    function setSidebarCollapsed(collapsed) {
        cherryApp.classList.toggle("sidebar-collapsed", collapsed);
        if (sidebarBtn) sidebarBtn.classList.toggle("panel-hidden", collapsed);
        localStorage.setItem("sidebar_collapsed", collapsed ? "1" : "0");
    }

    function setToolsCollapsed(collapsed) {
        mainBody.classList.toggle("tools-collapsed", collapsed);
        if (toolsBtn) toolsBtn.classList.toggle("panel-hidden", collapsed);
        localStorage.setItem("tools_collapsed", collapsed ? "1" : "0");
    }

    // Restore persisted states
    setSidebarCollapsed(localStorage.getItem("sidebar_collapsed") === "1");
    setToolsCollapsed(localStorage.getItem("tools_collapsed") === "1");

    // Restore persisted tools width
    const savedToolsWidth = localStorage.getItem("tools_width");
    if (savedToolsWidth && toolsSection) {
        toolsSection.style.flex = `0 0 ${savedToolsWidth}px`;
    }

    if (sidebarBtn) {
        sidebarBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            setSidebarCollapsed(!cherryApp.classList.contains("sidebar-collapsed"));
        });
    }

    if (toolsBtn) {
        toolsBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            setToolsCollapsed(!mainBody.classList.contains("tools-collapsed"));
        });
    }

    // ── Drag-to-resize the tools panel ──────────────────────
    if (resizeHandle && toolsSection) {
        let isResizing  = false;
        let startX      = 0;
        let startWidth  = 0;

        resizeHandle.addEventListener("mousedown", (e) => {
            e.preventDefault();
            isResizing = true;
            startX     = e.clientX;
            startWidth = toolsSection.offsetWidth;
            resizeHandle.classList.add("dragging");
            document.body.style.cursor     = "col-resize";
            document.body.style.userSelect = "none";
        });

        document.addEventListener("mousemove", (e) => {
            if (!isResizing) return;
            const dx       = startX - e.clientX;          // dragging left → tools grows
            const minW     = 200;
            const maxW     = window.innerWidth * 0.68;
            const newWidth = Math.max(minW, Math.min(maxW, startWidth + dx));
            toolsSection.style.flex = `0 0 ${newWidth}px`;
            localStorage.setItem("tools_width", newWidth);
        });

        document.addEventListener("mouseup", () => {
            if (isResizing) {
                isResizing = false;
                resizeHandle.classList.remove("dragging");
                document.body.style.cursor     = "";
                document.body.style.userSelect = "";
            }
        });
    }

    loadDocuments();
    loadUserProfile().then(() => {
        loadConversations().then(() => {
            loadChatHistory();
        });
    });

    // === VOICE CHAT LOGIC ===
    const voiceStatusText = document.getElementById("voice-status-text");
    const voiceStatusIndicator = document.getElementById("voice-status-indicator");
    const voiceApiUrlInput = document.getElementById("voice-api-url-input");
    const saveVoiceUrlBtn = document.getElementById("save-voice-url-btn");
    const voiceChatToggle = document.getElementById("voice-chat-toggle");
    const voiceActingLabel = document.getElementById("voice-acting-label");
    const voiceActingSub = document.getElementById("voice-acting-sub");
    const waveBars = document.querySelectorAll(".wave-bar");

    async function loadVoiceConfig() {
        try {
            const res = await fetch("/api/voice/config");
            const data = await res.json();
            if (data && data.voice_api_url) {
                voiceApiUrlInput.value = data.voice_api_url;
                if (voiceStatusText) voiceStatusText.textContent = "Ready";
                if (voiceStatusIndicator) {
                    voiceStatusIndicator.style.background = "#10b981"; // green
                    voiceStatusIndicator.style.boxShadow = "0 0 8px #10b981";
                }
            }
        } catch (err) {
            console.error("Error loading voice config:", err);
            if (voiceStatusText) voiceStatusText.textContent = "Unreachable";
            if (voiceStatusIndicator) {
                voiceStatusIndicator.style.background = "#ef4444"; // red
                voiceStatusIndicator.style.boxShadow = "0 0 8px #ef4444";
            }
        }
    }

    if (saveVoiceUrlBtn) {
        saveVoiceUrlBtn.addEventListener("click", async () => {
            const voice_api_url = voiceApiUrlInput.value.trim();
            if (!voice_api_url) return;
            
            saveVoiceUrlBtn.textContent = "Saving...";
            saveVoiceUrlBtn.style.opacity = "0.7";
            try {
                const res = await fetch("/api/voice/config", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ voice_api_url })
                });
                const data = await res.json();
                if (data.status === "success") {
                    saveVoiceUrlBtn.textContent = "Saved!";
                    if (voiceStatusText) voiceStatusText.textContent = "Configured";
                    if (voiceStatusIndicator) {
                        voiceStatusIndicator.style.background = "#10b981";
                        voiceStatusIndicator.style.boxShadow = "0 0 8px #10b981";
                    }
                } else {
                    alert("Error saving: " + data.message);
                }
            } catch (err) {
                console.error("Error saving voice config:", err);
                alert("Failed to save voice configuration");
            } finally {
                setTimeout(() => {
                    saveVoiceUrlBtn.textContent = "Save";
                    saveVoiceUrlBtn.style.opacity = "1";
                }, 1500);
            }
        });
    }

    function startVoiceVisualizer() {
        if (voiceActingLabel) voiceActingLabel.textContent = "Cherry is Speaking";
        if (voiceActingSub) voiceActingSub.textContent = "Audio stream active, playing output speaker audio...";
        waveBars.forEach(bar => {
            bar.classList.add("speaking");
        });
        if (voiceStatusText) voiceStatusText.textContent = "Speaking";
        if (voiceStatusIndicator) {
            voiceStatusIndicator.style.background = "#3b82f6"; // blue
            voiceStatusIndicator.style.boxShadow = "0 0 8px #3b82f6";
        }
    }

    function stopVoiceVisualizer() {
        if (voiceActingLabel) voiceActingLabel.textContent = "Visualizer Idle";
        if (voiceActingSub) voiceActingSub.textContent = "Activate Voice Mode or send a query to test speech response.";
        waveBars.forEach(bar => {
            bar.classList.remove("speaking");
        });
        if (voiceStatusText) voiceStatusText.textContent = "Ready";
        if (voiceStatusIndicator) {
            voiceStatusIndicator.style.background = "#10b981"; // green
            voiceStatusIndicator.style.boxShadow = "0 0 8px #10b981";
        }
    }

    // Persist voice toggle state
    if (voiceChatToggle) {
        voiceChatToggle.checked = localStorage.getItem("voice_mode_enabled") === "true";
        voiceChatToggle.addEventListener("change", (e) => {
            localStorage.setItem("voice_mode_enabled", e.target.checked);
        });
    }

    window.loadVoiceConfig = loadVoiceConfig;
    window.startVoiceVisualizer = startVoiceVisualizer;
    window.stopVoiceVisualizer = stopVoiceVisualizer;
    
    // Auto-load voice config on page load
    loadVoiceConfig();
});
