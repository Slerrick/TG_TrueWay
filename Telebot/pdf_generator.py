from fpdf import FPDF
import os
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(PROJECT_ROOT, "app")
LOGO_PATH = os.path.join(STATIC_DIR, "logo.png")
FONT_REGULAR = os.path.join(STATIC_DIR, "fonts", "DejaVuSans.ttf")
FONT_BOLD = os.path.join(STATIC_DIR, "fonts", "DejaVuSans-Bold.ttf")


class PDFGenerator:
    def __init__(self):
        self.pdf = FPDF()
        self.pdf.add_font("DejaVu", "", FONT_REGULAR)
        self.pdf.add_font("DejaVu", "B", FONT_BOLD)
        self.pdf.set_auto_page_break(auto=True, margin=20)

    def add_title(self, text):
        self.pdf.set_font("DejaVu", "B", 20)
        self.pdf.set_text_color(47, 139, 87)
        self.pdf.cell(0, 15, text, align='C')
        self.pdf.ln(15)

    def add_subtitle(self, text):
        self.pdf.set_font("DejaVu", "B", 14)
        self.pdf.set_text_color(30, 58, 43)
        self.pdf.cell(0, 10, text)
        self.pdf.ln(8)

    def add_body(self, text):
        self.pdf.set_font("DejaVu", "", 11)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.multi_cell(0, 7, text, align='L')
        self.pdf.ln(8)

    def generate_report(self, tracks, review, user_name="Ученик"):
        self.pdf.add_page()

        if os.path.exists(LOGO_PATH):
            self.pdf.image(LOGO_PATH, x=95, y=20, w=20)
            self.pdf.ln(35)
        else:
            self.pdf.ln(15)

        self.add_title("Отчёт по профориентации")

        self.pdf.set_font("DejaVu", "", 12)
        self.pdf.set_text_color(100, 100, 100)
        self.pdf.cell(0, 10, f"Для: {user_name} • {datetime.now().strftime('%d.%m.%Y')}", align='C')
        self.pdf.ln(15)

        self.add_subtitle("🔍 Отзыв о скрытых способностях")
        self.add_body(review.strip())

        for i, track in enumerate(tracks, 1):
            title = track.get("title", "Без названия").strip()
            description = track.get("description", "Нет описания.").strip()

            self.add_subtitle(f"🎯 Карьерный трек {i}: {title}")
            self.add_body(description)

        self.pdf.ln(10)
        self.add_body("Сгенерировано с помощью TrueWay AI — ИИ-профориентатора для школьников.")
        self.pdf.set_text_color(47, 139, 87)
        self.add_body("https://t.me/ItsTrueWay_bot")

    def output(self, file_path):
        self.pdf.output(file_path)