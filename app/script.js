// === ЭЛЕМЕНТЫ DOM ===
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-btn');

const consentModal = document.getElementById('consentModal');
const telegramModal = document.getElementById('telegramModal');
const startButtons = document.querySelectorAll('.start-btn');
const closeConsentModal = document.getElementById('closeConsentModal');
const cancelConsentBtn = document.getElementById('cancelConsentBtn');
const proceedToTelegramBtn = document.getElementById('proceedToTelegramBtn');
const closeTelegramModal = document.getElementById('closeTelegramModal');
const closeTelegramModalBtn = document.getElementById('closeTelegramModalBtn');
const consentCheckbox = document.getElementById('consentCheckbox');
const notification = document.getElementById('notification');

let sessionId = null;

function showNotification(message) {
    notification.textContent = message;
    notification.classList.add('show');
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

startButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        consentModal.style.display = 'flex';
    });
});

closeConsentModal.addEventListener('click', () => {
    consentModal.style.display = 'none';
});

cancelConsentBtn.addEventListener('click', () => {
    consentModal.style.display = 'none';
    showNotification('Вы можете продолжить позже.');
});

proceedToTelegramBtn.addEventListener('click', () => {
    if (!consentCheckbox.checked) {
        showNotification('Пожалуйста, подтвердите согласие.');
        return;
    }
    consentModal.style.display = 'none';
    telegramModal.style.display = 'flex';
});

closeTelegramModal?.addEventListener('click', () => {
    telegramModal.style.display = 'none';
});

closeTelegramModalBtn?.addEventListener('click', () => {
    telegramModal.style.display = 'none';
});

function initScrollAnimations() {
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        }
    );

    document.querySelectorAll('.animate-on-scroll').forEach((el) => {
        observer.observe(el);
    });
}

function addMessage(text, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'message user' : 'message bot';
    messageDiv.textContent = text;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function loadInitialMessage() {
    addMessage("Привет! Я TrueWay — ИИ-профориентатор. А как зовут тебя?", false);
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, true);
    userInput.value = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: sessionId
            })
        });

        const data = await response.json();

        if (data.session_id && !sessionId) {
            sessionId = data.session_id;
        }

        addMessage(data.response || data.error || "Неизвестная ошибка", false);

    } catch (error) {
        console.error("Ошибка сети:", error);
        addMessage("❌ Ошибка подключения к серверу. Проверьте интернет.", false);
    }
}

sendButton?.addEventListener('click', sendMessage);
userInput?.addEventListener('keypress', e => {
    if (e.key === 'Enter') sendMessage();
});

window.addEventListener('load', () => {
    loadInitialMessage();
    initScrollAnimations();
});