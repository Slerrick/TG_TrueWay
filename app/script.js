document.addEventListener('DOMContentLoaded', () => {
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

    function getTelegramId() {
        if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
            return 'tg_' + window.Telegram.WebApp.initDataUnsafe.user.id;
        }

        const storedId = sessionStorage.getItem('web_anon_id');
        if (storedId) {
            return storedId;
        }

        const timestamp = new Date().getTime();
        const random = Math.floor(Math.random() * 10000);
        const anonId = 'web_' + timestamp.toString(36) + random.toString(36);

        sessionStorage.setItem('web_anon_id', anonId);
        return anonId;
    }

    const TELEGRAM_ID = getTelegramId();

    function showNotification(message) {
        if (!notification) return;
        notification.textContent = message;
        notification.classList.add('show');
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }

    startButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (consentModal) consentModal.style.display = 'flex';
        });
    });

    closeConsentModal?.addEventListener('click', () => {
        if (consentModal) consentModal.style.display = 'none';
    });

    cancelConsentBtn?.addEventListener('click', () => {
        if (consentModal) consentModal.style.display = 'none';
        showNotification('Вы можете продолжить позже.');
    });

    proceedToTelegramBtn?.addEventListener('click', () => {
        if (!consentCheckbox?.checked) {
            showNotification('Пожалуйста, подтвердите согласие.');
            return;
        }
        if (consentModal) consentModal.style.display = 'none';
        if (telegramModal) telegramModal.style.display = 'flex';
    });

    closeTelegramModal?.addEventListener('click', () => {
        if (telegramModal) telegramModal.style.display = 'none';
    });

    closeTelegramModalBtn?.addEventListener('click', () => {
        if (telegramModal) telegramModal.style.display = 'none';
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

        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            observer.observe(el);
        });
    }

    function addTypingIndicator() {
        removeTypingIndicator();
        const typing = document.createElement('div');
        typing.className = 'message bot';
        typing.id = 'typing-indicator';
        typing.textContent = 'Печатает...';
        chatMessages.appendChild(typing);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    }

    function addMessage(text, isUser) {
        removeTypingIndicator();

        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'message user' : 'message bot';

        if (isUser) {
            messageDiv.textContent = text;
            chatMessages.appendChild(messageDiv);
        } else {
            let i = 0;
            const speed = 18;
            messageDiv.textContent = '';

            const typeWriter = () => {
                if (i < text.length) {
                    messageDiv.textContent += text.charAt(i);
                    i++;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    setTimeout(typeWriter, speed);
                }
            };

            chatMessages.appendChild(messageDiv);
            typeWriter();
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function loadInitialMessage() {
        addMessage("Привет! Я TrueWay — ИИ-профориентатор. А как зовут тебя?", false);
    }

    async function sendMessage() {
        const text = userInput?.value.trim();
        if (!text) return;

        addMessage(text, true);
        userInput.value = '';

        addTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId,
                    telegram_id: TELEGRAM_ID
                })
            });

            const data = await response.json();

            removeTypingIndicator();

            if (data.session_id && !sessionId) {
                sessionId = data.session_id;
            }

            if (data.error) {
                if (data.session_expired) {
                    addMessage(
                        "❌ Сессия с ИИ временно недоступна из-за обновления соединения.\n\n" +
                        "Пожалуйста, начните диалог заново — нажмите кнопку ниже 👇",
                        false
                    );

                    const restartBtn = document.createElement('button');
                    restartBtn.className = 'restart-button';
                    restartBtn.textContent = '🚀 Начать профориентацию заново';
                    restartBtn.onclick = () => {
                        sessionId = null;
                        chatMessages.innerHTML = '';
                        loadInitialMessage();
                    };

                    const btnWrapper = document.createElement('div');
                    btnWrapper.style.textAlign = 'center';
                    btnWrapper.style.marginTop = '10px';
                    btnWrapper.appendChild(restartBtn);

                    chatMessages.appendChild(btnWrapper);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } else {
                    addMessage("❌ " + data.error, false);
                }
            } else {
                const botResponse = data.response || "Неизвестная ошибка";
                addMessage(botResponse, false);
            }

        } catch (error) {
            console.error("Ошибка сети:", error);
            removeTypingIndicator();

            addMessage(
                "🌐 Не удалось подключиться к серверу.\n\n" +
                "Возможно, у вас нет интернета, или сервер временно недоступен.\n" +
                "Попробуйте перезагрузить страницу через несколько минут.",
                false
            );
        }
    }
    sendButton?.addEventListener('click', sendMessage);
    userInput?.addEventListener('keypress', e => {
        if (e.key === 'Enter') sendMessage();
    });

    loadInitialMessage();
    initScrollAnimations();
});