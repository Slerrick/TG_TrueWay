import requests
import time
import uuid
import ssl
import os
import socket
from datetime import datetime
from config import GIGACHAT_AUTH_KEY
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import base64

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    print("⚠️ Модуль 'cryptography' не установлен. Установите: pip install cryptography")
    print("   Будет использован fallback через команду 'openssl', если доступна.")


def ensure_certificate(hostname="ngw.devices.sberbank.ru", port=9443, cert_file="sberapi.crt"):
    cert_path = os.path.join(os.path.dirname(__file__), cert_file)

    def download_cert():
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1

        try:
            with socket.create_connection((hostname, port), timeout=10) as sock:
                ssock = context.wrap_socket(sock, server_hostname=hostname)
                ssock.context.check_hostname = False
                ssock.context.verify_mode = ssl.CERT_NONE

                cert_bin = ssock.getpeercert(binary_form=True)
                pem_cert = ssl.DER_cert_to_PEM_cert(cert_bin) # pyright: ignore[reportArgumentType]
                with open(cert_path, 'w') as f:
                    f.write(pem_cert)
                print(f"✅ Сертификат успешно скачан и сохранён: {cert_path}")
            return True
        except Exception as e:
            print(f"❌ Не удалось скачать сертификат: {e}")
            return False

    def get_cert_expiry():
        if not os.path.exists(cert_path):
            return None
        try:
            if HAS_CRYPTOGRAPHY:
                with open(cert_path, 'rb') as f:
                    cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                return cert.not_valid_after_utc.replace(tzinfo=None)
            else:
                result = os.popen(f"openssl x509 -in {cert_path} -noout -enddate").read()
                if "notAfter=" in result:
                    not_after_str = result.strip().split('=', 1)[1]
                    return datetime.strptime(not_after_str, '%b %d %H:%M:%S %Y %Z')
                return None
        except Exception as e:
            print(f"⚠️ Не удалось прочитать срок действия сертификата: {e}")
            return None

    # Проверяем наличие и актуальность сертификата
    if not os.path.exists(cert_path):
        print("🔒 Сертификат не найден. Загружаю...")
        if not download_cert():
            raise FileNotFoundError(f"Не удалось скачать {cert_file}. Подключение к GigaChat невозможно.")
    else:
        not_after = get_cert_expiry()
        if not_after is None:
            print("⚠️ Не удалось прочитать сертификат. Перезагружаю...")
            if not download_cert():
                raise Exception("Не удалось обновить сертификат.")
        else:
            days_left = (not_after - datetime.utcnow()).days
            if days_left < 30:
                print(f"🔄 Сертификат истекает через {days_left} дней. Обновляю...")
                if not download_cert():
                    print("⚠️ Не удалось обновить сертификат, но используем старый.")
                else:
                    print("✅ Сертификат обновлён.")
            else:
                print(f"🟢 Сертификат в порядке. Действителен ещё {days_left} дней.")

    return cert_path


class SSLAdapter(HTTPAdapter):
    def __init__(self, cert_path, **kwargs):
        self.cert_path = cert_path
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.load_verify_locations(cafile=self.cert_path)
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)


class GigaChatClient:
    def __init__(self, auth_key):
        self.auth_key = auth_key.strip()
        self.access_token = None
        self.token_expires_at = 0
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.cert_path = ensure_certificate()
        self.session = requests.Session()
        self.session.verify = False

    def _get_token(self):

        self.cert_path = ensure_certificate()
        self.session.mount("https://", SSLAdapter(cert_path=self.cert_path))

        if self.access_token and time.time() < self.token_expires_at - 60:
            return self.access_token

        try:
            decoded_bytes = base64.b64decode(self.auth_key)
            credentials = decoded_bytes.decode('utf-8')
        except Exception:
            credentials = self.auth_key

        if ":" not in credentials:
            raise ValueError("Неверный формат GIGACHAT_AUTH_KEY: ожидается 'client_id:client_secret'")

        client_id, client_secret = credentials.split(":", 1)

        rq_uid = str(uuid.uuid4())
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

        payload = {"scope": "GIGACHAT_API_PERS"}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": rq_uid,
            "Authorization": f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}"
        }

        for attempt in range(3):
            try:
                self.cert_path = ensure_certificate()
                self.session.mount("https://", SSLAdapter(cert_path=self.cert_path))

                response = self.session.post(
                    url,
                    headers=headers,
                    data=payload,
                    timeout=15
                )

                print(f"🔐 Запрос токена: {response.status_code}")
                try:
                    debug_response = response.json()
                    print(f"📩 Ответ от Sber OAuth: {debug_response}")
                except:
                    print(f"📩 Тело ответа (не JSON): {response.text}")

                response.raise_for_status()

                token_data = response.json()

                if "access_token" not in token_data:
                    raise KeyError("В ответе нет 'access_token'")

                self.access_token = token_data["access_token"]

                if "expires_at" in token_data:
                    self.token_expires_at = token_data["expires_at"] / 1000
                elif "expires_in" in token_data:
                    self.token_expires_at = time.time() + token_data["expires_in"]
                else:
                    raise KeyError("В ответе нет ни 'expires_in', ни 'expires_at'")

                print("✅ Токен успешно получен")
                return self.access_token

            except requests.exceptions.HTTPError as e:
                status = response.status_code
                if status == 400:
                    print(f"❌ Ошибка 400: Неверный запрос. Проверьте scope, RqUID, Authorization.")
                elif status == 401:
                    print(f"❌ Ошибка 401: Неверные учётные данные. Проверьте client_id и client_secret.")
                elif status == 403:
                    print(f"❌ Ошибка 403: Доступ запрещён. Возможно, IP заблокирован или нет прав.")
                else:
                    print(f"❌ HTTP ошибка: {e} ({status})")
                raise Exception(f"HTTP ошибка: {status}, ответ: {response.text}")

            except requests.exceptions.SSLError as e:
                print(f"❌ SSL ошибка (попытка {attempt + 1}/3): {e}")
                if attempt == 2:
                    raise Exception(f"Не удалось подключиться из-за SSL: {e}")
                time.sleep(3)

            except KeyError as e:
                raise Exception(f"Ключ не найден в ответе: {e}. Полный ответ: {token_data}")

            except Exception as e:
                if attempt == 2:
                    raise Exception(f"Не удалось получить токен после 3 попыток: {e}")
                time.sleep(2)

        raise Exception("Не удалось получить токен")

    def chat(self, messages):
        """Отправляет запрос к GigaChat и возвращает ответ"""
        token = self._get_token()
        headers = {
            'Accept': 'application/json',
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "GigaChat-2",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }

        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.SSLError as e:
            raise Exception(f"SSL ошибка при запросе: {e}")
        except requests.exceptions.RequestException as e:
            if 'response' in locals() and response is not None:
                raise Exception(f"Ошибка GigaChat: {e}, статус: {response.status_code}, ответ: {response.text}")
            else:
                raise Exception(f"Сетевая ошибка: {e}")
        except KeyError:
            raise Exception("Не удалось извлечь сообщение из ответа. Возможно, изменилась структура API.")
        except Exception as e:
            raise Exception(f"Неизвестная ошибка при общении с GigaChat: {e}")


# === Инициализация клиента ===
gigachat = None
if GIGACHAT_AUTH_KEY:
    try:
        gigachat = GigaChatClient(GIGACHAT_AUTH_KEY)
    except Exception as e:
        print(f"❌ Не удалось создать GigaChatClient: {e}")
else:
    print("⚠️ GIGACHAT_AUTH_KEY не найден. Работает в режиме эмуляции.")


# === Мок-ответы для тестирования ===
def mock_chat(messages):
    user_messages = [m for m in messages if m["role"] == "user"]
    last_user = user_messages[-1]["content"].lower() if user_messages else ""

    if "имя" in last_user:
        return "Приятно познакомиться! А в каком классе ты учишься?"
    elif "класс" in last_user:
        return "Отлично! В каком городе ты живёшь?"
    elif "город" in last_user:
        return "Понятно. Какие предметы в школе тебе нравятся больше всего?"
    elif "предмет" in last_user:
        return "Интересно. А что ты любишь делать в свободное время?"
    elif "хобби" in last_user:
        return "Здорово! А чем ты хочешь заниматься в будущем? Какая профессия тебя привлекает?"
    elif "профессия" in last_user:
        return EXAMPLE_TRACK_RESPONSE.strip()
    else:
        return "Расскажи подробнее о своих увлечениях и сильных сторонах."


EXAMPLE_TRACK_RESPONSE = """
Трек 1: Backend-разработчик
Описание: Создаёшь «мозг» сайтов и приложений — серверную логику, базы данных, API. Работаешь с Python.
Зарплата в Москве: от 120 000 ₽ (Junior) до 400 000+ ₽ (Senior)
ВУЗы: МГТУ им. Баумана, МФТИ, НИУ ВШЭ
Курсы: Stepik, Coursera, Яндекс.Практикум

Трек 2: UX-дизайнер
Описание: Проектируешь удобные интерфейсы. Работаешь в Figma.
Зарплата: от 90 000 ₽
ВУЗы: ВШЭ, РАНХиГС
Курсы: Нетология, Skillbox

Ты хорошо разбираешься в людях и технологиях — это редкая комбинация, используй её!
"""


def get_ai_response(messages):
    """Возвращает ответ от GigaChat или мок, если клиент недоступен"""
    if gigachat:
        try:
            return gigachat.chat(messages)
        except Exception as e:
            return f"❌ Ошибка при обращении к ИИ: {e}"
    else:
        return mock_chat(messages)