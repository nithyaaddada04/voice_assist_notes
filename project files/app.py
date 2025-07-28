import tkinter as tk
from tkinter import messagebox, scrolledtext
import speech_recognition as sr
import pyttsx3
import json
import os
import threading
import time
import datetime
import dateparser
import winsound
import re

NOTES_FILE = "notes.json"
REMINDERS_FILE = "reminders.json"

last_deleted_notes = []
last_deleted_reminders = []

engine = pyttsx3.init()
engine.setProperty("rate", 150)

def speak(text):
    engine.say(text)
    engine.runAndWait()

def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        speak("Listening...")
        try:
            audio = recognizer.listen(source, timeout=5)
            return recognizer.recognize_google(audio)
        except:
            speak("Sorry, I didn’t catch that.")
            return None

def load_json(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f)

def check_reminders():
    while True:
        reminders = load_json(REMINDERS_FILE)
        now = datetime.datetime.now()
        updated = []
        for item in reminders:
            remind_time = datetime.datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S")
            if now >= remind_time:
                winsound.Beep(1000, 700)
                speak(f"Reminder: {item['note']}")
            else:
                updated.append(item)
        save_json(REMINDERS_FILE, updated)
        time.sleep(5)

def delete_all_notes_and_reminders():
    save_json(NOTES_FILE, [])
    save_json(REMINDERS_FILE, [])
    speak("All notes and reminders deleted.")

def delete_task(task_text):
    global last_deleted_notes, last_deleted_reminders
    task_text = task_text.lower().strip()
    notes = load_json(NOTES_FILE)
    reminders = load_json(REMINDERS_FILE)

    new_notes = []
    new_reminders = []
    deleted_notes = []
    deleted_reminders = []

    for n in notes:
        if task_text in n['note'].lower():
            deleted_notes.append(n)
        else:
            new_notes.append(n)

    for r in reminders:
        if task_text in r['note'].lower():
            deleted_reminders.append(r)
        else:
            new_reminders.append(r)

    save_json(NOTES_FILE, new_notes)
    save_json(REMINDERS_FILE, new_reminders)

    last_deleted_notes = deleted_notes
    last_deleted_reminders = deleted_reminders

    if deleted_notes or deleted_reminders:
        speak("Task deleted.")
    else:
        speak(f"No matching task found for: {task_text}")

def undo_last_deletion():
    global last_deleted_notes, last_deleted_reminders
    notes = load_json(NOTES_FILE)
    reminders = load_json(REMINDERS_FILE)

    notes.extend(last_deleted_notes)
    reminders.extend(last_deleted_reminders)

    save_json(NOTES_FILE, notes)
    save_json(REMINDERS_FILE, reminders)

    last_deleted_notes.clear()
    last_deleted_reminders.clear()

    speak("Undo successful.")

def handle_deletion_command(command):
    if "delete all" in command:
        delete_all_notes_and_reminders()
    elif "delete" in command:
        task = command.replace("delete task", "").replace("delete", "").strip()
        if task:
            delete_task(task)
        else:
            speak("Please say the task to delete.")
    elif "undo" in command:
        undo_last_deletion()
    else:
        speak("Invalid delete command.")

class VoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Notes + Reminders")
        self.root.geometry("600x650")

        tk.Label(root, text="🎤 Voice Notes + Reminders", font=("Helvetica", 18, "bold")).pack(pady=10)

        tk.Button(root, text="🎙️ Record Task", command=self.record_task, bg="#4CAF50", fg="white", font=("Arial", 12)).pack(pady=5)
        tk.Button(root, text="🗑️ Voice Delete", command=self.voice_delete, bg="tomato", fg="white", font=("Arial", 12)).pack(pady=5)

        tk.Label(root, text="📝 Notes", font=("Arial", 14, "bold")).pack()
        self.notes_box = scrolledtext.ScrolledText(root, height=10, width=70)
        self.notes_box.pack(pady=5)

        tk.Label(root, text="⏰ Reminders", font=("Arial", 14, "bold")).pack()
        self.reminder_box = scrolledtext.ScrolledText(root, height=8, width=70)
        self.reminder_box.pack(pady=5)

        self.refresh_display()
        threading.Thread(target=check_reminders, daemon=True).start()

    def record_task(self):
        speak("Tell me your task.")
        note = listen()
        if note:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            notes = load_json(NOTES_FILE)
            notes.append({"note": note, "time": now})
            save_json(NOTES_FILE, notes)
            self.refresh_display()
            speak("When should I remind you?")
            reminder_time = listen()
            if reminder_time:
                parsed = dateparser.parse(reminder_time)

                # 🔁 Fallback manual parsing
                if not parsed:
                    match_min = re.search(r"(after|in) (\d+) minute", reminder_time)
                    match_sec = re.search(r"(after|in) (\d+) second", reminder_time)
                    match_hr  = re.search(r"(after|in) (\d+) hour", reminder_time)

                    if match_min:
                        minutes = int(match_min.group(2))
                        parsed = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
                    elif match_sec:
                        seconds = int(match_sec.group(2))
                        parsed = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
                    elif match_hr:
                        hours = int(match_hr.group(2))
                        parsed = datetime.datetime.now() + datetime.timedelta(hours=hours)

                if parsed and parsed > datetime.datetime.now():
                    reminders = load_json(REMINDERS_FILE)
                    reminders.append({"note": note, "time": parsed.strftime("%Y-%m-%d %H:%M:%S")})
                    save_json(REMINDERS_FILE, reminders)
                    self.refresh_display()
                    speak("Reminder set.")
                else:
                    speak("Invalid or past time. Reminder not set.")
        else:
            speak("Could not understand your task.")

    def voice_delete(self):
        speak("Say delete all, delete task name, or undo.")
        command = listen()
        if command:
            handle_deletion_command(command)
            self.refresh_display()

    def refresh_display(self):
        self.notes_box.delete(1.0, tk.END)
        notes = load_json(NOTES_FILE)
        for n in notes[::-1]:
            self.notes_box.insert(tk.END, f"- {n['note']} ({n['time']})\n")

        self.reminder_box.delete(1.0, tk.END)
        reminders = load_json(REMINDERS_FILE)
        for r in reminders:
            self.reminder_box.insert(tk.END, f"- {r['note']} → {r['time']}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceApp(root)
    root.mainloop()
