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

closeTelegramModal.addEventListener('click', () => {
    telegramModal.style.display = 'none';
});
closeTelegramModalBtn.addEventListener('click', () => {
    telegramModal.style.display = 'none';
});

function animateOnScroll() {
    const elements = document.querySelectorAll('.animate-on-scroll');
    const windowHeight = window.innerHeight;

    elements.forEach(el => {
        const elementTop = el.getBoundingClientRect().top;
        if (elementTop < windowHeight - 50) {
            el.classList.add('visible');
        }
    });
}

window.addEventListener('scroll', animateOnScroll);
window.addEventListener('load', animateOnScroll);

function typeMessage(text, isUser, callback) {
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'message user' : 'message bot';
    messageDiv.textContent = '';
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    let i = 0;
    const speed = 10;

    function type() {
        if (i < text.length) {
            messageDiv.textContent += text.charAt(i);
            i++;
            chatMessages.scrollTop = chatMessages.scrollHeight;
            setTimeout(type, speed);
        } else if (callback) {
            callback();
        }
    }

    type();
}

async function loadHistory() {
    if (!sessionId) {
        typeMessage("Привет! Я TrueWay — ИИ-профориентатор. А как зовут тебя?", false);
        return;
    }

    try {
        if (data.messages && Array.isArray(data.messages)) {
            chatMessages.innerHTML = '';
            data.messages.forEach(msg => {
                if (msg.role !== 'system') {
                    typeMessage(msg.content, msg.role === 'user');
                }
            });
        } else {
            typeMessage("Продолжим разговор?", false);
        }
    } catch (err) {
        console.error("Не удалось загрузить историю", err);
        typeMessage("Не удалось загрузить историю. Но можно продолжить.", false);
    }
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, true);
    userInput.value = '';

    try {
        const payload = { message: text };
        if (sessionId) payload.session_id = sessionId;
        if (telegramId) payload.telegram_id = telegramId;

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
            })
        });

        const data = await response.json();
        if (data.session_id && !sessionId) {
            sessionId = data.session_id;
        }

        addMessage(data.response || data.error, false);
    } catch (error) {
        addMessage("Ошибка подключения к серверу.", false);
        console.error(error);
    }
}

function addMessage(text, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'message user' : 'message bot';
    messageDiv.textContent = text;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') sendMessage();
});

loadHistory();