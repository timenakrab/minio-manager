import tkinter as tk
from tkinter import ttk, messagebox, Menu, filedialog, simpledialog
from minio import Minio
import json
import os

class FileManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MinIO File Manager GUI")
        self.root.geometry("1024x720")
        self.root.configure(bg="#f0f0f0")

        # สไตล์และการจัดเรียง
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 12), padding=5)
        style.configure("TButton", font=("Arial", 12), padding=5)
        style.configure("Treeview", font=("Arial", 10))

        # Frame สำหรับ Input
        input_frame = tk.Frame(root, bg="#f0f0f0")
        input_frame.pack(pady=10, padx=20, fill=tk.X)

        self.endpoint_label = ttk.Label(input_frame, text="MinIO Endpoint:")
        self.endpoint_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        self.endpoint_entry = ttk.Entry(input_frame, width=25)
        self.endpoint_entry.grid(row=0, column=1, padx=5)

        self.access_key_label = ttk.Label(input_frame, text="Access Key:")
        self.access_key_label.grid(row=0, column=2, sticky=tk.W, padx=5)
        self.access_key_entry = ttk.Entry(input_frame, width=25)
        self.access_key_entry.grid(row=0, column=3, padx=5)

        self.secret_key_label = ttk.Label(input_frame, text="Secret Key:")
        self.secret_key_label.grid(row=0, column=4, sticky=tk.W, padx=5)
        self.secret_key_entry = ttk.Entry(input_frame, width=25, show="*")
        self.secret_key_entry.grid(row=0, column=5, padx=5)

        self.connect_button = ttk.Button(input_frame, text="Connect", command=self.connect_to_minio, state=tk.DISABLED)
        self.connect_button.grid(row=0, column=6, padx=10)

        self.output_folder = os.getcwd()  # Default output folder

        # Bind event to check if all inputs are filled
        self.endpoint_entry.bind("<KeyRelease>", self.check_inputs)
        self.access_key_entry.bind("<KeyRelease>", self.check_inputs)
        self.secret_key_entry.bind("<KeyRelease>", self.check_inputs)

        # Treeview สำหรับแสดงโครงสร้างไฟล์
        self.tree_frame = tk.Frame(root, bg="#f0f0f0")
        self.tree_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(self.tree_frame)
        self.tree.heading('#0', text='Buckets and Files', anchor='w')
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Scrollbar สำหรับ Treeview
        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Main Frame for Selected Files and Progress
        main_frame = tk.Frame(root, bg="#f0f0f0")
        main_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        # Preview Frame (Left Side)
        self.preview_frame = tk.Frame(main_frame, bg="#f0f0f0")
        self.preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.preview_label = ttk.Label(self.preview_frame, text="Selected Files:")
        self.preview_label.pack(anchor='nw')
        self.preview_listbox = tk.Listbox(self.preview_frame)
        self.preview_listbox.pack(fill=tk.BOTH, expand=True)
        self.preview_listbox.bind('<<ListboxSelect>>', self.check_download_button_state)

        # Progress Frame (Right Side)
        self.progress_frame = tk.Frame(main_frame, bg="#f0f0f0")
        self.progress_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.progress_label = ttk.Label(self.progress_frame, text="Download Progress:")
        self.progress_label.pack(anchor='nw')

        self.progress_text = tk.Text(self.progress_frame, height=10, wrap='none')
        self.progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.progress_scrollbar = ttk.Scrollbar(self.progress_frame, orient="vertical", command=self.progress_text.yview)
        self.progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.progress_text.configure(yscrollcommand=self.progress_scrollbar.set)

        # Frame สำหรับปุ่มเพิ่มเติม
        button_frame = tk.Frame(root, bg="#f0f0f0")
        button_frame.pack(pady=10, padx=20, fill=tk.X)

        self.download_button = ttk.Button(button_frame, text="Download", command=self.download_files, state=tk.DISABLED)
        self.download_button.pack(side=tk.LEFT, padx=10)

        self.output_folder_button = ttk.Button(button_frame, text="Select Output Folder", command=self.select_output_folder)
        self.output_folder_button.pack(side=tk.LEFT, padx=10)

        self.refresh_button = ttk.Button(button_frame, text="Refresh Buckets", command=self.load_buckets, state=tk.DISABLED)
        self.refresh_button.pack(side=tk.LEFT, padx=10)

        # Load config if exists
        self.load_config()

        # Right-click menu for Treeview
        self.menu = Menu(self.tree, tearoff=0)
        self.menu.add_command(label="Select", command=self.select_file)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Control-Button-1>", self.show_context_menu)
        self.tree.bind("<Button-2>", self.show_context_menu)

        # Right-click menu for Listbox (Preview)
        self.preview_menu = Menu(self.preview_listbox, tearoff=0)
        self.preview_menu.add_command(label="Delete", command=self.delete_selected_file)
        self.preview_listbox.bind("<Button-3>", self.show_preview_context_menu)
        self.preview_listbox.bind("<Control-Button-1>", self.show_preview_context_menu)
        self.preview_listbox.bind("<Button-2>", self.show_preview_context_menu)

    def check_inputs(self, event):
        if self.endpoint_entry.get() and self.access_key_entry.get() and self.secret_key_entry.get():
            self.connect_button.config(state=tk.NORMAL)
        else:
            self.connect_button.config(state=tk.DISABLED)

    def connect_to_minio(self):
        endpoint = self.endpoint_entry.get()
        access_key = self.access_key_entry.get()
        secret_key = self.secret_key_entry.get()

        try:
            self.minio_client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False
            )
            messagebox.showinfo("Success", "Connected to MinIO Server successfully!")
            self.save_config(endpoint, access_key, secret_key)
            self.load_buckets()
            self.refresh_button.config(state=tk.NORMAL)
        except Exception as e:
            print(f"Error: Failed to connect to MinIO: {str(e)}")
            messagebox.showerror("Error", f"Failed to connect to MinIO: {str(e)}")

    def load_buckets(self):
        # ล้าง Treeview ก่อนโหลดใหม่
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            buckets = self.minio_client.list_buckets()
            for bucket in buckets:
                bucket_node = self.tree.insert('', 'end', text=bucket.name, open=False)
                self.load_objects(bucket.name, bucket_node)
        except Exception as e:
            print(f"Error: Failed to load buckets: {str(e)}")
            messagebox.showerror("Error", f"Failed to load buckets: {str(e)}")

    def load_objects(self, bucket_name, parent):
        try:
            objects = self.minio_client.list_objects(bucket_name, recursive=True)
            for obj in objects:
                path_parts = obj.object_name.split('/')
                current_parent = parent
                for i, part in enumerate(path_parts):
                    # ตรวจสอบว่าโหนดย่อยมีอยู่แล้วหรือไม่ ถ้าไม่มีให้เพิ่ม
                    existing_node = self.find_existing_node(current_parent, part)
                    if existing_node:
                        current_parent = existing_node
                    else:
                        if i == len(path_parts) - 1:  # If it's the last part (file)
                            current_parent = self.tree.insert(current_parent, 'end', text=part, tags=('file',))
                        else:
                            current_parent = self.tree.insert(current_parent, 'end', text=part)
        except Exception as e:
            print(f"Error: Failed to load objects: {str(e)}")
            messagebox.showerror("Error", f"Failed to load objects: {str(e)}")

    def find_existing_node(self, parent, text):
        # ค้นหาโหนดที่มีข้อความที่ตรงกันภายใต้โหนด parent
        for child in self.tree.get_children(parent):
            if self.tree.item(child, 'text') == text:
                return child
        return None

    def show_context_menu(self, event):
        # แสดงเมนูคลิกขวาเมื่อคลิกที่ Treeview
        selected_item = self.tree.identify_row(event.y)
        if selected_item:
            self.tree.selection_set(selected_item)
            # self.menu.post(event.x_root, event.y_root)
            self.menu.tk_popup(event.x_root, event.y_root)

    def show_preview_context_menu(self, event):
        # แสดงเมนูคลิกขวาเมื่อคลิกที่ Listbox (Preview)
        if self.preview_listbox.size() > 0:
            # self.preview_menu.post(event.x_root, event.y_root)
            self.preview_menu.tk_popup(event.x_root, event.y_root)

    def select_file(self):
        # เพิ่มไฟล์ที่เลือกในรายการ preview พร้อม path เต็ม
        selected_item = self.tree.selection()[0]
        full_path = self.get_full_path(selected_item)
        if 'file' in self.tree.item(selected_item, 'tags'):
            self.preview_listbox.insert(tk.END, full_path)
        self.check_download_button_state()

    def get_full_path(self, item):
        # สร้าง path เต็มจากโหนดที่เลือก
        path = self.tree.item(item, 'text')
        parent = self.tree.parent(item)
        while parent:
            path = f"{self.tree.item(parent, 'text')}/{path}"
            parent = self.tree.parent(parent)
        return path

    def check_download_button_state(self, event=None):
        # ตรวจสอบว่ามีการเลือกไฟล์อย่างน้อยหนึ่งไฟล์ใน preview_listbox หรือไม่
        if self.preview_listbox.size() > 0:
            self.download_button.config(state=tk.NORMAL)
        else:
            self.download_button.config(state=tk.DISABLED)

    def delete_selected_file(self):
        # ลบไฟล์ที่เลือกจากรายการ preview
        try:
            selected_index = self.preview_listbox.curselection()
            if selected_index:
                self.preview_listbox.delete(selected_index)
                self.check_download_button_state()
        except Exception as e:
            print(f"Error: Failed to delete selected file: {str(e)}")
            messagebox.showerror("Error", f"Failed to delete selected file: {str(e)}")

    def download_files(self):
        # ดาวน์โหลดไฟล์ที่เลือกไว้
        selected_files = self.preview_listbox.get(0, tk.END)
        if not selected_files:
            messagebox.showwarning("Warning", "No files selected for download.")
            return

        self.progress_text.delete(1.0, tk.END)  # Clear previous progress

        for file_path in selected_files:
            try:
                # แยก bucket_name และ object_name จาก path
                path_parts = file_path.split('/', 1)
                if len(path_parts) != 2:
                    messagebox.showerror("Error", f"Invalid file path: {file_path}")
                    continue
                bucket_name, object_name = path_parts

                # Replace ':' with '_' in local path to avoid issues on Windows
                local_object_name = object_name.replace(':', '_')
                local_path = os.path.join(self.output_folder, local_object_name)
                local_dir = os.path.dirname(local_path)
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir)

                response = self.minio_client.get_object(bucket_name, object_name)
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded_size = 0

                with open(local_path, 'wb') as file_data:
                    for d in response.stream(32*1024):
                        file_data.write(d)
                        downloaded_size += len(d)

                # Add to progress only when download is complete
                self.progress_text.insert(tk.END, f"'{object_name}': 100%\n")
                self.progress_text.see(tk.END)
            except Exception as e:
                print(f"Error: Failed to download file '{file_path}': {str(e)}")
                messagebox.showerror("Error", f"Failed to download file '{file_path}': {str(e)}")

    def select_output_folder(self):
        # เลือกโฟลเดอร์ปลายทางสำหรับการดาวน์โหลดไฟล์
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder = folder_selected
            messagebox.showinfo("Output Folder Selected", f"Output folder set to: {self.output_folder}")
            self.save_config(self.endpoint_entry.get(), self.access_key_entry.get(), self.secret_key_entry.get())

    def save_config(self, endpoint, access_key, secret_key):
        config = {
            "endpoint": endpoint,
            "access_key": access_key,
            "secret_key": secret_key,
            "output_folder": self.output_folder
        }
        with open("minio_config.json", "w") as config_file:
            json.dump(config, config_file)

    def load_config(self):
        if os.path.exists("minio_config.json"):
            with open("minio_config.json", "r") as config_file:
                config = json.load(config_file)
                self.endpoint_entry.insert(0, config.get("endpoint", ""))
                self.access_key_entry.insert(0, config.get("access_key", ""))
                self.secret_key_entry.insert(0, config.get("secret_key", ""))
                self.output_folder = config.get("output_folder", os.getcwd())
                self.check_inputs(None)

if __name__ == "__main__":
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()
