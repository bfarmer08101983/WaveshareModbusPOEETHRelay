import sys
import json
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit,
    QLineEdit, QLabel, QHBoxLayout, QComboBox, QFormLayout, QCheckBox
)
from PyQt5.QtCore import Qt
from pymodbus.client import ModbusSerialClient, ModbusTcpClient, ModbusUdpClient

SETTINGS_FILE = "settings.json"

class ModbusGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveshare Modbus GUI")
        self.resize(600, 600)

        self.modbus_client = None
        self.channel_labels = []

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.201")
        form_layout.addRow("IP Address:", self.ip_input)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("4196")
        form_layout.addRow("Port:", self.port_input)

        self.mode_select = QComboBox()
        self.mode_select.addItems(["TCP", "UDP", "RTU"])
        form_layout.addRow("Connection Mode:", self.mode_select)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect)
        btn_layout.addWidget(self.connect_btn)

        self.read_btn = QPushButton("Read Output Status")
        self.read_btn.clicked.connect(self.read_output_status)
        self.read_btn.setEnabled(False)
        btn_layout.addWidget(self.read_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.output_status_layout = QVBoxLayout()
        self.output_status_label = QLabel("Output Status:")
        layout.addWidget(self.output_status_label)

        # Channel status checkboxes and labels
        self.channel_checkboxes = []
        self.toggle_buttons = []

        for i in range(8):  # 8 Channels
            checkbox = QCheckBox(f"CH{i+1}: OFF")
            self.output_status_layout.addWidget(checkbox)
            self.channel_checkboxes.append(checkbox)

            toggle_button = QPushButton(f"Toggle CH{i+1}")
            toggle_button.clicked.connect(lambda _, i=i: self.toggle_channel(i))
            self.output_status_layout.addWidget(toggle_button)
            self.toggle_buttons.append(toggle_button)

        self.toggle_all_btn = QPushButton("Toggle All Outputs")
        self.toggle_all_btn.clicked.connect(self.toggle_all_channels)
        self.output_status_layout.addWidget(self.toggle_all_btn)

        layout.addLayout(self.output_status_layout)

        self.setLayout(layout)
        self.load_settings()

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.log_output.append(f"{timestamp} {message}")

    def connect(self):
        ip = self.ip_input.text().strip() or "192.168.1.201"
        port_text = self.port_input.text().strip()
        port = int(port_text) if port_text.isdigit() else 4196
        mode = self.mode_select.currentText()

        if self.modbus_client:
            self.modbus_client.close()
            self.modbus_client = None

        try:
            if mode == "TCP":
                self.modbus_client = ModbusTcpClient(ip, port=port)
            elif mode == "UDP":
                self.modbus_client = ModbusUdpClient(ip, port=port)
            elif mode == "RTU":
                self.modbus_client = ModbusSerialClient(method='rtu', port=ip, baudrate=9600)
            else:
                raise ValueError("Unsupported connection mode")

            if self.modbus_client.connect():
                self.log(f"Connected to Modbus device (IP: {ip}, Port: {port}, Mode: {mode})")
                self.read_btn.setEnabled(True)
            else:
                self.log("Failed to connect to Modbus device.")
        except Exception as e:
            self.log(f"Connection error: {e}")

    def read_output_status(self):
        if not self.modbus_client:
            self.log("Client not connected.")
            return

        address = 0x0000
        count = 8

        try:
            self.log(f"[Sent] Read Coils - Address: 0x{address:04X}, Count: {count}")

            result = self.modbus_client.read_coils(address=address, count=count)

            if result.isError():
                self.log(f"[Error] {result}")
            else:
                status_list = result.bits[:count]
                status_str = ', '.join(f"CH{i+1}: {'ON' if bit else 'OFF'}" for i, bit in enumerate(status_list))
                self.log(f"[Received] Output Status: {status_str}")

                # Update the UI with the new status
                for i, bit in enumerate(status_list):
                    self.channel_checkboxes[i].setChecked(bit)
                    self.channel_checkboxes[i].setText(f"CH{i+1}: {'ON' if bit else 'OFF'}")

        except Exception as e:
            self.log(f"[Exception] Failed to read output status: {e}")

    def toggle_channel(self, channel_index):
        if not self.modbus_client:
            self.log("Client not connected.")
            return

        current_status = self.channel_checkboxes[channel_index].isChecked()
        new_status = not current_status

        try:
            address = 0x0000 + channel_index
            self.modbus_client.write_coil(address, new_status)

            # Update the UI to reflect the change
            self.channel_checkboxes[channel_index].setChecked(new_status)
            self.channel_checkboxes[channel_index].setText(f"CH{channel_index+1}: {'ON' if new_status else 'OFF'}")

            self.log(f"[Sent] Toggle CH{channel_index+1} - New Status: {'ON' if new_status else 'OFF'}")
        except Exception as e:
            self.log(f"[Exception] Failed to toggle channel {channel_index+1}: {e}")

    def toggle_all_channels(self):
        if not self.modbus_client:
            self.log("Client not connected.")
            return

        new_status = True  # Toggle all to ON, you can set to False to toggle all to OFF

        try:
            for i in range(8):
                address = 0x0000 + i
                self.modbus_client.write_coil(address, new_status)
                self.channel_checkboxes[i].setChecked(new_status)
                self.channel_checkboxes[i].setText(f"CH{i+1}: {'ON' if new_status else 'OFF'}")

            self.log(f"[Sent] Toggle All Channels - New Status: {'ON' if new_status else 'OFF'}")
        except Exception as e:
            self.log(f"[Exception] Failed to toggle all channels: {e}")

    def save_settings(self):
        settings = {
            "ip": self.ip_input.text(),
            "port": self.port_input.text(),
            "mode": self.mode_select.currentText()
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
        self.log("Settings saved.")

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                self.ip_input.setText(settings.get("ip", ""))
                self.port_input.setText(settings.get("port", ""))
                mode = settings.get("mode", "TCP")
                index = self.mode_select.findText(mode)
                if index != -1:
                    self.mode_select.setCurrentIndex(index)
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = ModbusGUI()
    gui.show()
    sys.exit(app.exec_())
