import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# List of baseline CSV files expected in the root directory
BASELINE_CSV_FILES = [
    "sales_history_24m_piacenza_enhanced.csv",
    "products_master_enhanced.csv",
    "product_lifecycle.csv",
    "sales_forecast_12m_piacenza.csv",
    "leadtime_history_24m_piacenza.csv",
]


class MEIOApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("MEIO Shop v1")
        self.geometry("1000x600")

        # Root directory where this script lives
        self.root_dir = os.path.dirname(os.path.abspath(__file__))

        # Currently loaded CSV file path
        self.current_csv_path = None

        # Configure grid layout: 1 row, 2 columns
        self.columnconfigure(0, weight=0)  # sidebar fixed
        self.columnconfigure(1, weight=1)  # main area expands
        self.rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_area()

        # Load baseline CSV files on startup
        self._populate_baseline_files()

    # ----------------- UI creation -----------------

    def _create_sidebar(self):
        """Create the left menu sidebar."""
        sidebar = tk.Frame(self, width=220, bg="#2c3e50")
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)  # keep fixed width

        # Title in sidebar
        title_label = tk.Label(
            sidebar,
            text="CSV Files",
            fg="white",
            bg="#2c3e50",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            padx=10,
        )
        title_label.pack(fill="x", pady=(10, 5))

        # Listbox for files
        self.file_listbox = tk.Listbox(
            sidebar,
            activestyle="dotbox",
            bg="#34495e",
            fg="white",
            selectbackground="#1abc9c",
            selectforeground="black",
            borderwidth=0,
        )
        self.file_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_selected)

        # Button to add more CSV files
        add_button = tk.Button(
            sidebar,
            text="Add CSV...",
            command=self._add_csv_file,
            bg="#1abc9c",
            fg="black",
            activebackground="#16a085",
            relief="flat",
            padx=5,
            pady=5,
        )
        add_button.pack(fill="x", padx=10, pady=(0, 10))

    def _create_main_area(self):
        """Create the main display area."""
        main_frame = tk.Frame(self, bg="#ecf0f1")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Header
        header_label = tk.Label(
            main_frame,
            text="MEIO Shop - CSV Preview",
            font=("Segoe UI", 14, "bold"),
            bg="#ecf0f1",
            anchor="w",
        )
        header_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Treeview for table preview
        self.table = ttk.Treeview(main_frame, show="headings")
        self.table.grid(row=1, column=0, sticky="nsew")

        # Scrollbars
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.table.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            main_frame,
            textvariable=self.status_var,
            bd=1,
            relief="sunken",
            anchor="w",
            bg="#bdc3c7",
        )
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))

    # ----------------- Data loading -----------------

    def _populate_baseline_files(self):
        """Populate the sidebar with the baseline CSV files if they exist."""
        self.file_listbox.delete(0, tk.END)
        existing_files = []

        for fname in BASELINE_CSV_FILES:
            path = os.path.join(self.root_dir, fname)
            if os.path.isfile(path):
                existing_files.append(fname)

        if not existing_files:
            self.status_var.set("No baseline CSV files found in the program root.")
        else:
            for fname in existing_files:
                self.file_listbox.insert(tk.END, fname)
            self.status_var.set(
                f"Loaded {len(existing_files)} baseline CSV file(s) from root."
            )

    def _add_csv_file(self):
        """Let the user select additional CSV files to show in the sidebar."""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return

        # Use just the file name as the list entry, but store full path in a dict
        fname = os.path.basename(file_path)
        # Avoid duplicates in listbox
        existing = self.file_listbox.get(0, tk.END)
        if fname not in existing:
            self.file_listbox.insert(tk.END, fname)

        # Store full path for non-root files
        # For baseline files, path is root_dir / fname; for others, use chosen path
        if not hasattr(self, "_extra_paths"):
            self._extra_paths = {}
        self._extra_paths[fname] = file_path

        self.status_var.set(f"Added CSV file: {fname}")

    def _on_file_selected(self, event):
        """Callback when a CSV is selected from the sidebar."""
        selection = self.file_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        fname = self.file_listbox.get(index)

        # Determine full path
        full_path = None

        # If it's one of the baseline files and exists in root, use root path
        root_candidate = os.path.join(self.root_dir, fname)
        if os.path.isfile(root_candidate):
            full_path = root_candidate
        # Otherwise look in extra paths
        elif hasattr(self, "_extra_paths") and fname in self._extra_paths:
            full_path = self._extra_paths[fname]

        if not full_path or not os.path.isfile(full_path):
            messagebox.showerror("File not found", f"Could not find file: {fname}")
            self.status_var.set(f"Error: file not found: {fname}")
            return

        self.current_csv_path = full_path
        self._load_csv_preview(full_path)

    def _load_csv_preview(self, path, max_rows=100):
        """Load a CSV file and show a simple preview in the table."""
        import csv

        # Clear previous table
        for col in self.table["columns"]:
            self.table.heading(col, text="")
        self.table.delete(*self.table.get_children())

        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = []
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    rows.append(row)

            if not rows:
                self.status_var.set(f"{os.path.basename(path)}: file is empty.")
                return

            headers = rows[0]
            data_rows = rows[1:] if len(rows) > 1 else []

            # Set up columns
            self.table["columns"] = [f"col{i}" for i in range(len(headers))]
            for i, header in enumerate(headers):
                col_id = f"col{i}"
                self.table.heading(col_id, text=header)
                self.table.column(col_id, width=100, anchor="w")

            # Insert data
            for row in data_rows:
                # Pad or trim row length to match number of headers
                if len(row) < len(headers):
                    row = row + [""] * (len(headers) - len(row))
                elif len(row) > len(headers):
                    row = row[: len(headers)]
                self.table.insert("", "end", values=row)

            self.status_var.set(
                f"Loaded {os.path.basename(path)} "
                f"({len(data_rows)} row(s) shown, max {max_rows})."
            )

        except Exception as e:
            messagebox.showerror("Error loading CSV", str(e))
            self.status_var.set(f"Error loading CSV: {e}")


def main():
    app = MEIOApp()
    app.mainloop()


if __name__ == "__main__":
    main()
