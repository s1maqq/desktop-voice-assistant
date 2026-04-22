import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QTextEdit, QSystemTrayIcon, QMenu,
    QAction, QStyle, QHBoxLayout, QLineEdit
)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from assist import VoiceAssistantCore


class AssistantThread(QThread):
    message_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self._is_running = True

    def run(self):
        self.message_received.emit("Ассистент: Готов к работе. Скажите 'помощник' для активации.")

        while self._is_running:
            query = self.assistant.listen()

            if not query:
                continue

            self.process_query(query)

    def process_query(self, query):
        self.message_received.emit(f"Вы: {query}")

        if any(word in query for word in ["пока", "выход", "заверши"]):
            self.message_received.emit("Ассистент: До свидания!")
            self.stop()
            return

        if "помощник" in query:
            self.message_received.emit("Ассистент: Да, слушаю вас!")
            query = query.replace("помощник", "").strip()

            if not query:
                return

            response = self.assistant.execute_system_command(query)

            if response:
                self.message_received.emit(f"Ассистент: {response}")
                return

            self.message_received.emit("Ассистент: Думаю...")

            try:
                ai_response = self.assistant.ask_ai(query)
                self.message_received.emit(f"Ассистент: {ai_response[:500]}")
            except Exception as e:
                self.message_received.emit(f"Ассистент: Ошибка: {str(e)}")

    def stop(self):
        self._is_running = False
        self.finished.emit()


class AssistantApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.assistant = VoiceAssistantCore()
        self.init_ui()
        self.init_tray_icon()
        self.speech_queue = []
        self.is_speaking = False
        self.assistant_thread = None

    def init_ui(self):
        self.setWindowTitle("Голосовой помощник")
        self.setGeometry(300, 300, 600, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите запрос вручную...")
        self.btn_send = QPushButton("Отправить")

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.btn_send)
        layout.addLayout(input_layout)

        self.btn_start = QPushButton("Старт голосового ввода")
        self.btn_stop = QPushButton("Стоп")
        self.btn_exit = QPushButton("Выход")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_exit)

        self.btn_start.clicked.connect(self.start_assistant)
        self.btn_stop.clicked.connect(self.stop_assistant)
        self.btn_exit.clicked.connect(self.close)
        self.btn_send.clicked.connect(self.process_manual_input)
        self.input_field.returnPressed.connect(self.process_manual_input)

    def process_manual_input(self):
        query = self.input_field.text()

        if query:
            self.log_message(f"Вы (ручной ввод): {query}")
            self.input_field.clear()

            if self.assistant_thread and self.assistant_thread.isRunning():
                self.assistant_thread.process_query(query)
            else:
                self.log_message("Ассистент: Думаю...")

                try:
                    response = self.assistant.ask_ai(query)
                    self.log_message(f"Ассистент: {response[:500]}")
                except Exception as e:
                    self.log_message(f"Ассистент: Ошибка: {str(e)}")

    def init_tray_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.tray_icon = QSystemTrayIcon(self)

        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

        tray_menu = QMenu()
        show_action = QAction("Показать", self)
        exit_action = QAction("Выход", self)

        show_action.triggered.connect(self.show)
        exit_action.triggered.connect(self.close)

        tray_menu.addAction(show_action)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def start_assistant(self):
        if not self.assistant_thread or not self.assistant_thread.isRunning():
            self.assistant_thread = AssistantThread(self.assistant)
            self.assistant_thread.message_received.connect(self.log_message)
            self.assistant_thread.finished.connect(self.assistant_thread.deleteLater)
            self.assistant_thread.start()
            self.log_message("Ассистент запущен")

    def stop_assistant(self):
        if self.assistant_thread and self.assistant_thread.isRunning():
            self.assistant_thread.stop()
            self.log_message("Ассистент остановлен")

    def process_speech_queue(self):
        if not self.is_speaking and self.speech_queue:
            text = self.speech_queue.pop(0)
            self.is_speaking = True
            self.assistant.speak(text)
            self.is_speaking = False
            QTimer.singleShot(100, self.process_speech_queue)

    def log_message(self, message: str):
        self.log_text.append(message)
        text_to_speak = message.split(":", 1)[-1].strip()
        self.speech_queue.append(text_to_speak)

        if not self.is_speaking:
            self.process_speech_queue()

    def closeEvent(self, event):
        self.stop_assistant()
        self.tray_icon.hide()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AssistantApp()
    window.show()
    sys.exit(app.exec_())
