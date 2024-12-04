import tkinter as tk
from tkinter import ttk, messagebox, Menu, filedialog, simpledialog
from minio import Minio
import json
import os
import platform
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from urllib3 import PoolManager, Timeout

class FileManagerApp:
    def __init__(self, root):
      self.root = root
      self.minio_client = None
      self.is_connected = False
      self.root.title("MinIO File Manager GUI")
      self.root.geometry("1024x720")
      self.root.configure(bg="#323232")
      self.root.state('zoomed')

      style = ttk.Style()
      style.configure("TLabel", font=("Arial", 12), padding=5)
      style.configure("TButton", font=("Arial", 12), padding=5)
      style.configure("Treeview", font=("Arial", 14))

      input_frame = tk.Frame(root, bg="#323232")
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

      self.disconnect_button = ttk.Button(input_frame, text="Disconnect", command=self.disconnect_from_minio, state=tk.DISABLED)
      self.disconnect_button.grid(row=0, column=7, padx=10)

      self.endpoint_entry.bind("<KeyRelease>", self.check_inputs)
      self.access_key_entry.bind("<KeyRelease>", self.check_inputs)
      self.secret_key_entry.bind("<KeyRelease>", self.check_inputs)

      self.tree_frame = tk.Frame(root, bg="#323232")
      self.tree_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

      self.tree = ttk.Treeview(self.tree_frame)
      self.tree.heading('#0', text='Buckets and Files', anchor='w')

      self.scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
      self.tree.configure(yscroll=self.scrollbar.set)

      self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
      self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)

      self.output_frame = tk.Frame(self.tree_frame, bg="#323232")
      self.output_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

      output_header_frame = tk.Frame(self.output_frame, bg="#e0e0e0")
      output_header_frame.pack(fill=tk.X)

      self.output_tree = ttk.Treeview(self.output_frame)
      self.output_tree.heading('#0', text='Output Files and Folders', anchor='w')

      self.output_scrollbar = ttk.Scrollbar(self.output_frame, orient="vertical", command=self.output_tree.yview)
      self.output_tree.configure(yscrollcommand=self.output_scrollbar.set)

      self.output_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
      self.output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

      main_frame = tk.Frame(root, bg="#323232")
      main_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

      self.preview_frame = tk.Frame(main_frame, bg="#323232")
      self.preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

      self.preview_label = ttk.Label(self.preview_frame, text="Selected Files:")
      self.preview_label.pack(anchor='nw')

      self.preview_listbox = tk.Listbox(self.preview_frame)
      self.preview_listbox.pack(fill=tk.BOTH, expand=True)
      self.preview_listbox.bind('<<ListboxSelect>>', self.check_download_button_state)

      self.progress_frame = tk.Frame(main_frame, bg="#323232")
      self.progress_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

      self.progress_label = ttk.Label(self.progress_frame, text="Download Progress:")
      self.progress_label.pack(anchor='nw')

      self.progress_text = tk.Text(self.progress_frame, height=10, wrap='none')
      self.progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

      self.progress_scrollbar = ttk.Scrollbar(self.progress_frame, orient="vertical", command=self.progress_text.yview)
      self.progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
      self.progress_text.configure(yscrollcommand=self.progress_scrollbar.set)

      button_frame = tk.Frame(root, bg="#323232")
      button_frame.pack(pady=10, padx=20, fill=tk.X)

      self.clear_button = ttk.Button(button_frame, text="Clear Selected Files", command=self.clear_selected_files, state=tk.NORMAL)
      self.clear_button.pack(side=tk.LEFT, padx=10)

      self.download_button = ttk.Button(button_frame, text="Download", command=self.download_files, state=tk.DISABLED)
      self.download_button.pack(side=tk.LEFT, padx=10)

      self.output_folder_button = ttk.Button(button_frame, text="Select Output Folder", command=self.select_output_folder)
      self.output_folder_button.pack(side=tk.LEFT, padx=10)

      self.refresh_button = ttk.Button(button_frame, text="Refresh Buckets", command=self.load_buckets, state=tk.DISABLED)
      self.refresh_button.pack(side=tk.LEFT, padx=10)

      self.refresh_output_button = ttk.Button(button_frame, text="Refresh Output Folders", command=self.refresh_output_folders)
      self.refresh_output_button.pack(side=tk.LEFT, padx=10)

      self.menu = Menu(self.tree, tearoff=0)
      self.menu.add_command(label="Select", command=self.select_file)
      self.menu.add_command(label="Upload", command=self.upload_to_folder)
      self.tree.bind("<Button-3>", self.show_context_menu)
      self.tree.bind("<Control-Button-1>", self.show_context_menu)
      self.tree.bind("<Button-2>", self.show_context_menu)

      self.preview_menu = Menu(self.preview_listbox, tearoff=0)
      self.preview_menu.add_command(label="Delete", command=self.delete_selected_file)
      self.preview_listbox.bind("<Button-3>", self.show_preview_context_menu)
      self.preview_listbox.bind("<Control-Button-1>", self.show_preview_context_menu)
      self.preview_listbox.bind("<Button-2>", self.show_preview_context_menu)

      self.is_windows = platform.system() == 'Windows'
      self.is_linux = platform.system() == 'Linux'
      self.load_config()

    def upload_to_folder(self):
        selected_item = self.tree.selection()[0]
        folder_path = self.get_full_path(selected_item)

        if 'file' in self.tree.item(selected_item, 'tags'):
            messagebox.showerror("Error", "You can only upload to folders.")
            return

        folder_to_upload = filedialog.askdirectory()
        if not folder_to_upload:
            return

        try:
            base_folder_name = os.path.basename(folder_to_upload)
            folder_only = f"{'/'.join(folder_path.split('/')[1:])}/{base_folder_name}".rstrip('/')

            tasks = []

            # ใช้ ThreadPoolExecutor สำหรับการอัปโหลดแบบมัลติเธรด
            with ThreadPoolExecutor(max_workers=10) as executor:
                for root, dirs, files in os.walk(folder_to_upload):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        relative_path = os.path.relpath(file_path, folder_to_upload)
                        object_name = f"{folder_only}/{relative_path}".lstrip('/')

                        # สร้าง Task สำหรับการอัปโหลดไฟล์แต่ละไฟล์
                        tasks.append(
                            executor.submit(self._upload_single_file, folder_path.split('/')[0], object_name, file_path)
                        )

                # ประมวลผล Tasks พร้อมกันและจัดการข้อผิดพลาด
                for future in as_completed(tasks):
                    try:
                        result = future.result()
                        if result:
                            self._update_progress(result)
                    except Exception as e:
                        self._update_progress(f"Error during upload: {str(e)}\n")

            messagebox.showinfo("Upload Success", "All files in the folder were uploaded successfully!")
            self.load_buckets()

        except Exception as e:
            general_error_message = f"Error walking through directory {folder_to_upload}: {str(e)}"
            print(general_error_message)
            messagebox.showerror("Upload Failed", general_error_message)

    def _upload_single_file(self, bucket_name, object_name, file_path):
        try:
            with open(file_path, 'rb') as file_data:
                self.minio_client.put_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    data=file_data,
                    length=os.path.getsize(file_path)
                )
            return f"Uploaded: {object_name}\n"
        except Exception as e:
            error_message = f"Error during upload of {object_name}: {str(e)}"
            print(error_message)
            return error_message

    def check_inputs(self, event):
        if self.endpoint_entry.get() and self.access_key_entry.get() and self.secret_key_entry.get():
            self.connect_button.config(state=tk.NORMAL)
        else:
            self.connect_button.config(state=tk.DISABLED)

    def connect_to_minio(self):
        if self.is_connected:
            messagebox.showinfo("Info", "Already connected to MinIO Server.")
            return
        threading.Thread(target=self._connect_to_minio_thread).start()

    def _connect_to_minio_thread(self):
        endpoint = self.endpoint_entry.get()
        access_key = self.access_key_entry.get()
        secret_key = self.secret_key_entry.get()

        try:
            http_client = PoolManager(
                timeout=Timeout(connect=10, read=60),
                retries=False
            )
            self.minio_client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False,
                http_client=http_client
            )

            buckets = self.minio_client.list_buckets()

            self.root.after(0, lambda: messagebox.showinfo("Success", "Connected to MinIO Server successfully!"))
            self.root.after(0, lambda: self.save_config(endpoint, access_key, secret_key))
            self.root.after(0, self.load_buckets)
            self.root.after(0, lambda: self.refresh_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.disconnect_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.connect_button.config(state=tk.DISABLED))
        except Exception as e:
            self.root.after(0, lambda e=e: messagebox.showerror("Error", f"Failed to connect to MinIO: {str(e)}"))

    def disconnect_from_minio(self):
        self.minio_client = None
        self.is_connected = False
        self.refresh_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.DISABLED)
        self.connect_button.config(state=tk.NORMAL)
        for item in self.tree.get_children():
            self.tree.delete(item)
        messagebox.showinfo("Disconnected", "Disconnected from MinIO Server.")

    def load_buckets(self):
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
                    existing_node = self.find_existing_node(current_parent, part)
                    if existing_node:
                        current_parent = existing_node
                    else:
                        if i == len(path_parts) - 1:
                            current_parent = self.tree.insert(current_parent, 'end', text=part, tags=('file',))
                        else:
                            current_parent = self.tree.insert(current_parent, 'end', text=part)
        except Exception as e:
            print(f"Error: Failed to load objects: {str(e)}")
            messagebox.showerror("Error", f"Failed to load objects: {str(e)}")

    def find_existing_node(self, parent, text):
        for child in self.tree.get_children(parent):
            if self.tree.item(child, 'text') == text:
                return child
        return None

    def show_context_menu(self, event):
        selected_item = self.tree.identify_row(event.y)
        if selected_item:
            self.tree.selection_set(selected_item)
            
            # ตรวจสอบว่าเป็นโฟลเดอร์หรือไม่
            if 'file' not in self.tree.item(selected_item, 'tags'):
                self.menu.entryconfig("Upload", state=tk.NORMAL)
            else:
                self.menu.entryconfig("Upload", state=tk.DISABLED)
            
            self.menu.tk_popup(event.x_root, event.y_root)

    def show_preview_context_menu(self, event):
        if self.preview_listbox.size() > 0:
            self.preview_menu.tk_popup(event.x_root, event.y_root)

    def select_file(self):
      selected_item = self.tree.selection()[0]
      if 'file' in self.tree.item(selected_item, 'tags'):
          full_path = self.get_full_path(selected_item)
          if full_path not in self.preview_listbox.get(0, tk.END):
              self.preview_listbox.insert(tk.END, full_path)
      else:
          self.select_all_files_in_folder(selected_item)
      self.check_download_button_state()

    def select_all_files_in_folder(self, folder_item):
        children = self.tree.get_children(folder_item)
        for child in children:
            if 'file' in self.tree.item(child, 'tags'):
                full_path = self.get_full_path(child)
                if full_path not in self.preview_listbox.get(0, tk.END):
                    self.preview_listbox.insert(tk.END, full_path)
            else:
                self.select_all_files_in_folder(child)

    def get_full_path(self, item):
        path = self.tree.item(item, 'text')
        parent = self.tree.parent(item)
        while parent:
            path = f"{self.tree.item(parent, 'text')}/{path}"
            parent = self.tree.parent(parent)
        return path

    def check_download_button_state(self, event=None):
        if self.preview_listbox.size() > 0:
            self.download_button.config(state=tk.NORMAL)
        else:
            self.download_button.config(state=tk.DISABLED)

    def delete_selected_file(self):
        try:
            selected_index = self.preview_listbox.curselection()
            if selected_index:
                self.preview_listbox.delete(selected_index)
                self.check_download_button_state()
        except Exception as e:
            print(f"Error: Failed to delete selected file: {str(e)}")
            messagebox.showerror("Error", f"Failed to delete selected file: {str(e)}")

    def download_files(self):
      selected_files = self.preview_listbox.get(0, tk.END)
      if not selected_files:
          messagebox.showwarning("Warning", "No files selected for download.")
          return

      self.progress_text.delete(1.0, tk.END)
      self.download_button.config(state=tk.DISABLED)

      download_thread = threading.Thread(target=self._download_files_thread, args=(selected_files,))
      download_thread.start()

    def _download_files_thread(self, selected_files):
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(self._download_single_file, selected_files)

        for result in results:
            if result:
                self._update_progress(result)

        self._update_progress("All downloads completed.\n")
        self.download_button.config(state=tk.NORMAL)

    def _download_single_file(self, file_path):
        try:
            path_parts = file_path.split('/', 1)
            if len(path_parts) != 2:
                return f"Invalid file path: {file_path}\n"

            bucket_name, object_name = path_parts
            if self.is_windows:
                local_object_name = object_name.replace(':', '__')
            elif self.is_linux:
                local_object_name = object_name.replace(':', '__')
            else:
                local_object_name = object_name.replace(':', '__')

            local_path = os.path.join(self.output_folder, local_object_name)
            local_dir = os.path.dirname(local_path)

            if not os.path.exists(local_dir):
                os.makedirs(local_dir)

            response = self.minio_client.get_object(bucket_name, object_name)
            with open(local_path, 'wb') as file_data:
                total_size = 0
                for chunk in response.stream(5 * 1024 * 1024):
                    file_data.write(chunk)
                    total_size += len(chunk)
                    self._update_progress(f"Downloading '{object_name}': {total_size / (1024 * 1024):.2f} MB downloaded...\n")

            return f"'{object_name}': Downloaded successfully\n"
        except Exception as e:
            return f"Error downloading '{file_path}': {str(e)}\n"

    def _update_progress(self, message):
        def update():
            self.progress_text.insert(tk.END, message)
            self.progress_text.see(tk.END)
        self.root.after(0, update)

    def load_output_tree(self):
        for item in self.output_tree.get_children():
            self.output_tree.delete(item)

        if os.path.exists(self.output_folder):
            self.insert_output_tree(self.output_folder, "")

    def refresh_output_folders(self):
        self.load_output_tree()
        self._update_progress("Output folders refreshed.\n")

    def insert_output_tree(self, path, parent):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                folder_node = self.output_tree.insert(parent, 'end', text=item, open=False)
                self.insert_output_tree(item_path, folder_node)
            else:
                self.output_tree.insert(parent, 'end', text=item, open=False)

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder = folder_selected
            messagebox.showinfo("Output Folder Selected", f"Output folder set to: {self.output_folder}")
            self.save_config(self.endpoint_entry.get(), self.access_key_entry.get(), self.secret_key_entry.get())
            self.load_output_tree()

    def clear_selected_files(self):
      try:
          self.preview_listbox.delete(0, tk.END)
          self.check_download_button_state()  # อัปเดตสถานะของปุ่มดาวน์โหลด
          self._update_progress("Cleared all selected files.\n")
      except Exception as e:
          print(f"Error: Failed to clear selected files: {str(e)}")
          messagebox.showerror("Error", f"Failed to clear selected files: {str(e)}")

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
