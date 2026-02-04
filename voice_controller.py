"""
Voice-Controlled Hardware Demo Application
Educational prototype for voice command to ESP8266 communication
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import speech_recognition as sr
import requests
import threading
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
ESP_IP = "192.168.10.193"  # ESP8266 IP address for blood flow LED control
TIMEOUT = 2  # HTTP request timeout in seconds

# Command mapping: voice phrase -> numeric code
COMMAND_MAP = {
    "increase oxygen": "1",
    "decrease oxygen": "2",
    "alarm on": "1",
    "alarm off": "2",
    "mute alarm": "2",
    "critical mode": "1",
    "reset": "2",
}


# ============================================
# MAIN APPLICATION CLASS
# ============================================
class VoiceControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Command Controller")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        
        # State variables
        self.is_listening = False
        self.is_critical_mode = False
        self.recognizer = sr.Recognizer()
        self.microphone = None  # Will be set based on selection
        self.mic_list = []
        self.selected_mic_index = None
        
        # Configure styles
        self.setup_styles()
        
        # Build UI
        self.build_ui()
        
        # Initialize microphone list
        self.refresh_mic_list()
        
        # Initialize status
        self.update_mic_status("Idle", "#6c757d")
        self.check_esp_connection()
        self.log_message("INFO", "Application started")
        
    def setup_styles(self):
        """Configure ttk styles for modern look"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button styles
        style.configure('Action.TButton', 
                       font=('Segoe UI', 10, 'bold'),
                       padding=10)
        
        style.configure('Critical.TButton',
                       font=('Segoe UI', 10, 'bold'),
                       padding=10,
                       background='#dc3545')
        
        style.configure('Normal.TButton',
                       font=('Segoe UI', 10, 'bold'),
                       padding=10,
                       background='#28a745')
        
    def build_ui(self):
        """Build the complete user interface"""
        
        # ===== HEADER =====
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🎙️ Voice Command Controller",
            font=("Segoe UI", 20, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=20)
        
        # ===== MICROPHONE SELECTION =====
        mic_select_frame = tk.Frame(self.root, bg="#ecf0f1", padx=20, pady=10)
        mic_select_frame.pack(fill=tk.X)
        
        tk.Label(
            mic_select_frame,
            text="Microphone Device:",
            font=("Segoe UI", 10, "bold"),
            bg="#ecf0f1",
            fg="#34495e"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.mic_combo = ttk.Combobox(
            mic_select_frame,
            font=("Segoe UI", 9),
            state="readonly",
            width=40
        )
        self.mic_combo.pack(side=tk.LEFT, padx=5)
        self.mic_combo.bind("<<ComboboxSelected>>", self.on_mic_selected)
        
        self.refresh_mic_btn = tk.Button(
            mic_select_frame,
            text="🔄 Refresh",
            font=("Segoe UI", 9, "bold"),
            bg="#6c757d",
            fg="white",
            activebackground="#5a6268",
            activeforeground="white",
            relief=tk.RAISED,
            bd=1,
            cursor="hand2",
            command=self.refresh_mic_list
        )
        self.refresh_mic_btn.pack(side=tk.LEFT, padx=5)
        
        # ===== STATUS PANEL =====
        status_frame = tk.Frame(self.root, bg="#ecf0f1", padx=20, pady=15)
        status_frame.pack(fill=tk.X)
        
        # Mic Status
        mic_frame = tk.Frame(status_frame, bg="#ecf0f1")
        mic_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(
            mic_frame,
            text="Microphone:",
            font=("Segoe UI", 10),
            bg="#ecf0f1",
            fg="#34495e"
        ).pack(side=tk.LEFT)
        
        self.mic_status_label = tk.Label(
            mic_frame,
            text="Idle",
            font=("Segoe UI", 10, "bold"),
            bg="#ecf0f1",
            fg="#6c757d",
            width=12
        )
        self.mic_status_label.pack(side=tk.LEFT, padx=5)
        
        # ESP Status
        esp_frame = tk.Frame(status_frame, bg="#ecf0f1")
        esp_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(
            esp_frame,
            text="ESP8266:",
            font=("Segoe UI", 10),
            bg="#ecf0f1",
            fg="#34495e"
        ).pack(side=tk.LEFT)
        
        self.esp_status_label = tk.Label(
            esp_frame,
            text="Checking...",
            font=("Segoe UI", 10, "bold"),
            bg="#ecf0f1",
            fg="#6c757d",
            width=15
        )
        self.esp_status_label.pack(side=tk.LEFT, padx=5)
        
        # ===== DETECTED SPEECH DISPLAY =====
        speech_frame = tk.Frame(self.root, bg="white", padx=20, pady=15)
        speech_frame.pack(fill=tk.X)
        
        tk.Label(
            speech_frame,
            text="Last Detected Speech:",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#34495e"
        ).pack(anchor=tk.W)
        
        self.speech_text_label = tk.Label(
            speech_frame,
            text="(waiting for input...)",
            font=("Segoe UI", 12),
            bg="#f8f9fa",
            fg="#495057",
            relief=tk.SUNKEN,
            padx=10,
            pady=10,
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=640
        )
        self.speech_text_label.pack(fill=tk.X, pady=5)
        
        # ===== CONTROL BUTTONS =====
        button_frame = tk.Frame(self.root, bg="white", padx=20, pady=10)
        button_frame.pack(fill=tk.X)
        
        # Row 1: Start/Stop Listening
        row1 = tk.Frame(button_frame, bg="white")
        row1.pack(fill=tk.X, pady=5)
        
        self.start_btn = tk.Button(
            row1,
            text="▶ Start Listening",
            font=("Segoe UI", 11, "bold"),
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.start_listening
        )
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.stop_btn = tk.Button(
            row1,
            text="⏹ Stop Listening",
            font=("Segoe UI", 11, "bold"),
            bg="#dc3545",
            fg="white",
            activebackground="#c82333",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.stop_listening
        )
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Row 2: Mode Buttons
        row2 = tk.Frame(button_frame, bg="white")
        row2.pack(fill=tk.X, pady=5)
        
        self.normal_mode_btn = tk.Button(
            row2,
            text="🟢 Normal Mode",
            font=("Segoe UI", 10, "bold"),
            bg="#17a2b8",
            fg="white",
            activebackground="#138496",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.set_normal_mode
        )
        self.normal_mode_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.critical_mode_btn = tk.Button(
            row2,
            text="🔴 Critical Mode",
            font=("Segoe UI", 10, "bold"),
            bg="#ffc107",
            fg="#212529",
            activebackground="#e0a800",
            activeforeground="#212529",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.set_critical_mode
        )
        self.critical_mode_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.reset_btn = tk.Button(
            row2,
            text="🔄 Reset",
            font=("Segoe UI", 10, "bold"),
            bg="#6c757d",
            fg="white",
            activebackground="#5a6268",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.reset_system
        )
        self.reset_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # ===== LOG BOX =====
        log_frame = tk.Frame(self.root, bg="white", padx=20, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            log_frame,
            text="Activity Log:",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#34495e"
        ).pack(anchor=tk.W)
        
        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            relief=tk.SUNKEN,
            bd=2,
            height=10,
            state=tk.DISABLED
        )
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # ===== FOOTER =====
        footer_frame = tk.Frame(self.root, bg="#34495e", height=30)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        tk.Label(
            footer_frame,
            text=f"ESP8266 IP: {ESP_IP} | Educational Prototype Only",
            font=("Segoe UI", 8),
            bg="#34495e",
            fg="#ecf0f1"
        ).pack(pady=5)
        
    # ============================================
    # MICROPHONE MANAGEMENT METHODS
    # ============================================
    
    def get_mic_list(self):
        """Get list of available microphone devices"""
        try:
            mic_names = sr.Microphone.list_microphone_names()
            if not mic_names:
                self.log_message("WARN", "No microphones detected")
                return ["No microphones found"]
            return mic_names
        except Exception as e:
            self.log_message("ERROR", f"Failed to enumerate microphones: {e}")
            return ["Error detecting microphones"]
    
    def refresh_mic_list(self):
        """Refresh the microphone device list"""
        self.mic_list = self.get_mic_list()
        self.mic_combo['values'] = self.mic_list
        
        # Set default selection (first device)
        if self.mic_list and "No microphones" not in self.mic_list[0] and "Error" not in self.mic_list[0]:
            self.mic_combo.current(0)
            self.selected_mic_index = 0
            self.log_message("INFO", f"Microphone list refreshed ({len(self.mic_list)} devices found)")
            self.log_message("INFO", f"Default microphone: {self.mic_list[0]}")
        else:
            self.log_message("WARN", "No valid microphones available")
    
    def get_selected_mic_index(self):
        """Get the device index for the selected microphone"""
        try:
            selected_name = self.mic_combo.get()
            if selected_name in self.mic_list:
                return self.mic_list.index(selected_name)
            return None  # Use default device
        except Exception as e:
            self.log_message("ERROR", f"Error getting mic index: {e}")
            return None
    
    def on_mic_selected(self, event):
        """Handle microphone selection event"""
        selected_name = self.mic_combo.get()
        self.selected_mic_index = self.get_selected_mic_index()
        self.log_message("INFO", f"Microphone selected: {selected_name}")
    
    # ============================================
    # SPEECH RECOGNITION METHODS
    # ============================================
    
    def start_listening(self):
        """Start continuous speech recognition"""
        if self.is_listening:
            return
        
        # Get selected microphone index
        self.selected_mic_index = self.get_selected_mic_index()
        
        # Create microphone instance with selected device
        try:
            if self.selected_mic_index is not None:
                self.microphone = sr.Microphone(device_index=self.selected_mic_index)
                self.log_message("INFO", f"Using microphone: {self.mic_combo.get()}")
            else:
                self.microphone = sr.Microphone()  # Use default
                self.log_message("INFO", "Using default microphone")
        except Exception as e:
            self.log_message("ERROR", f"Failed to initialize microphone: {e}")
            return
            
        self.is_listening = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.mic_combo.config(state=tk.DISABLED)
        self.refresh_mic_btn.config(state=tk.DISABLED)
        self.update_mic_status("Listening", "#28a745")
        self.log_message("INFO", "Started listening for voice commands")
        
        # Run speech recognition in separate thread
        threading.Thread(target=self.listen_loop, daemon=True).start()
        
    def stop_listening(self):
        """Stop speech recognition"""
        self.is_listening = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.mic_combo.config(state="readonly")
        self.refresh_mic_btn.config(state=tk.NORMAL)
        self.update_mic_status("Idle", "#6c757d")
        self.log_message("INFO", "Stopped listening")
        
    def listen_loop(self):
        """Continuous listening loop (runs in background thread)"""
        with self.microphone as source:
            self.log_message("INFO", "Calibrating for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                try:
                    # Convert speech to text
                    text = self.recognizer.recognize_google(audio).lower()
                    self.root.after(0, self.process_speech, text)
                    
                except sr.UnknownValueError:
                    self.root.after(0, self.log_message, "WARN", "Could not understand audio")
                except sr.RequestError as e:
                    self.root.after(0, self.log_message, "ERROR", f"Speech recognition error: {e}")
                    
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                self.root.after(0, self.log_message, "ERROR", f"Listening error: {e}")
                break
                
    def process_speech(self, text):
        """Process recognized speech text"""
        # Update UI with detected speech
        self.speech_text_label.config(text=f'"{text}"')
        self.log_message("HEARD", text)
        
        # Parse command
        command_code = self.parse_command(text)
        
        if command_code:
            self.log_message("PARSED", f"Command mapped to code: {command_code}")
            self.send_command(command_code)
        else:
            self.log_message("WARN", "Unknown command - no action taken")
            
    def parse_command(self, text):
        """Map speech text to command code"""
        text = text.lower().strip()
        
        # Check for blood flow control commands
        # Increase blood flow → LED ON (1)
        if "increase blood flow" in text or \
           ("increase" in text and "flow" in text) or \
           "more blood" in text:
            return "1"
        
        # Decrease blood flow → LED OFF (2)
        if "decrease blood flow" in text or \
           ("decrease" in text and "flow" in text) or \
           "reduce blood" in text:
            return "2"
        
        # Check for exact matches in command map
        for phrase, code in COMMAND_MAP.items():
            if phrase in text:
                return code
                
        return None
        
    # ============================================
    # ESP8266 COMMUNICATION
    # ============================================
    
    def send_command(self, value):
        """Send HTTP GET request to ESP8266"""
        url = f"http://{ESP_IP}/{value}"
        
        def send_request():
            try:
                self.root.after(0, self.log_message, "SENT", f"Sending command {value} to ESP...")
                response = requests.get(url, timeout=TIMEOUT)
                
                if response.status_code == 200:
                    self.root.after(0, self.log_message, "OK", "ESP acknowledged command")
                    self.root.after(0, self.update_esp_status, "Connected", "#28a745")
                else:
                    self.root.after(0, self.log_message, "WARN", f"ESP returned status {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                self.root.after(0, self.log_message, "ERROR", "Cannot connect to ESP - check IP and WiFi")
                self.root.after(0, self.update_esp_status, "Not Connected", "#dc3545")
            except requests.exceptions.Timeout:
                self.root.after(0, self.log_message, "ERROR", "ESP request timeout")
                self.root.after(0, self.update_esp_status, "Timeout", "#ffc107")
            except Exception as e:
                self.root.after(0, self.log_message, "ERROR", f"Request failed: {e}")
                
        # Run in background thread
        threading.Thread(target=send_request, daemon=True).start()
        
    def check_esp_connection(self):
        """Check if ESP8266 is reachable"""
        def check():
            try:
                response = requests.get(f"http://{ESP_IP}/", timeout=2)
                self.root.after(0, self.update_esp_status, "Connected", "#28a745")
            except:
                self.root.after(0, self.update_esp_status, "Not Connected", "#dc3545")
                
        threading.Thread(target=check, daemon=True).start()
        
    # ============================================
    # MODE CONTROL
    # ============================================
    
    def set_normal_mode(self):
        """Activate normal mode"""
        self.is_critical_mode = False
        self.send_command("0")  # Assuming 0 = normal mode
        self.log_message("MODE", "Switched to NORMAL mode")
        
    def set_critical_mode(self):
        """Activate critical mode"""
        self.is_critical_mode = True
        self.send_command("5")  # Critical mode command
        self.log_message("MODE", "Switched to CRITICAL mode")
        
    def reset_system(self):
        """Reset the system"""
        self.send_command("2")  # Reset command
        self.log_message("RESET", "System reset command sent")
        self.speech_text_label.config(text="(waiting for input...)")
        
    # ============================================
    # UI UPDATE METHODS
    # ============================================
    
    def update_mic_status(self, status, color):
        """Update microphone status label"""
        self.mic_status_label.config(text=status, fg=color)
        
    def update_esp_status(self, status, color):
        """Update ESP8266 status label"""
        self.esp_status_label.config(text=status, fg=color)
        
    def log_message(self, level, message):
        """Add message to log box"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding for different log levels
        colors = {
            "INFO": "#61afef",
            "HEARD": "#98c379",
            "PARSED": "#e5c07b",
            "SENT": "#c678dd",
            "OK": "#56b6c2",
            "WARN": "#e06c75",
            "ERROR": "#e06c75",
            "MODE": "#d19a66",
            "RESET": "#abb2bf"
        }
        
        color = colors.get(level, "#d4d4d4")
        
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_box.insert(tk.END, f"[{level}] ", level)
        self.log_box.insert(tk.END, f"{message}\n")
        
        # Configure tags for colors
        self.log_box.tag_config("timestamp", foreground="#7f848e")
        self.log_box.tag_config(level, foreground=color, font=("Consolas", 9, "bold"))
        
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)


# ============================================
# MAIN ENTRY POINT
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceControllerApp(root)
    root.mainloop()
