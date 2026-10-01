/**
 * MF FAQ Assistant - Frontend JavaScript
 *
 * Handles user interactions, API calls, and response display.
 */

const API_BASE_URL = "http://localhost:8000";

// Generate a unique session ID for conversation memory
function generateSessionId() {
    return "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
}

const SESSION_ID = generateSessionId();

/**
 * Handle Enter key press in input field.
 */
function handleKeyPress(event) {
    if (event.key === "Enter") {
        askQuestion();
    }
}

/**
 * Handle example button click.
 */
function askExample(button) {
    const question = button.textContent.trim();
    document.getElementById("questionInput").value = question;
    askQuestion();
}

/**
 * Send question to API and display answer.
 */
async function askQuestion() {
    const input = document.getElementById("questionInput");
    const question = input.value.trim();

    if (!question) {
        showError("Please enter a question.");
        return;
    }

    // Show loading, hide previous answers
    showLoading(true);
    hideAnswer();
    hideError();

    // Disable send button
    const sendBtn = document.querySelector(".send-btn");
    sendBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ question, session_id: SESSION_ID }),
        });

        const data = await response.json();

        if (!response.ok) {
            // Handle error responses
            const errorMsg = data.detail?.error || data.error || "An error occurred.";
            showError(errorMsg);
            return;
        }

        // Display answer
        displayAnswer(data);

    } catch (error) {
        showError("Failed to connect to server. Make sure the API is running at localhost:8000");
    } finally {
        showLoading(false);
        sendBtn.disabled = false;
    }
}

/**
 * Display the answer with sources.
 */
function displayAnswer(data) {
    const answerArea = document.getElementById("answerArea");
    const answerText = document.getElementById("answerText");
    const sourcesSection = document.getElementById("sourcesSection");
    const sourcesList = document.getElementById("sourcesList");

    // Set answer text
    answerText.textContent = data.answer;

    // Set sources
    sourcesList.innerHTML = "";
    if (data.sources && data.sources.length > 0) {
        data.sources.forEach((source) => {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = source;
            a.textContent = source;
            a.target = "_blank";
            a.rel = "noopener noreferrer";
            li.appendChild(a);
            sourcesList.appendChild(li);
        });
        sourcesSection.style.display = "block";
    } else {
        sourcesSection.style.display = "none";
    }

    // Show answer area
    answerArea.classList.remove("hidden");

    // Scroll to answer
    answerArea.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Show error message.
 */
function showError(message) {
    const errorArea = document.getElementById("errorArea");
    const errorText = document.getElementById("errorText");
    errorText.textContent = message;
    errorArea.classList.remove("hidden");
}

/**
 * Hide error area.
 */
function hideError() {
    document.getElementById("errorArea").classList.add("hidden");
}

/**
 * Hide answer area.
 */
function hideAnswer() {
    document.getElementById("answerArea").classList.add("hidden");
}

/**
 * Show or hide loading indicator.
 */
function showLoading(show) {
    const loading = document.getElementById("loading");
    if (show) {
        loading.classList.remove("hidden");
    } else {
        loading.classList.add("hidden");
    }
}
