import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import os
import requests
import subprocess
from typing import Optional
import winreg
from dotenv import load_dotenv

load_dotenv()

class VoiceAssistantCore:
    def __init__(self):
        self.engine = None
        self.recognizer = sr.Recognizer()
        self.PROGRAMS = {
            "блокнот": r"C:\Windows\system32\notepad.exe",
            "проводник": r"explorer.exe",
            "стим": r"C:\Program Files (x86)\Steam\Steam.exe",
            "дискорд": r"C:\Users\{USERNAME}\AppData\Local\Discord\app-1.0.9003\Discord.exe",
            "калькулятор": r"C:\Windows\system32\calc.exe",
            "браузер": r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        }
        self.HF_API_TOKEN = os.getenv("HF_API_TOKEN")
        self.HF_API_URL = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models/bigscience/bloomz")

    def init_engine(self):
        if self.engine is None:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.startLoop(False)

    def speak(self, text: str) -> None:
        self.init_engine()
        self.engine.say(text)
        self.engine.iterate()

    def listen(self) -> Optional[str]:
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                query = self.recognizer.recognize_google(audio, language="ru-RU").lower()
                return query
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                print(f"Ошибка распознавания: {e}")
                return None

    def find_program_path(self, program_name: str) -> Optional[str]:
        """Поиск пути к программе в реестре Windows"""
        try:
            if program_name == "стим":
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                    return winreg.QueryValueEx(key, "SteamExe")[0]
            elif program_name == "дискорд":
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Discord"
                ) as key:
                    return winreg.QueryValueEx(key, "DisplayIcon")[0].replace(',0', '')
        except Exception:
            return None
        return None

    def execute_system_command(self, command: str) -> Optional[str]:
        command = command.lower()

        for program_name, default_path in self.PROGRAMS.items():
            if program_name in command:
                path = self.find_program_path(program_name) or default_path
                path = path.replace("{USERNAME}", os.getlogin())

                try:
                    if program_name == "проводник":
                        subprocess.Popen([path])
                    else:
                        os.startfile(path)
                    return f"Открываю {program_name}"
                except Exception as e:
                    print(f"Ошибка открытия {program_name}: {e}")
                    return f"Не удалось открыть {program_name}"

        if "открой браузер" in command:
            os.startfile(self.PROGRAMS["браузер"])
            return "Открываю браузер"
        elif "погода" in command:
            city = "Москва"
            webbrowser.open(f"https://yandex.ru/pogoda/{city}")
            return f"Открываю погоду для {city}"
        elif "время" in command:
            return f"Сейчас {datetime.datetime.now().strftime('%H:%M')}"
        elif "выключи компьютер" in command:
            os.system("shutdown /s /t 60")
            return "Компьютер будет выключен через 1 минуту"

        return None

    def ask_ai(self, prompt: str) -> str:
        """Запрос к Hugging Face API"""
        headers = {
            "Authorization": f"Bearer {self.HF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7
            }
        }

        try:
            response = requests.post(self.HF_API_URL, headers=headers, json=payload)
            print("Статус ответа API:", response.status_code)
            print("Тело ответа API:", response.text)

            response.raise_for_status()

            if isinstance(response.json(), list):
                return response.json()[0].get("generated_text", "Не удалось обработать ответ")
            else:
                return response.json().get("generated_text", "Не удалось обработать ответ")
        except requests.exceptions.RequestException as e:
            print(f"Ошибка API: {e}")
            return "Не удалось получить ответ от ИИ"
