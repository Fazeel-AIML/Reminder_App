import sys
import pandas as pd
from datetime import datetime
import time
from threading import Thread
from plyer import notification
from qtpy.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLineEdit, 
                             QTextEdit, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QGraphicsDropShadowEffect)
from qtpy.QtGui import QColor, QPalette, QBrush, QFont
from qtpy.QtCore import QTimer, Qt

class ReminderApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.df = self.load_data()
        self.init_ui()

    def load_data(self):
        try:
            df = pd.read_excel("reminder.xlsx")
            df["Time"] = df["Time"].apply(self.parse_time)
            df["Day"] = pd.to_datetime(df["Day"]).dt.date  # Ensure Day is a date object
        except FileNotFoundError:
            df = pd.DataFrame(columns=["Text", "Day", "Time"])
        return df

    def parse_time(self, time_str):
        for fmt in ("%I:%M %p", "%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        raise ValueError(f"Time format not recognized: {time_str}")

    def init_ui(self):
        self.setWindowTitle("Reminder Application")
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #e0f7fa;  /* Light cyan background for the window */
                border-radius: 10px;
            }
            QLineEdit {
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #0097a7;
                background-color: #ffffff;
                color: #004d40;
                font-size: 14px;
            }
            QPushButton {
                padding: 10px;
                border: none;
                border-radius: 5px;
                color: #000000;  /* Text color black */
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #004d40;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #00332e;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #0097a7;
                font-size: 14px;
                color: #004d40;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #0097a7;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QLabel {
                font-size: 16px;
                color: #004d40;
            }
        """)

        layout = QVBoxLayout()

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("What do you want to remind of?")
        layout.addWidget(self.text_input)

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Enter the date in YYYY-MM-DD format")
        layout.addWidget(self.date_input)

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Enter the time in HH:MM AM or PM format")
        layout.addWidget(self.time_input)

        add_button = QPushButton("Add Reminder")
        add_button.setStyleSheet("background: linear-gradient(45deg, #00acc1, #0097a7);")
        add_button.clicked.connect(self.add_remind)
        layout.addWidget(add_button)

        self.reminder_display = QTableWidget()
        self.reminder_display.setColumnCount(3)
        self.reminder_display.setHorizontalHeaderLabels(["Text", "Day", "Time"])
        self.reminder_display.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.reminder_display)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(10000)  # Check reminders every 10 seconds

        self.reminder_thread = Thread(target=self.run_reminder_check)
        self.reminder_thread.daemon = True
        self.reminder_thread.start()

        # Apply shadow effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 0)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.centralWidget().setGraphicsEffect(self.shadow)

    def add_remind(self):
        text = self.text_input.text()
        if text == "":
            text = "Reminder"
        date_str = self.date_input.text()
        time_str = self.time_input.text()

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            reminder_time = self.parse_time(time_str)
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
            return

        now = datetime.now()
        if date < now.date() or (date == now.date() and reminder_time <= now.time()):
            QMessageBox.warning(self, "Input Error", "The date and time must be in the future.")
            return

        new_row = {"Text": text, "Day": date, "Time": reminder_time}
        self.df = self.df._append(new_row, ignore_index=True)
        self.df.to_excel("reminder.xlsx", index=False)
        QMessageBox.information(self, "Success", "Reminder added successfully.")
        self.text_input.clear()
        self.date_input.clear()
        self.time_input.clear()
        self.show_list()  # Automatically update the list when a reminder is added

    def show_list(self):
        self.reminder_display.setRowCount(0)
        for index, row in self.df.iterrows():
            row_position = self.reminder_display.rowCount()
            self.reminder_display.insertRow(row_position)
            self.reminder_display.setItem(row_position, 0, QTableWidgetItem(row["Text"]))
            self.reminder_display.setItem(row_position, 1, QTableWidgetItem(row["Day"].strftime("%Y-%m-%d")))
            self.reminder_display.setItem(row_position, 2, QTableWidgetItem(row["Time"].strftime("%H:%M:%S")))

    def check_reminders(self):
        current_datetime = datetime.now()
        to_remove = []
        for ind, row in self.df.iterrows():
            reminder_datetime = datetime.combine(row["Day"], row["Time"])
            if current_datetime >= reminder_datetime:
                notification.notify(
                    title="Reminder",
                    message=f"You have to do: {row['Text']}\nAt {row['Time']}",
                    app_icon=None,
                    app_name="Reminder Software",
                    ticker="Reminder",
                    timeout=20,
                )
                to_remove.append(ind)
        if to_remove:
            self.df.drop(to_remove, inplace=True)
            self.df.to_excel("reminder.xlsx", index=False)
            self.show_list()  # Update the display

    def run_reminder_check(self):
        while True:
            self.check_reminders()
            time.sleep(60)  # Check reminders every minute

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = ReminderApp()
    main_window.show()
    sys.exit(app.exec_())