"""
main.py
Tkinter interface for College Event Management System.
Run: python main.py
Default first-run login: admin / admin123
Change the default password after first login before real use.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

from database import Database, Error


APP_TITLE = "College Event Management System"


class EventManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1220x760")
        self.root.minsize(1000, 650)

        self.db = Database()
        self.current_user = None
        self._configure_style()

        try:
            self.db.initialize()
        except Exception as exc:
            messagebox.showerror(
                "Database setup failed",
                "Could not initialize the MySQL database.\n\n"
                f"{exc}\n\nCheck database.py and your MySQL service."
            )
            self.root.destroy()
            return

        self.show_login()

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=7)
        style.configure("Treeview", rowheight=27)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 10))
        style.configure("Metric.TLabel", font=("Segoe UI", 21, "bold"))

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def show_login(self):
        self.clear()
        frame = ttk.Frame(self.root, padding=35)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="College Event Management System",
                  style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 8))
        ttk.Label(frame, text="Administrator sign in",
                  style="Sub.TLabel").grid(row=1, column=0, columnspan=2, pady=(0, 22))

        ttk.Label(frame, text="Username").grid(row=2, column=0, sticky="w", pady=7)
        username = ttk.Entry(frame, width=32)
        username.grid(row=2, column=1, pady=7)

        ttk.Label(frame, text="Password").grid(row=3, column=0, sticky="w", pady=7)
        password = ttk.Entry(frame, width=32, show="•")
        password.grid(row=3, column=1, pady=7)

        def login(event=None):
            try:
                user = self.db.login(username.get().strip(), password.get())
                if not user:
                    messagebox.showerror("Login failed", "Invalid username or password.")
                    return
                self.current_user = user
                self.show_main()
            except Error as exc:
                messagebox.showerror("Login error", str(exc))

        ttk.Button(frame, text="Sign in", command=login).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=18
        )
        ttk.Label(
            frame, text="First-run account: admin  |  password: admin123",
            foreground="#666666"
        ).grid(row=5, column=0, columnspan=2)
        password.bind("<Return>", login)
        username.focus_set()

    def show_main(self):
        self.clear()
        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text=f"Signed in: {self.current_user['Full_Name']} ({self.current_user['Role']})"
        ).pack(side="right", padx=10)
        ttk.Button(header, text="Log out", command=self.show_login).pack(side="right")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.dashboard_tab = ttk.Frame(self.notebook, padding=16)
        self.events_tab = ttk.Frame(self.notebook, padding=12)
        self.students_tab = ttk.Frame(self.notebook, padding=12)
        self.reg_tab = ttk.Frame(self.notebook, padding=12)
        self.venues_tab = ttk.Frame(self.notebook, padding=12)
        self.reports_tab = ttk.Frame(self.notebook, padding=12)
        self.organizers_tab = ttk.Frame(self.notebook, padding=12)

        tabs = [
            ("Dashboard", self.dashboard_tab),
            ("Events", self.events_tab),
            ("Students", self.students_tab),
            ("Registrations", self.reg_tab),
            ("Venues", self.venues_tab),
            ("Organizers", self.organizers_tab),
            ("Reports", self.reports_tab),
        ]
        for label, tab in tabs:
            self.notebook.add(tab, text=label)

        self.build_dashboard()
        self.build_events()
        self.build_students()
        self.build_registrations()
        self.build_venues()
        self.build_reports()
        self.build_organizers()

    # ---------------- shared UI helpers ----------------

    def make_tree(self, parent, columns, headings=None, height=13):
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="both", expand=True, pady=8)
        tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=height)
        yscroll = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(wrapper, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        wrapper.rowconfigure(0, weight=1)
        wrapper.columnconfigure(0, weight=1)
        for col in columns:
            tree.heading(col, text=(headings or {}).get(col, col.replace("_", " ")))
            tree.column(col, width=125, minwidth=80, anchor="w")
        return tree

    def fill_tree(self, tree, rows, keys):
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", "end", values=tuple(row.get(key) for key in keys))

    def report_error(self, exc):
        messagebox.showerror("Operation failed", str(exc))

    def require_admin(self):
        if self.current_user["Role"] != "Admin":
            messagebox.showwarning("Permission denied", "This action requires the Admin role.")
            return False
        return True

    # ---------------- dashboard ----------------

    def build_dashboard(self):
        ttk.Label(self.dashboard_tab, text="Administration overview",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 14))
        metrics = ttk.Frame(self.dashboard_tab)
        metrics.pack(fill="x")
        self.metric_labels = {}
        for title in ["Upcoming Events", "Open Events", "Active Registrations", "Students"]:
            card = ttk.LabelFrame(metrics, text=title, padding=15)
            card.pack(side="left", fill="both", expand=True, padx=5)
            label = ttk.Label(card, text="—", style="Metric.TLabel")
            label.pack()
            self.metric_labels[title] = label

        actions = ttk.LabelFrame(self.dashboard_tab, text="Quick actions", padding=12)
        actions.pack(fill="x", pady=18)
        ttk.Button(actions, text="Refresh dashboard",
                   command=self.refresh_dashboard).pack(side="left", padx=4)
        ttk.Button(actions, text="Create event",
                   command=lambda: self.notebook.select(self.events_tab)).pack(side="left", padx=4)
        ttk.Button(actions, text="Register student",
                   command=lambda: self.notebook.select(self.reg_tab)).pack(side="left", padx=4)

        ttk.Label(self.dashboard_tab, text="Upcoming event schedule",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.dashboard_tree = self.make_tree(
            self.dashboard_tab,
            ("Event_ID", "Event_Name", "Event_Date", "Start_Time",
             "Venue_Name", "Status"),
            height=9
        )
        self.refresh_dashboard()

    def refresh_dashboard(self):
        try:
            counts = self.db.fetch_all("""
                SELECT
                    (SELECT COUNT(*) FROM EVENT
                     WHERE Event_Date >= CURDATE()
                       AND Status NOT IN ('Cancelled','Completed')) AS upcoming,
                    (SELECT COUNT(*) FROM EVENT WHERE Status='Open') AS open_events,
                    (SELECT COUNT(*) FROM REGISTRATION WHERE Status='Registered') AS registrations,
                    (SELECT COUNT(*) FROM STUDENT WHERE Is_Active=TRUE) AS students
            """)[0]
            values = {
                "Upcoming Events": counts["upcoming"],
                "Open Events": counts["open_events"],
                "Active Registrations": counts["registrations"],
                "Students": counts["students"],
            }
            for title, value in values.items():
                self.metric_labels[title].configure(text=str(value))
            rows = self.db.fetch_all("""
                SELECT e.Event_ID,e.Event_Name,e.Event_Date,e.Start_Time,
                       v.Venue_Name,e.Status
                FROM EVENT e JOIN VENUE v ON e.Venue_ID=v.Venue_ID
                WHERE e.Event_Date >= CURDATE()
                  AND e.Status NOT IN ('Cancelled','Completed')
                ORDER BY e.Event_Date,e.Start_Time LIMIT 20
            """)
            self.fill_tree(self.dashboard_tree, rows,
                           ("Event_ID","Event_Name","Event_Date","Start_Time","Venue_Name","Status"))
        except Error as exc:
            self.report_error(exc)

    # ---------------- events ----------------

    def build_events(self):
        ttk.Label(self.events_tab, text="Event management",
                  style="Title.TLabel").pack(anchor="w")

        # DBMS practical tools are grouped inside Events rather than in a
        # separate top-level tab.
        self.events_notebook = ttk.Notebook(self.events_tab)
        self.events_notebook.pack(fill="both", expand=True, pady=8)
        self.events_manage_frame = ttk.Frame(self.events_notebook, padding=8)
        self.events_dbms_frame = ttk.Frame(self.events_notebook, padding=8)
        self.events_notebook.add(self.events_manage_frame, text="Manage Events")
        self.events_notebook.add(self.events_dbms_frame, text="Additional Tools")

        bar = ttk.Frame(self.events_manage_frame)
        bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="Add event", command=self.event_form).pack(side="left", padx=3)
        ttk.Button(bar, text="Edit selected", command=self.edit_event).pack(side="left", padx=3)
        ttk.Button(bar, text="Cancel selected", command=self.cancel_event).pack(side="left", padx=3)
        ttk.Button(bar, text="Delete selected", command=self.delete_event).pack(side="left", padx=3)
        ttk.Button(bar, text="Refresh", command=self.refresh_events).pack(side="left", padx=3)
        self.events_tree = self.make_tree(
            self.events_manage_frame,
            ("Event_ID","Event_Name","Event_Type","Event_Date","Start_Time",
             "End_Time","Venue_Name","Organizer_Name","Max_Participants","Status"),
            height=16
        )
        self.refresh_events()
        self.build_dbms_lab(self.events_dbms_frame)

    def refresh_events(self):
        rows = self.db.fetch_all("""
            SELECT e.Event_ID,e.Event_Name,e.Event_Type,e.Event_Date,
                   e.Start_Time,e.End_Time,v.Venue_Name,o.Organizer_Name,
                   e.Max_Participants,e.Status
            FROM EVENT e
            JOIN VENUE v ON e.Venue_ID=v.Venue_ID
            JOIN ORGANIZER o ON e.Organizer_ID=o.Organizer_ID
            ORDER BY e.Event_Date,e.Start_Time
        """)
        self.fill_tree(self.events_tree, rows,
                       ("Event_ID","Event_Name","Event_Type","Event_Date","Start_Time",
                        "End_Time","Venue_Name","Organizer_Name","Max_Participants","Status"))
        self.refresh_dashboard()

    def selected_event_id(self):
        selection = self.events_tree.selection()
        if not selection:
            messagebox.showwarning("Select event", "Select an event first.")
            return None
        return int(self.events_tree.item(selection[0], "values")[0])

    def event_form(self, existing=None):
        if not self.require_admin():
            return
        win = tk.Toplevel(self.root)
        win.title("Edit event" if existing else "Create event")
        win.transient(self.root)
        win.grab_set()
        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)

        fields = [
            ("Event ID", "event_id", ""),
            ("Event name", "event_name", ""),
            ("Event type", "event_type", "Technical"),
            ("Description", "description", ""),
            ("Event date (YYYY-MM-DD)", "event_date", "2026-12-20"),
            ("Start time (HH:MM)", "start_time", "09:00"),
            ("End time (HH:MM)", "end_time", "17:00"),
            ("Registration deadline (YYYY-MM-DD)", "deadline", "2026-12-15"),
            ("Maximum participants", "capacity", "100"),
            ("Status (Draft/Open/Closed/Cancelled/Completed)", "status", "Open"),
        ]
        entries = {}
        for row, (label, key, default) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(frame, width=38)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            entry.insert(0, default)
            entries[key] = entry

        # Choose an organizer by name; the corresponding Organizer_ID is saved.
        organizers = self.db.fetch_all(
            "SELECT Organizer_ID, Organizer_Name FROM ORGANIZER ORDER BY Organizer_Name"
        )
        organizer_map = {
            f"{item['Organizer_Name']} (ID: {item['Organizer_ID']})": item["Organizer_ID"]
            for item in organizers
        }
        ttk.Label(frame, text="Organizer name").grid(
            row=len(fields), column=0, sticky="w", pady=4
        )
        organizer_choice = ttk.Combobox(
            frame, width=35, state="readonly",
            values=list(organizer_map.keys())
        )
        organizer_choice.grid(row=len(fields), column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Venue ID").grid(
            row=len(fields) + 1, column=0, sticky="w", pady=4
        )
        venue_entry = ttk.Entry(frame, width=38)
        venue_entry.grid(row=len(fields) + 1, column=1, sticky="ew", pady=4)
        entries["venue_id"] = venue_entry

        if not organizers:
            ttk.Label(
                frame, text="No organizers found. Add an organizer in the Organizers tab first.",
                foreground="red"
            ).grid(row=len(fields) + 2, column=0, columnspan=2, sticky="w", pady=4)

        if existing:
            data = self.db.fetch_all("SELECT * FROM EVENT WHERE Event_ID=%s", (existing,))
            if data:
                row_data = data[0]
                mapping = {
                    "event_id":"Event_ID","event_name":"Event_Name","event_type":"Event_Type",
                    "description":"Description","event_date":"Event_Date",
                    "start_time":"Start_Time","end_time":"End_Time",
                    "deadline":"Registration_Deadline","capacity":"Max_Participants",
                    "status":"Status","venue_id":"Venue_ID"
                }
                for key, col in mapping.items():
                    entries[key].delete(0, "end")
                    entries[key].insert(0, str(row_data[col] or ""))
                for display, organizer_id in organizer_map.items():
                    if organizer_id == row_data["Organizer_ID"]:
                        organizer_choice.set(display)
                        break

        def save():
            try:
                data = {
                    "event_id": int(entries["event_id"].get()),
                    "event_name": entries["event_name"].get().strip(),
                    "event_type": entries["event_type"].get().strip(),
                    "description": entries["description"].get().strip(),
                    "event_date": entries["event_date"].get().strip(),
                    "start_time": entries["start_time"].get().strip(),
                    "end_time": entries["end_time"].get().strip(),
                    "deadline": entries["deadline"].get().strip(),
                    "capacity": int(entries["capacity"].get()),
                    "status": entries["status"].get().strip(),
                    "organizer_id": organizer_map[organizer_choice.get()],
                    "venue_id": int(entries["venue_id"].get()),
                }
                datetime.strptime(data["event_date"], "%Y-%m-%d")
                datetime.strptime(data["deadline"], "%Y-%m-%d")
                datetime.strptime(data["start_time"], "%H:%M")
                datetime.strptime(data["end_time"], "%H:%M")
                if data["end_time"] <= data["start_time"]:
                    raise ValueError("End time must be later than start time.")
                if existing:
                    self.db.update_event(existing, data)
                else:
                    self.db.create_event(data)
                messagebox.showinfo("Saved", "Event saved successfully.")
                win.destroy()
                self.refresh_events()
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(frame, text="Save event", command=save).grid(
            row=len(fields) + 2, column=0, columnspan=2, sticky="ew", pady=12
        )

    def edit_event(self):
        event_id = self.selected_event_id()
        if event_id is not None:
            self.event_form(event_id)

    def cancel_event(self):
        if not self.require_admin():
            return
        event_id = self.selected_event_id()
        if event_id is None:
            return
        if messagebox.askyesno("Cancel event", "Mark this event as Cancelled?"):
            try:
                self.db.execute("UPDATE EVENT SET Status='Cancelled' WHERE Event_ID=%s",
                                (event_id,))
                self.refresh_events()
            except Exception as exc:
                self.report_error(exc)

    def delete_event(self):
        if not self.require_admin():
            return
        event_id = self.selected_event_id()
        if event_id is None:
            return
        if not messagebox.askyesno(
            "Delete event", "Permanently delete this event? It must have no registrations."
        ):
            return
        try:
            self.db.execute("DELETE FROM EVENT WHERE Event_ID=%s", (event_id,))
            self.refresh_events()
        except Exception as exc:
            self.report_error(exc)

    # ---------------- students ----------------

    def build_students(self):
        ttk.Label(self.students_tab, text="Student records",
                  style="Title.TLabel").pack(anchor="w")
        bar = ttk.Frame(self.students_tab)
        bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="Add student", command=self.student_form).pack(side="left", padx=3)
        ttk.Button(bar, text="Edit selected", command=self.edit_student).pack(side="left", padx=3)
        ttk.Button(bar, text="Deactivate selected", command=self.deactivate_student).pack(side="left", padx=3)
        ttk.Button(bar, text="Refresh", command=self.refresh_students).pack(side="left", padx=3)
        self.students_tree = self.make_tree(
            self.students_tab,
            ("Student_ID","Name","Email","Phone","Department","Academic_Year","Is_Active"),
            height=16
        )
        self.refresh_students()

    def refresh_students(self):
        rows = self.db.fetch_all("""
            SELECT Student_ID,Name,Email,Phone,Department,Academic_Year,Is_Active
            FROM STUDENT ORDER BY Student_ID
        """)
        self.fill_tree(self.students_tree, rows,
                       ("Student_ID","Name","Email","Phone","Department","Academic_Year","Is_Active"))

    def selected_student_id(self):
        selection = self.students_tree.selection()
        if not selection:
            messagebox.showwarning("Select student", "Select a student first.")
            return None
        return int(self.students_tree.item(selection[0], "values")[0])

    def student_form(self, existing=None):
        if not self.require_admin():
            return
        win = tk.Toplevel(self.root)
        win.title("Edit student" if existing else "Add student")
        win.transient(self.root)
        win.grab_set()
        frame = ttk.Frame(win, padding=18)
        frame.pack()
        labels = ["Student ID","Name","Email","Phone","Department","Academic year (1-4)"]
        keys = ["id","name","email","phone","department","year"]
        entries = {}
        for i, (label, key) in enumerate(zip(labels, keys)):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=5)
            ent = ttk.Entry(frame, width=35)
            ent.grid(row=i, column=1, pady=5)
            entries[key] = ent

        if existing is not None:
            row = self.db.fetch_all("SELECT * FROM STUDENT WHERE Student_ID=%s", (existing,))[0]
            vals = [row["Student_ID"],row["Name"],row["Email"],row["Phone"],
                    row["Department"],row["Academic_Year"]]
            for ent, val in zip(entries.values(), vals):
                ent.insert(0, str(val or ""))

        def save():
            try:
                vals = (
                    int(entries["id"].get()), entries["name"].get().strip(),
                    entries["email"].get().strip(), entries["phone"].get().strip(),
                    entries["department"].get().strip(), int(entries["year"].get())
                )
                if existing is None:
                    self.db.execute(
                        """INSERT INTO STUDENT
                           (Student_ID,Name,Email,Phone,Department,Academic_Year)
                           VALUES (%s,%s,%s,%s,%s,%s)""", vals
                    )
                else:
                    self.db.execute(
                        """UPDATE STUDENT SET Name=%s,Email=%s,Phone=%s,
                           Department=%s,Academic_Year=%s WHERE Student_ID=%s""",
                        (vals[1],vals[2],vals[3],vals[4],vals[5],existing)
                    )
                win.destroy()
                self.refresh_students()
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(frame, text="Save student", command=save).grid(
            row=len(labels), column=0, columnspan=2, sticky="ew", pady=12
        )

    def edit_student(self):
        student_id = self.selected_student_id()
        if student_id is not None:
            self.student_form(student_id)

    def deactivate_student(self):
        if not self.require_admin():
            return
        student_id = self.selected_student_id()
        if student_id is not None and messagebox.askyesno(
            "Deactivate student", "Deactivate this student account?"
        ):
            try:
                self.db.execute("UPDATE STUDENT SET Is_Active=FALSE WHERE Student_ID=%s",
                                (student_id,))
                self.refresh_students()
            except Exception as exc:
                self.report_error(exc)

    # ---------------- registrations and attendance ----------------

    def build_registrations(self):
        ttk.Label(self.reg_tab, text="Registration and attendance",
                  style="Title.TLabel").pack(anchor="w")
        controls = ttk.LabelFrame(self.reg_tab, text="Register a student", padding=10)
        controls.pack(fill="x", pady=8)
        ttk.Label(controls, text="Student ID").grid(row=0, column=0, padx=4)
        self.reg_student = ttk.Entry(controls, width=14)
        self.reg_student.grid(row=0, column=1, padx=4)
        ttk.Label(controls, text="Event ID").grid(row=0, column=2, padx=4)
        self.reg_event = ttk.Entry(controls, width=14)
        self.reg_event.grid(row=0, column=3, padx=4)
        ttk.Button(controls, text="Register", command=self.register_student).grid(
            row=0, column=4, padx=8
        )
        ttk.Button(controls, text="Refresh", command=self.refresh_registrations).grid(
            row=0, column=5, padx=4
        )

        actions = ttk.Frame(self.reg_tab)
        actions.pack(fill="x", pady=5)
        ttk.Button(actions, text="Cancel registration",
                   command=lambda: self.set_registration_status("Cancelled")).pack(side="left", padx=3)
        ttk.Button(actions, text="Mark attended",
                   command=lambda: self.set_registration_status("Attended")).pack(side="left", padx=3)
        ttk.Button(actions, text="Mark absent",
                   command=lambda: self.set_registration_status("Absent")).pack(side="left", padx=3)
        ttk.Button(actions, text="View event roster",
                   command=self.show_event_roster).pack(side="left", padx=3)

        self.reg_tree = self.make_tree(
            self.reg_tab,
            ("Registration_ID","Student_ID","Student_Name","Event_ID",
             "Event_Name","Reg_Date","Status"),
            height=14
        )
        self.refresh_registrations()

    def refresh_registrations(self):
        rows = self.db.fetch_all("""
            SELECT r.Registration_ID,r.Student_ID,s.Name AS Student_Name,
                   r.Event_ID,e.Event_Name,r.Reg_Date,r.Status
            FROM REGISTRATION r
            JOIN STUDENT s ON s.Student_ID=r.Student_ID
            JOIN EVENT e ON e.Event_ID=r.Event_ID
            ORDER BY r.Reg_Date DESC
        """)
        self.fill_tree(self.reg_tree, rows,
                       ("Registration_ID","Student_ID","Student_Name","Event_ID",
                        "Event_Name","Reg_Date","Status"))
        self.refresh_dashboard()

    def selected_registration_id(self):
        selection = self.reg_tree.selection()
        if not selection:
            messagebox.showwarning("Select registration", "Select a registration first.")
            return None
        return int(self.reg_tree.item(selection[0], "values")[0])

    def register_student(self):
        try:
            student_id = int(self.reg_student.get())
            event_id = int(self.reg_event.get())
            registration_id = self.db.register_student(student_id, event_id)
            messagebox.showinfo("Registration successful",
                                f"Registration created. ID: {registration_id}")
            self.refresh_registrations()
        except Exception as exc:
            self.report_error(exc)

    def set_registration_status(self, status):
        if not self.require_admin():
            return
        registration_id = self.selected_registration_id()
        if registration_id is None:
            return
        try:
            self.db.change_registration_status(
                registration_id, status, self.current_user["Username"]
            )
            self.refresh_registrations()
            messagebox.showinfo("Updated", f"Registration marked as {status}.")
        except Exception as exc:
            self.report_error(exc)

    def show_event_roster(self):
        event_id = simpledialog.askinteger("Event roster", "Enter Event ID:", parent=self.root)
        if event_id is None:
            return
        try:
            rows = self.db.event_roster(event_id)
            win = tk.Toplevel(self.root)
            win.title(f"Event {event_id} roster")
            tree = self.make_tree(
                win, ("Student_ID","Name","Email"), height=15
            )
            for row in rows:
                tree.insert("", "end", values=row)
            if not rows:
                ttk.Label(win, text="No registrations found for this event.").pack()
        except Exception as exc:
            self.report_error(exc)

    # ---------------- venues ----------------

    def build_venues(self):
        ttk.Label(self.venues_tab, text="Venue management and schedule",
                  style="Title.TLabel").pack(anchor="w")
        bar = ttk.Frame(self.venues_tab)
        bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="Add venue", command=self.venue_form).pack(side="left", padx=3)
        ttk.Button(bar, text="Refresh venues", command=self.refresh_venues).pack(side="left", padx=3)
        ttk.Button(bar, text="Check availability", command=self.check_venue_availability).pack(side="left", padx=3)
        self.venues_tree = self.make_tree(
            self.venues_tab,
            ("Venue_ID","Venue_Name","Location","Capacity","Is_Active"),
            height=8
        )
        self.refresh_venues()
        ttk.Label(self.venues_tab, text="Scheduled venue bookings",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8,0))
        self.booking_tree = self.make_tree(
            self.venues_tab,
            ("Event_ID","Event_Name","Event_Date","Start_Time","End_Time","Venue_Name","Status"),
            height=7
        )
        self.refresh_bookings()

    def refresh_venues(self):
        rows = self.db.fetch_all(
            "SELECT Venue_ID,Venue_Name,Location,Capacity,Is_Active FROM VENUE ORDER BY Venue_ID"
        )
        self.fill_tree(self.venues_tree, rows,
                       ("Venue_ID","Venue_Name","Location","Capacity","Is_Active"))

    def refresh_bookings(self):
        rows = self.db.fetch_all("""
            SELECT e.Event_ID,e.Event_Name,e.Event_Date,e.Start_Time,e.End_Time,
                   v.Venue_Name,e.Status
            FROM EVENT e JOIN VENUE v ON v.Venue_ID=e.Venue_ID
            WHERE e.Status <> 'Cancelled'
            ORDER BY e.Event_Date,e.Start_Time
        """)
        self.fill_tree(self.booking_tree, rows,
                       ("Event_ID","Event_Name","Event_Date","Start_Time",
                        "End_Time","Venue_Name","Status"))

    def venue_form(self):
        if not self.require_admin():
            return
        venue_id = simpledialog.askinteger("New venue", "Venue ID:", parent=self.root)
        if venue_id is None:
            return
        name = simpledialog.askstring("New venue", "Venue name:", parent=self.root)
        if not name:
            return
        location = simpledialog.askstring("New venue", "Location:", parent=self.root) or ""
        capacity = simpledialog.askinteger("New venue", "Capacity:", parent=self.root, minvalue=1)
        if capacity is None:
            return
        try:
            self.db.execute(
                """INSERT INTO VENUE (Venue_ID,Venue_Name,Location,Capacity)
                   VALUES (%s,%s,%s,%s)""",
                (venue_id,name,location,capacity)
            )
            self.refresh_venues()
        except Exception as exc:
            self.report_error(exc)

    def check_venue_availability(self):
        venue_id = simpledialog.askinteger("Venue availability", "Venue ID:", parent=self.root)
        if venue_id is None:
            return
        date = simpledialog.askstring("Venue availability", "Date (YYYY-MM-DD):", parent=self.root)
        start = simpledialog.askstring("Venue availability", "Start time (HH:MM):", parent=self.root)
        end = simpledialog.askstring("Venue availability", "End time (HH:MM):", parent=self.root)
        if not all([date, start, end]):
            return
        try:
            conflicts = self.db.check_venue_conflict(venue_id, date, start, end)
            if conflicts:
                details = "\n".join(
                    f"{r['Event_Name']}: {r['Start_Time']}–{r['End_Time']}"
                    for r in conflicts
                )
                messagebox.showwarning("Venue unavailable", details)
            else:
                messagebox.showinfo("Venue available", "No overlapping event was found.")
        except Exception as exc:
            self.report_error(exc)

    # ---------------- organizers ----------------

    def build_organizers(self):
        ttk.Label(self.organizers_tab, text="Organizer management",
                  style="Title.TLabel").pack(anchor="w")
        bar = ttk.Frame(self.organizers_tab)
        bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="Add organizer", command=self.organizer_form).pack(side="left", padx=3)
        ttk.Button(bar, text="Edit selected", command=self.edit_organizer).pack(side="left", padx=3)
        ttk.Button(bar, text="Delete selected", command=self.delete_organizer).pack(side="left", padx=3)
        ttk.Button(bar, text="Refresh", command=self.refresh_organizers).pack(side="left", padx=3)
        self.organizers_tree = self.make_tree(
            self.organizers_tab,
            ("Organizer_ID", "Organizer_Name", "Contact", "Email"),
            height=16
        )
        self.refresh_organizers()

    def refresh_organizers(self):
        rows = self.db.fetch_all("""
            SELECT Organizer_ID, Organizer_Name, Contact, Email
            FROM ORGANIZER ORDER BY Organizer_Name
        """)
        self.fill_tree(
            self.organizers_tree, rows,
            ("Organizer_ID", "Organizer_Name", "Contact", "Email")
        )

    def selected_organizer_id(self):
        selection = self.organizers_tree.selection()
        if not selection:
            messagebox.showwarning("Select organizer", "Select an organizer first.")
            return None
        return int(self.organizers_tree.item(selection[0], "values")[0])

    def organizer_form(self, existing=None):
        if not self.require_admin():
            return
        win = tk.Toplevel(self.root)
        win.title("Edit organizer" if existing else "Add organizer")
        win.transient(self.root)
        win.grab_set()
        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)

        labels = ["Organizer ID", "Organizer name", "Contact number", "Email"]
        keys = ["id", "name", "contact", "email"]
        entries = {}
        for i, (label, key) in enumerate(zip(labels, keys)):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=5)
            entry = ttk.Entry(frame, width=38)
            entry.grid(row=i, column=1, pady=5)
            entries[key] = entry

        if existing is not None:
            row = self.db.fetch_all(
                "SELECT * FROM ORGANIZER WHERE Organizer_ID=%s", (existing,)
            )[0]
            for key, column in [
                ("id", "Organizer_ID"), ("name", "Organizer_Name"),
                ("contact", "Contact"), ("email", "Email")
            ]:
                entries[key].insert(0, str(row[column] or ""))

        def save():
            try:
                organizer_id = int(entries["id"].get())
                name = entries["name"].get().strip()
                contact = entries["contact"].get().strip()
                email = entries["email"].get().strip()
                if not name:
                    raise ValueError("Organizer name is required.")
                if existing is None:
                    self.db.execute(
                        """INSERT INTO ORGANIZER
                           (Organizer_ID, Organizer_Name, Contact, Email)
                           VALUES (%s,%s,%s,%s)""",
                        (organizer_id, name, contact, email)
                    )
                else:
                    self.db.execute(
                        """UPDATE ORGANIZER
                           SET Organizer_Name=%s, Contact=%s, Email=%s
                           WHERE Organizer_ID=%s""",
                        (name, contact, email, existing)
                    )
                win.destroy()
                self.refresh_organizers()
                self.refresh_events()
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(frame, text="Save organizer", command=save).grid(
            row=len(labels), column=0, columnspan=2, sticky="ew", pady=12
        )

    def edit_organizer(self):
        organizer_id = self.selected_organizer_id()
        if organizer_id is not None:
            self.organizer_form(organizer_id)

    def delete_organizer(self):
        if not self.require_admin():
            return
        organizer_id = self.selected_organizer_id()
        if organizer_id is None:
            return
        if not messagebox.askyesno(
            "Delete organizer",
            "Delete this organizer? Organizers assigned to existing events cannot be deleted."
        ):
            return
        try:
            self.db.execute(
                "DELETE FROM ORGANIZER WHERE Organizer_ID=%s", (organizer_id,)
            )
            self.refresh_organizers()
        except Exception as exc:
            self.report_error(exc)

    # ---------------- reports ----------------

    def build_reports(self):
        ttk.Label(self.reports_tab, text="Administrative reports",
                  style="Title.TLabel").pack(anchor="w")
        bar = ttk.Frame(self.reports_tab)
        bar.pack(fill="x", pady=8)
        self.report_choice = tk.StringVar(value="Event popularity")
        choices = [
            "Event popularity", "Department-wise registrations",
            "Attendance summary", "Venue utilization",
            "Cancelled registrations", "Upcoming events"
        ]
        ttk.Combobox(bar, textvariable=self.report_choice, values=choices,
                     state="readonly", width=32).pack(side="left", padx=4)
        ttk.Button(bar, text="Generate report", command=self.generate_report).pack(side="left", padx=4)
        self.report_tree = self.make_tree(self.reports_tab, ("Column_1","Column_2","Column_3","Column_4"),
                                          height=18)

    def generate_report(self):
        report = self.report_choice.get()
        report_sql = {
            "Event popularity": """
                SELECT e.Event_Name,
                       COUNT(CASE WHEN r.Status='Registered' THEN 1 END) AS Active_Registrations,
                       e.Max_Participants,
                       ROUND(100.0*COUNT(CASE WHEN r.Status='Registered' THEN 1 END)
                             / e.Max_Participants,1) AS Capacity_Percent
                FROM EVENT e LEFT JOIN REGISTRATION r ON r.Event_ID=e.Event_ID
                GROUP BY e.Event_ID,e.Event_Name,e.Max_Participants
                ORDER BY Active_Registrations DESC
            """,
            "Department-wise registrations": """
                SELECT s.Department, COUNT(*) AS Registrations,
                       COUNT(DISTINCT s.Student_ID) AS Students,
                       COUNT(DISTINCT r.Event_ID) AS Events
                FROM STUDENT s JOIN REGISTRATION r ON r.Student_ID=s.Student_ID
                WHERE r.Status <> 'Cancelled'
                GROUP BY s.Department ORDER BY Registrations DESC
            """,
            "Attendance summary": """
                SELECT e.Event_Name,
                       COUNT(CASE WHEN r.Status='Attended' THEN 1 END) AS Attended,
                       COUNT(CASE WHEN r.Status='Absent' THEN 1 END) AS Absent,
                       COUNT(CASE WHEN r.Status='Registered' THEN 1 END) AS Pending
                FROM EVENT e LEFT JOIN REGISTRATION r ON r.Event_ID=e.Event_ID
                GROUP BY e.Event_ID,e.Event_Name ORDER BY e.Event_Date
            """,
            "Venue utilization": """
                SELECT v.Venue_Name, COUNT(e.Event_ID) AS Events_Hosted,
                       v.Capacity, v.Location
                FROM VENUE v LEFT JOIN EVENT e
                  ON e.Venue_ID=v.Venue_ID AND e.Status <> 'Cancelled'
                GROUP BY v.Venue_ID,v.Venue_Name,v.Capacity,v.Location
                ORDER BY Events_Hosted DESC
            """,
            "Cancelled registrations": """
                SELECT s.Name, s.Department, e.Event_Name, r.Reg_Date, r.Status
                FROM REGISTRATION r JOIN STUDENT s ON s.Student_ID=r.Student_ID
                JOIN EVENT e ON e.Event_ID=r.Event_ID
                WHERE r.Status='Cancelled' ORDER BY r.Reg_Date DESC
            """,
            "Upcoming events": """
                SELECT e.Event_Name,e.Event_Date,e.Start_Time,v.Venue_Name,e.Status
                FROM EVENT e JOIN VENUE v ON v.Venue_ID=e.Venue_ID
                WHERE e.Event_Date >= CURDATE()
                  AND e.Status NOT IN ('Cancelled','Completed')
                ORDER BY e.Event_Date,e.Start_Time
            """
        }
        try:
            rows = self.db.fetch_all(report_sql[report])
            self.report_tree.delete(*self.report_tree.get_children())
            if not rows:
                self.report_tree["columns"] = ("Message",)
                self.report_tree.heading("Message", text="Message")
                self.report_tree.insert("", "end", values=("No records found",))
                return
            columns = list(rows[0].keys())
            self.report_tree["columns"] = columns
            for col in columns:
                self.report_tree.heading(col, text=col.replace("_", " "))
                self.report_tree.column(col, width=160, minwidth=100)
            for row in rows:
                self.report_tree.insert("", "end", values=tuple(row.values()))
        except Exception as exc:
            self.report_error(exc)

    # ---------------- DBMS lab demonstrations ----------------

    def build_dbms_lab(self, parent):
        proc = ttk.LabelFrame(parent, text="Explicit cursor / stored procedure", padding=10)
        proc.pack(fill="x", pady=8)
        ttk.Label(proc, text="Event ID").pack(side="left")
        self.roster_event_id = ttk.Entry(proc, width=12)
        self.roster_event_id.pack(side="left", padx=6)
        ttk.Button(proc, text="Run registration roster procedure",
                   command=self.show_event_roster).pack(side="left", padx=6)

        func = ttk.LabelFrame(parent, text="Stored function: available seats", padding=10)
        func.pack(fill="x", pady=8)
        ttk.Label(func, text="Event ID").pack(side="left")
        self.function_event_id = ttk.Entry(func, width=12)
        self.function_event_id.pack(side="left", padx=6)
        ttk.Button(func, text="Calculate available seats",
                   command=self.run_available_seats).pack(side="left", padx=6)

        audit = ttk.LabelFrame(parent, text="Trigger audit log", padding=10)
        audit.pack(fill="both", expand=True, pady=8)
        ttk.Button(audit, text="View registration audit",
                   command=self.show_audit).pack(anchor="w")
        self.audit_tree = self.make_tree(
            audit, ("Audit_ID","Registration_ID","Old_Status","New_Status","Changed_By","Changed_At"),
            height=8
        )

        txn = ttk.LabelFrame(parent, text="Transaction demonstration", padding=10)
        txn.pack(fill="x", pady=8)
        ttk.Label(
            txn,
            text="This demo inserts a temporary student inside a transaction, then rolls it back."
        ).pack(anchor="w")
        ttk.Button(txn, text="Demonstrate ROLLBACK",
                   command=self.demonstrate_rollback).pack(anchor="w", pady=5)

        algebra = ttk.LabelFrame(parent, text="Relational algebra examples", padding=10)
        algebra.pack(fill="x", pady=8)
        ttk.Label(
            algebra,
            text="Selection: σ Department='CSE'(STUDENT)\n"
                 "Projection: π Name,Email(STUDENT)\n"
                 "Join: STUDENT ⋈ REGISTRATION\n"
                 "Set difference: STUDENT − students who have registrations\n"
                 "The SQL equivalents are implemented in the SQL query collection / reports."
        ).pack(anchor="w")

    def run_available_seats(self):
        try:
            event_id = int(self.function_event_id.get())
            seats = self.db.available_seats(event_id)
            messagebox.showinfo("Available seats", f"Available seats: {seats}")
        except Exception as exc:
            self.report_error(exc)

    def show_audit(self):
        try:
            rows = self.db.fetch_all("""
                SELECT Audit_ID,Registration_ID,Old_Status,New_Status,Changed_By,Changed_At
                FROM REGISTRATION_AUDIT ORDER BY Changed_At DESC LIMIT 200
            """)
            self.fill_tree(self.audit_tree, rows,
                           ("Audit_ID","Registration_ID","Old_Status","New_Status","Changed_By","Changed_At"))
        except Exception as exc:
            self.report_error(exc)

    def demonstrate_rollback(self):
        cur = self.db.cursor()
        temporary_id = 999999
        try:
            self.db.connection.start_transaction()
            cur.execute(
                """INSERT INTO STUDENT
                   (Student_ID,Name,Email,Department,Academic_Year)
                   VALUES (%s,%s,%s,%s,%s)""",
                (temporary_id, "Rollback Demo", "rollback.demo@example.edu", "DBMS Lab", 1)
            )
            self.db.connection.rollback()
            messagebox.showinfo(
                "ROLLBACK demonstrated",
                "A temporary student row was inserted inside a transaction and then rolled back. "
                "The row was not saved."
            )
        except Exception as exc:
            self.db.connection.rollback()
            self.report_error(exc)
        finally:
            cur.close()


def main():
    root = tk.Tk()
    app = EventManagementApp(root)

    def close_app():
        try:
            app.db.close()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_app)
    root.mainloop()


if __name__ == "__main__":
    main()
