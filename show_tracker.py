import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import json
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import mimetypes
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, 'show_data.json')
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

class PWAHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def send(self, code, ctype, body):
        if isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/shows':
            try:
                with open(DATA_FILE) as f: data = f.read()
            except FileNotFoundError:
                data = '{}'
            self.send(200, 'application/json', data)

        elif path == '/api/cover':
            qs = parse_qs(parsed.query)
            img_path = unquote(qs.get('path', [''])[0])
            if os.path.isfile(img_path):
                mime = mimetypes.guess_type(img_path)[0] or 'image/jpeg'
                with open(img_path, 'rb') as f: self.send(200, mime, f.read())
            else:
                self.send(404, 'text/plain', 'Not found')

        else:
            if path == '/': path = '/index.html'
            file_path = os.path.join(SCRIPT_DIR, path.lstrip('/'))
            if os.path.isfile(file_path):
                mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                with open(file_path, 'rb') as f: self.send(200, mime, f.read())
            else:
                self.send(404, 'text/plain', 'Not found')

    def do_POST(self):
        if self.path.startswith('/api/cover/'):
            title = unquote(self.path[len('/api/cover/'):])
            length = int(self.headers.get('Content-Length', 0))
            content_type = self.headers.get('Content-Type', 'image/jpeg')
            ext = mimetypes.guess_extension(content_type.split(';')[0].strip()) or '.jpg'
            if ext == '.jpe': ext = '.jpg'
            covers_dir = os.path.join(SCRIPT_DIR, 'Show Covers')
            os.makedirs(covers_dir, exist_ok=True)
            save_path = os.path.join(covers_dir, f'{title}{ext}')
            with open(save_path, 'wb') as f: f.write(self.rfile.read(length))
            try:
                with open(DATA_FILE) as f: data = json.load(f)
                if title in data:
                    data[title]['cover_image'] = save_path
                    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)
            except FileNotFoundError: pass
            self.send(200, 'application/json', json.dumps({'path': save_path}))

    def do_PUT(self):
        if self.path.startswith('/api/shows/'):
            title = unquote(self.path[len('/api/shows/'):])
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            try:
                with open(DATA_FILE) as f: data = json.load(f)
            except FileNotFoundError:
                data = {}
            data[title] = body
            with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)
            self.send(200, 'application/json', '{"ok":true}')

    def do_DELETE(self):
        if self.path.startswith('/api/shows/'):
            title = unquote(self.path[len('/api/shows/'):])
            try:
                with open(DATA_FILE) as f: data = json.load(f)
                data.pop(title, None)
                with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)
            except FileNotFoundError:
                pass
            self.send(200, 'application/json', '{"ok":true}')

def start_server(server_holder, port):
    server = HTTPServer(('0.0.0.0', port), PWAHandler)
    server_holder.append(server)
    server.serve_forever()


class ShowTracker:
    def __init__(self, master):
        self.master = master
        master.title("TV Show Tracker")

        # Define color attributes
        self.bg_color = "#000000"  # AMOLED black background
        self.fg_color = "#D8DEE9"  # Light text color
        self.accent_color = "#88C0D0"  # Accent color for highlights

        # Initialize cover_image attribute
        self.cover_image = None

        # Call the setup_modern_ui method
        self.setup_modern_ui()

        self.show_data = self.load_data()
        self._last_mtime = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else 0

        # Create GUI elements
        self.create_widgets()
        self._poll_file()

    def setup_modern_ui(self):
        # Configure a custom style for a modern look
        style = ttk.Style()
        style.theme_use('clam')

        # Define custom colors
        bg_color = "#000000"  # AMOLED black background
        fg_color = "#D8DEE9"  # Light text color
        accent_color = "#88C0D0"  # Accent color for highlights

        # Configure colors for various widget states
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TButton", background=accent_color, foreground=bg_color)
        style.map("TButton", background=[('active', "#81A1C1")])
        style.configure("TEntry", fieldbackground=bg_color, foreground=fg_color)
        style.configure("TSpinbox", fieldbackground=bg_color, foreground=fg_color)

        # Configure the main window
        self.master.configure(bg=bg_color)
        self.master.option_add("*Font", "Roboto 10")
        self.master.option_add("*Background", bg_color)
        self.master.option_add("*Foreground", fg_color)

        # Add some padding to the main window
        self.master.geometry("800x600")
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(1, weight=1)

    def create_widgets(self):
        # Configure button styles
        style = ttk.Style()
        style.configure("Custom.TButton", background=self.accent_color, foreground=self.bg_color, padding=10)  # Add padding for height

        # Remove the TV Show Tracker label
        # self.label = tk.Label(self.master, text="TV Show Tracker", font=("Helvetica", 16))
        # self.label.grid(row=0, column=0, columnspan=3, pady=10)

        # Configure Treeview style
        style = ttk.Style()
        style.configure("Treeview", rowheight=60)  # Set the row height to be higher
        style.configure("Treeview", background=self.bg_color, fieldbackground=self.bg_color, foreground=self.fg_color, borderwidth=0)  # Set background and text color, remove border
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])  # Remove borders

        # Add Show button
        self.add_show_button = ttk.Button(self.master, text="Add Show", command=self.add_new_show, style="Custom.TButton", width=15)
        self.add_show_button.grid(row=0, column=0, columnspan=3, pady=10)

        # Show Treeview with cover images
        self.tree = ttk.Treeview(self.master, columns=("Title",), show="tree", selectmode='browse', style="Treeview")
        self.tree.column("#0", width=100)
        self.tree.column("Title", width=200)
        self.tree.grid(row=1, column=0, rowspan=5, columnspan=3, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.load_show_details)

        # Dictionary to hold PhotoImage references
        self.image_refs = {}

        # Details Frame
        self.details_frame = ttk.Frame(self.master)
        self.details_frame.grid(row=1, column=3, rowspan=6, padx=10, pady=10)

        # PWA toggle
        self.pwa_var = tk.BooleanVar(value=False)
        style = ttk.Style()
        style.configure("PWA.TCheckbutton", background="#000000", foreground="#88C0D0", indicatorcolor="#88C0D0")
        style.map("PWA.TCheckbutton", background=[("active", "#000000")], foreground=[("active", "#88C0D0")])
        pwa_frame = tk.Frame(self.details_frame, bg=self.bg_color)
        pwa_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.pwa_check = ttk.Checkbutton(pwa_frame, text="Start PWA", variable=self.pwa_var, command=self.toggle_pwa, style="PWA.TCheckbutton")
        self.pwa_check.pack(side=tk.LEFT)
        ttk.Label(pwa_frame, text="Port:").pack(side=tk.LEFT, padx=(10, 4))
        self.port_entry = ttk.Entry(pwa_frame, width=6)
        self.port_entry.insert(0, str(load_config().get('port', 8080)))
        self.port_entry.pack(side=tk.LEFT)

        # Title
        self.title_label = ttk.Label(self.details_frame, text="Title:")
        self.title_label.grid(row=1, column=0, sticky="w", padx=(0, 5))
        self.title_entry = ttk.Entry(self.details_frame, width=30)
        self.title_entry.grid(row=1, column=1, sticky="w")

        # Description
        self.description_label = ttk.Label(self.details_frame, text="Description:")
        self.description_label.grid(row=2, column=0, sticky="w", padx=(0, 5))
        self.description_text = tk.Text(self.details_frame, height=5, width=30, bg=self.bg_color, fg=self.fg_color, wrap=tk.WORD)
        self.description_text.grid(row=2, column=1, sticky="w")

        # Season and Episode
        self.season_label = ttk.Label(self.details_frame, text="Season:")
        self.season_label.grid(row=3, column=0, sticky="w", padx=(0, 5))
        self.season_spinbox = ttk.Spinbox(self.details_frame, from_=1, to=99, width=5)
        self.season_spinbox.grid(row=3, column=1, sticky="w")

        self.episode_label = ttk.Label(self.details_frame, text="Episode:")
        self.episode_label.grid(row=4, column=0, sticky="w", padx=(0, 5))
        self.episode_spinbox = ttk.Spinbox(self.details_frame, from_=1, to=999, width=5)
        self.episode_spinbox.grid(row=4, column=1, sticky="w")

        # Cover Image
        self.cover_image_label = ttk.Label(self.details_frame, cursor="hand2")
        self.cover_image_label.grid(row=5, column=0, columnspan=2, pady=10)
        self.cover_image_label.bind("<Button-1>", self.show_full_image)

        # Image Buttons Frame
        image_buttons_frame = tk.Frame(self.details_frame)
        image_buttons_frame.grid(row=6, column=0, columnspan=2)

        self.browse_button = ttk.Button(image_buttons_frame, text="Browse Cover Image", command=self.browse_image, style="Custom.TButton", width=20)
        self.browse_button.pack(side=tk.LEFT, padx=10)

        self.remove_image_button = ttk.Button(image_buttons_frame, text="Remove Cover Image", command=self.remove_cover_image, style="Custom.TButton", width=20)
        self.remove_image_button.pack(side=tk.LEFT, padx=10)

        # Action Buttons Frame
        action_buttons_frame = tk.Frame(self.details_frame)
        action_buttons_frame.grid(row=7, column=0, columnspan=2)

        # Delete button (under Browse Image)
        self.delete_button = ttk.Button(action_buttons_frame, text="Delete", command=self.delete_show, style="Custom.TButton", width=15)
        self.delete_button.pack(side=tk.LEFT, padx=5, pady=(5, 10))

        # Save/Update button (under Remove Image)
        self.save_button = ttk.Button(action_buttons_frame, text="Save/Update", command=self.save_show, style="Custom.TButton", width=15)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=(5, 10))

        # Refresh button (under Delete and Save/Update)
        self.refresh_button = ttk.Button(action_buttons_frame, text="Refresh", command=self.refresh_show_list, style="Custom.TButton", width=15)
        self.refresh_button.pack(side=tk.LEFT, padx=5, pady=(5, 10))

        self.refresh_show_list()

    def browse_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if file_path:
            try:
                with Image.open(file_path) as img:
                    img.thumbnail((200, 200))
                    photo = ImageTk.PhotoImage(img)
                self.cover_image_label.config(image=photo)
                self.cover_image_label.image = photo
                self.cover_image = file_path
            except Exception as e:
                print(f"Error loading image: {e}")

    def remove_cover_image(self):
        self.cover_image_label.config(image="")
        self.cover_image_label.image = None
        self.cover_image = None

    def add_new_show(self):
        """Clears all input fields and deselects any selected show."""
        # Deselect any selected item in the tree
        self.tree.selection_remove(self.tree.selection())
        
        # Clear all input fields
        self.title_entry.delete(0, tk.END)
        self.description_text.delete("1.0", tk.END)
        self.season_spinbox.delete(0, tk.END)
        self.episode_spinbox.delete(0, tk.END)
        
        # Clear cover image
        self.cover_image_label.config(image="")
        self.cover_image_label.image = None
        self.cover_image = None

    def show_full_image(self, event=None):
        """Display the full-size cover image in a new window."""
        if self.cover_image:
            try:
                with Image.open(self.cover_image) as img:
                    screen_width = self.master.winfo_screenwidth()
                    screen_height = self.master.winfo_screenheight()
                    max_width = int(screen_width * 0.9)
                    max_height = int(screen_height * 0.9)
                    if img.width > max_width or img.height > max_height:
                        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    w, h = img.width, img.height
                img_window = tk.Toplevel(self.master)
                img_window.title("Cover Image")
                img_window.configure(bg=self.bg_color)
                img_label = tk.Label(img_window, image=photo, bg=self.bg_color)
                img_label.image = photo
                img_label.pack()
                img_window.geometry(f"{w}x{h}")
            except Exception as e:
                print(f"Error displaying full image: {e}")

    def refresh_show_list(self):
        """Clears and reloads shows in the Treeview from self.show_data."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.image_refs.clear()  # Clear previous image references

        # Sort the shows alphabetically
        sorted_shows = sorted(self.show_data.items(), key=lambda x: x[0].lower())

        for show_title, details in sorted_shows:
            cover_image_path = details.get("cover_image", "")
            if cover_image_path:
                try:
                    with Image.open(cover_image_path) as img:
                        img.thumbnail((50, 50))
                        photo = ImageTk.PhotoImage(img)
                    self.image_refs[show_title] = photo
                    item = self.tree.insert("", "end", text="", image=photo, values=(show_title,))
                except Exception as e:
                    print(f"Error loading image: {e}")
                    item = self.tree.insert("", "end", text="", values=(show_title,))
            else:
                item = self.tree.insert("", "end", text="", values=(show_title,))

            # Select the newly added/updated show
            if show_title == self.title_entry.get():
                self.tree.selection_set(item)
                self.tree.see(item)

    def load_show_details(self, event=None):
        """Loads show details into the input fields when a show is selected."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            selected_show = item["values"][0]
            show_details = self.show_data.get(selected_show, {})

            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, selected_show)
            self.description_text.delete("1.0", tk.END)
            self.description_text.insert("1.0", show_details.get("description", ""))
            self.season_spinbox.delete(0, tk.END)
            season = show_details.get("season")
            if season is not None:
                self.season_spinbox.insert(0, season)
            self.episode_spinbox.delete(0, tk.END)
            episode = show_details.get("episode")
            if episode is not None:
                self.episode_spinbox.insert(0, episode)

            # Load cover image if available
            cover_image_path = show_details.get("cover_image")
            if cover_image_path:
                try:
                    with Image.open(cover_image_path) as img:
                        img.thumbnail((200, 200))
                        photo = ImageTk.PhotoImage(img)
                    self.cover_image_label.config(image=photo)
                    self.cover_image_label.image = photo
                    self.cover_image = cover_image_path
                except Exception as e:
                    print(f"Error loading image: {e}")
            else:
                self.cover_image_label.config(image="")
                self.cover_image = None

    def save_show(self):
        """Saves or updates the show details."""
        title = self.title_entry.get()
        description = self.description_text.get("1.0", tk.END).strip()
        
        # Handle empty season/episode fields
        season_value = self.season_spinbox.get().strip()
        episode_value = self.episode_spinbox.get().strip()
        season = int(season_value) if season_value else None
        episode = int(episode_value) if episode_value else None

        self.show_data[title] = {
            "description": description,
            "season": season,
            "episode": episode,
            "cover_image": self.cover_image  # Store the file path
        }

        self.save_data(self.show_data)
        self.refresh_show_list()  # Refresh the list to reflect changes

    def delete_show(self):
        """Deletes the selected show from the Treeview and the underlying data structure."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            selected_show = item["values"][0]

            # Remove from the Treeview
            self.tree.delete(selection[0])

            # Remove from the underlying data structure
            if selected_show in self.show_data:
                del self.show_data[selected_show]

            # Save the updated data to the JSON file
            self.save_data_to_json()

            # Clear the input fields
            self.title_entry.delete(0, tk.END)
            self.description_text.delete("1.0", tk.END)
            self.season_spinbox.delete(0, tk.END)
            self.episode_spinbox.delete(0, tk.END)
            self.cover_image_label.config(image="")
            self.cover_image = None

    def toggle_pwa(self):
        if self.pwa_var.get():
            try:
                port = int(self.port_entry.get().strip())
            except ValueError:
                port = 8080
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, "8080")
            save_config({'port': port})
            self.port_entry.config(state='disabled')
            self._pwa_server = []
            threading.Thread(target=start_server, args=(self._pwa_server, port), daemon=True).start()
            ip = socket.gethostbyname(socket.gethostname())
            self.pwa_check.config(text=f"PWA: http://{ip}:{port}")
        else:
            if hasattr(self, "_pwa_server") and self._pwa_server:
                threading.Thread(target=self._pwa_server[0].shutdown, daemon=True).start()
                self._pwa_server = []
            self.port_entry.config(state='normal')
            self.pwa_check.config(text="Start PWA")

    def _poll_file(self):
        """Check every 2s if show_data.json changed and reload if so."""
        try:
            mtime = os.path.getmtime(DATA_FILE)
            if mtime != self._last_mtime:
                self._last_mtime = mtime
                self.show_data = self.load_data()
                self.refresh_show_list()
        except FileNotFoundError:
            pass
        self.master.after(2000, self._poll_file)

    def load_data(self):
        """Loads show data from the JSON file."""
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_data(self, data):
        """Saves show data to the JSON file."""
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def save_data_to_json(self):
        """Saves the current show data to the JSON file."""
        with open(DATA_FILE, 'w') as json_file:
            json.dump(self.show_data, json_file, indent=4)

root = tk.Tk()
app = ShowTracker(root)
root.mainloop()
