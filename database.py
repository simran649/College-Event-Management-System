"""
database.py
Database layer for College Event Management System.
Requires: pip install mysql-connector-python
"""

import hashlib
import mysql.connector
from mysql.connector import Error


DB_NAME = "college_event_management"

# Update these settings for your local MySQL installation.
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "emilly",
    "port": 3306,
}


def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        self.connection = mysql.connector.connect(**MYSQL_CONFIG)
        self.connection.autocommit = False
        return self.connection

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def cursor(self, dictionary=False):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        return self.connection.cursor(dictionary=dictionary)

    def initialize(self):
        """Create database, schema, sample data and MySQL stored programs."""
        server = mysql.connector.connect(**MYSQL_CONFIG)
        cur = server.cursor()
        try:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        finally:
            cur.close()
            server.close()

        self.connect()
        cur = self.cursor()
        try:
            cur.execute(f"USE {DB_NAME}")
            statements = [
                """
                CREATE TABLE IF NOT EXISTS ADMIN (
                    Admin_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Username VARCHAR(40) NOT NULL UNIQUE,
                    Password_Hash CHAR(64) NOT NULL,
                    Full_Name VARCHAR(80) NOT NULL,
                    Role ENUM('Admin','Organizer','Viewer') NOT NULL DEFAULT 'Admin',
                    Is_Active BOOLEAN NOT NULL DEFAULT TRUE,
                    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS STUDENT (
                    Student_ID INT PRIMARY KEY,
                    Name VARCHAR(80) NOT NULL,
                    Email VARCHAR(100) NOT NULL UNIQUE,
                    Phone VARCHAR(20),
                    Department VARCHAR(60) NOT NULL,
                    Academic_Year INT NOT NULL,
                    Is_Active BOOLEAN NOT NULL DEFAULT TRUE,
                    CHECK (Academic_Year BETWEEN 1 AND 4)
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS ORGANIZER (
                    Organizer_ID INT PRIMARY KEY,
                    Organizer_Name VARCHAR(100) NOT NULL,
                    Contact VARCHAR(20),
                    Email VARCHAR(100)
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS VENUE (
                    Venue_ID INT PRIMARY KEY,
                    Venue_Name VARCHAR(100) NOT NULL,
                    Location VARCHAR(150),
                    Capacity INT NOT NULL,
                    Is_Active BOOLEAN NOT NULL DEFAULT TRUE,
                    CHECK (Capacity > 0)
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS EVENT (
                    Event_ID INT PRIMARY KEY,
                    Event_Name VARCHAR(120) NOT NULL,
                    Event_Type VARCHAR(60) NOT NULL,
                    Description TEXT,
                    Event_Date DATE NOT NULL,
                    Start_Time TIME NOT NULL,
                    End_Time TIME NOT NULL,
                    Registration_Deadline DATE NOT NULL,
                    Max_Participants INT NOT NULL,
                    Status ENUM('Draft','Open','Closed','Cancelled','Completed')
                        NOT NULL DEFAULT 'Draft',
                    Organizer_ID INT NOT NULL,
                    Venue_ID INT NOT NULL,
                    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (Organizer_ID) REFERENCES ORGANIZER(Organizer_ID),
                    FOREIGN KEY (Venue_ID) REFERENCES VENUE(Venue_ID),
                    CHECK (End_Time > Start_Time),
                    CHECK (Max_Participants > 0)
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS REGISTRATION (
                    Registration_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Student_ID INT NOT NULL,
                    Event_ID INT NOT NULL,
                    Reg_Date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    Status ENUM('Registered','Cancelled','Attended','Absent')
                        NOT NULL DEFAULT 'Registered',
                    UNIQUE KEY uq_student_event (Student_ID, Event_ID),
                    FOREIGN KEY (Student_ID) REFERENCES STUDENT(Student_ID),
                    FOREIGN KEY (Event_ID) REFERENCES EVENT(Event_ID)
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS REGISTRATION_AUDIT (
                    Audit_ID BIGINT AUTO_INCREMENT PRIMARY KEY,
                    Registration_ID INT NOT NULL,
                    Old_Status VARCHAR(20),
                    New_Status VARCHAR(20),
                    Changed_By VARCHAR(80) DEFAULT 'application',
                    Changed_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """,
            ]
            for statement in statements:
                cur.execute(statement)

            self.connection.commit()

            # Upgrade tables created by the earlier version of this project.
            # CREATE TABLE IF NOT EXISTS does not add columns to existing tables.
            self._migrate_existing_schema(cur)
            self.connection.commit()

            self._create_trigger(cur)
            self._create_procedure(cur)
            self._create_function(cur)
            self.connection.commit()
            self._seed_data(cur)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def _migrate_existing_schema(self, cur):
        """Add columns required by the upgraded application to older databases."""

        def columns(table_name):
            cur.execute(f"SHOW COLUMNS FROM {table_name}")
            return {row[0] for row in cur.fetchall()}

        # STUDENT: the first version used Year instead of Academic_Year.
        student_cols = columns("STUDENT")
        if "Academic_Year" not in student_cols:
            cur.execute(
                "ALTER TABLE STUDENT ADD COLUMN Academic_Year INT NOT NULL DEFAULT 1"
            )
            if "Year" in student_cols:
                cur.execute(
                    "UPDATE STUDENT SET Academic_Year = Year WHERE Year IS NOT NULL"
                )
        student_cols = columns("STUDENT")
        if "Is_Active" not in student_cols:
            cur.execute(
                "ALTER TABLE STUDENT ADD COLUMN Is_Active BOOLEAN NOT NULL DEFAULT TRUE"
            )

        # VENUE: add location and active/inactive flag.
        venue_cols = columns("VENUE")
        if "Location" not in venue_cols:
            cur.execute("ALTER TABLE VENUE ADD COLUMN Location VARCHAR(150) NULL")
        venue_cols = columns("VENUE")
        if "Is_Active" not in venue_cols:
            cur.execute(
                "ALTER TABLE VENUE ADD COLUMN Is_Active BOOLEAN NOT NULL DEFAULT TRUE"
            )
        # ORGANIZER: add Email column if missing.
        organizer_cols = columns("ORGANIZER")
        if "Email" not in organizer_cols:
            cur.execute("ALTER TABLE ORGANIZER ADD COLUMN Email VARCHAR(100) NULL")
        # EVENT: the earlier version used Event_Time and did not have status,
        # end time, registration deadline or participant limit.
        event_cols = columns("EVENT")
        additions = {
            "Description": "ALTER TABLE EVENT ADD COLUMN Description TEXT NULL",
            "Start_Time": "ALTER TABLE EVENT ADD COLUMN Start_Time TIME NULL",
            "End_Time": "ALTER TABLE EVENT ADD COLUMN End_Time TIME NULL",
            "Registration_Deadline": (
                "ALTER TABLE EVENT ADD COLUMN Registration_Deadline DATE NULL"
            ),
            "Max_Participants": (
                "ALTER TABLE EVENT ADD COLUMN Max_Participants INT NULL"
            ),
            "Status": (
                "ALTER TABLE EVENT ADD COLUMN Status "
                "ENUM('Draft','Open','Closed','Cancelled','Completed') "
                "NOT NULL DEFAULT 'Open'"
            ),
        }
        for column_name, alter_sql in additions.items():
            if column_name not in event_cols:
                cur.execute(alter_sql)

        event_cols = columns("EVENT")
        if "Event_Time" in event_cols:
            cur.execute(
                """UPDATE EVENT
                   SET Start_Time = COALESCE(Start_Time, Event_Time, '09:00:00')"""
            )
        else:
            cur.execute(
                "UPDATE EVENT SET Start_Time = COALESCE(Start_Time, '09:00:00')"
            )

        cur.execute(
            """UPDATE EVENT
               SET End_Time = COALESCE(End_Time, ADDTIME(Start_Time, '01:00:00')),
                   Registration_Deadline = COALESCE(
                       Registration_Deadline, DATE_SUB(Event_Date, INTERVAL 1 DAY)
                   ),
                   Max_Participants = COALESCE(
                       Max_Participants,
                       (SELECT Capacity FROM VENUE WHERE VENUE.Venue_ID = EVENT.Venue_ID)
                   )"""
        )

        # The new application expects these columns to contain values.
        cur.execute(
            """UPDATE EVENT
               SET End_Time = '10:00:00' WHERE End_Time IS NULL"""
        )
        cur.execute(
            """UPDATE EVENT
               SET Registration_Deadline = Event_Date
               WHERE Registration_Deadline IS NULL"""
        )
        cur.execute(
            """UPDATE EVENT SET Max_Participants = 100
               WHERE Max_Participants IS NULL OR Max_Participants < 1"""
        )
        cur.execute(
            "ALTER TABLE EVENT MODIFY Start_Time TIME NOT NULL"
        )
        cur.execute(
            "ALTER TABLE EVENT MODIFY End_Time TIME NOT NULL"
        )
        cur.execute(
            "ALTER TABLE EVENT MODIFY Registration_Deadline DATE NOT NULL"
        )
        cur.execute(
            "ALTER TABLE EVENT MODIFY Max_Participants INT NOT NULL"
        )

        # REGISTRATION_AUDIT: older versions may not have Changed_By.
        audit_cols = columns("REGISTRATION_AUDIT")
        if "Changed_By" not in audit_cols:
            cur.execute(
                """ALTER TABLE REGISTRATION_AUDIT
                   ADD COLUMN Changed_By VARCHAR(80) DEFAULT 'application'"""
            )

    def _create_trigger(self, cur):
        cur.execute("DROP TRIGGER IF EXISTS trg_registration_status_audit")
        cur.execute("""
            CREATE TRIGGER trg_registration_status_audit
            AFTER UPDATE ON REGISTRATION
            FOR EACH ROW
            BEGIN
                IF OLD.Status <> NEW.Status THEN
                    INSERT INTO REGISTRATION_AUDIT
                        (Registration_ID, Old_Status, New_Status, Changed_By)
                    VALUES
                        (OLD.Registration_ID, OLD.Status, NEW.Status,
                         COALESCE(@app_user, 'application'));
                END IF;
            END
        """)

    def _create_procedure(self, cur):
        cur.execute("DROP PROCEDURE IF EXISTS sp_event_registration_roster")
        cur.execute("""
            CREATE PROCEDURE sp_event_registration_roster(IN p_event_id INT)
            BEGIN
                DECLARE done INT DEFAULT FALSE;
                DECLARE v_student_id INT;
                DECLARE v_student_name VARCHAR(80);
                DECLARE v_email VARCHAR(100);
                DECLARE registration_cursor CURSOR FOR
                    SELECT s.Student_ID, s.Name, s.Email
                    FROM STUDENT s
                    JOIN REGISTRATION r ON r.Student_ID = s.Student_ID
                    WHERE r.Event_ID = p_event_id
                      AND r.Status IN ('Registered','Attended','Absent')
                    ORDER BY s.Name;
                DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

                DROP TEMPORARY TABLE IF EXISTS roster_output;
                CREATE TEMPORARY TABLE roster_output (
                    Student_ID INT,
                    Student_Name VARCHAR(80),
                    Email VARCHAR(100)
                );

                OPEN registration_cursor;
                roster_loop: LOOP
                    FETCH registration_cursor
                    INTO v_student_id, v_student_name, v_email;
                    IF done THEN
                        LEAVE roster_loop;
                    END IF;
                    INSERT INTO roster_output
                    VALUES (v_student_id, v_student_name, v_email);
                END LOOP;
                CLOSE registration_cursor;

                SELECT * FROM roster_output;
            END
        """)

    def _create_function(self, cur):
        cur.execute("DROP FUNCTION IF EXISTS fn_available_seats")
        cur.execute("""
            CREATE FUNCTION fn_available_seats(p_event_id INT)
            RETURNS INT
            READS SQL DATA
            BEGIN
                DECLARE v_capacity INT DEFAULT 0;
                DECLARE v_registered INT DEFAULT 0;

                SELECT Max_Participants INTO v_capacity
                FROM EVENT WHERE Event_ID = p_event_id;

                SELECT COUNT(*) INTO v_registered
                FROM REGISTRATION
                WHERE Event_ID = p_event_id AND Status = 'Registered';

                RETURN v_capacity - v_registered;
            END
        """)

    def _seed_data(self, cur):
        cur.execute("SELECT COUNT(*) AS n FROM ADMIN")
        if cur.fetchone()[0] == 0:
            cur.execute(
                """INSERT INTO ADMIN
                   (Username, Password_Hash, Full_Name, Role)
                   VALUES (%s,%s,%s,%s)""",
                ("admin", password_hash("admin123"), "System Administrator", "Admin")
            )

        cur.execute("SELECT COUNT(*) FROM STUDENT")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """INSERT INTO STUDENT
                   (Student_ID,Name,Email,Phone,Department,Academic_Year)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                [
                    (101, "Aarav Sharma", "aarav@example.edu", "9876543210", "CSE", 2),
                    (102, "Simran Singh", "simran@example.edu", "9876543211", "CSE", 2),
                    (103, "Ishan Kumar", "ishan@example.edu", "9876543212", "ECE", 2),
                    (104, "Vaibhav Gupta", "vaibhav@example.edu", "9876543213", "CSE", 3),
                    (105, "Ananya Verma", "ananya@example.edu", "9876543214", "IT", 2),
                    (106, "Rohan Mehta", "rohan@example.edu", "9876543215", "ECE", 3),
                    (107, "Priya Sharma", "priya@example.edu", "9876543216", "IT", 1),
                    (108, "Kabir Singh", "kabir@example.edu", "9876543217", "CSE", 1),
                ]
            )

        cur.execute("SELECT COUNT(*) FROM ORGANIZER")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO ORGANIZER VALUES (%s,%s,%s,%s)",
                [
                    (201, "Innovation Hub", "9876500001", "innovation@example.edu"),
                    (202, "Technical Society", "9876500002", "tech@example.edu"),
                    (203, "Cultural Club", "9876500003", "culture@example.edu"),
                ]
            )

        cur.execute("SELECT COUNT(*) FROM VENUE")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """INSERT INTO VENUE
                   (Venue_ID,Venue_Name,Location,Capacity)
                   VALUES (%s,%s,%s,%s)""",
                [
                    (301, "Auditorium", "Main Campus", 500),
                    (302, "Seminar Hall", "Academic Block", 150),
                    (303, "Computer Lab", "Technology Block", 60),
                    (304, "Open Ground", "Sports Complex", 300),
                ]
            )

        cur.execute("SELECT COUNT(*) FROM EVENT")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """INSERT INTO EVENT
                   (Event_ID,Event_Name,Event_Type,Description,Event_Date,
                    Start_Time,End_Time,Registration_Deadline,Max_Participants,
                    Status,Organizer_ID,Venue_ID)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                [
                    (401, "Hackathon 2026", "Technical", "Inter-college coding hackathon",
                     "2026-12-05", "09:00", "18:00", "2026-12-01", 200, "Open", 201, 301),
                    (402, "Code Sprint", "Competition", "Competitive programming contest",
                     "2026-12-10", "10:00", "16:00", "2026-12-07", 50, "Open", 202, 303),
                    (403, "Dance Competition", "Cultural", "Inter-department dance event",
                     "2026-12-12", "15:00", "19:00", "2026-12-09", 250, "Open", 203, 304),
                    (404, "AI Workshop", "Workshop", "Introduction to applied AI",
                     "2026-12-15", "11:00", "14:00", "2026-12-12", 100, "Open", 201, 302),
                ]
            )

        cur.execute("SELECT COUNT(*) FROM REGISTRATION")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """INSERT INTO REGISTRATION
                   (Student_ID,Event_ID,Reg_Date,Status)
                   VALUES (%s,%s,%s,%s)""",
                [
                    (101, 401, "2026-11-20 10:00:00", "Registered"),
                    (102, 401, "2026-11-20 10:05:00", "Registered"),
                    (103, 401, "2026-11-21 11:00:00", "Registered"),
                    (104, 402, "2026-11-21 12:00:00", "Registered"),
                    (105, 402, "2026-11-22 09:00:00", "Registered"),
                    (106, 403, "2026-11-22 09:30:00", "Registered"),
                    (107, 403, "2026-11-23 10:00:00", "Registered"),
                    (108, 404, "2026-11-23 10:30:00", "Registered"),
                    (101, 404, "2026-11-24 08:30:00", "Registered"),
                ]
            )
        self.connection.commit()

    def login(self, username, password):
        cur = self.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT Admin_ID, Username, Full_Name, Role
                   FROM ADMIN
                   WHERE Username=%s AND Password_Hash=%s AND Is_Active=TRUE""",
                (username, password_hash(password))
            )
            return cur.fetchone()
        finally:
            cur.close()

    def fetch_all(self, query, params=()):
        cur = self.cursor(dictionary=True)
        try:
            cur.execute(query, params)
            return cur.fetchall()
        finally:
            cur.close()

    def execute(self, query, params=()):
        cur = self.cursor()
        try:
            cur.execute(query, params)
            self.connection.commit()
            return cur.lastrowid, cur.rowcount
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def register_student(self, student_id, event_id):
        """Transaction-safe registration with duplicate, date, status and capacity checks."""
        cur = self.cursor(dictionary=True)
        try:
            self.connection.start_transaction()
            cur.execute(
                "SELECT * FROM EVENT WHERE Event_ID=%s FOR UPDATE",
                (event_id,)
            )
            event = cur.fetchone()
            if not event:
                raise ValueError("Event does not exist.")
            if event["Status"] != "Open":
                raise ValueError("Registration is not open for this event.")
            cur.execute(
                "SELECT Student_ID FROM STUDENT WHERE Student_ID=%s AND Is_Active=TRUE",
                (student_id,)
            )
            if not cur.fetchone():
                raise ValueError("Active student was not found.")
            cur.execute(
                """SELECT COUNT(*) AS n FROM REGISTRATION
                   WHERE Event_ID=%s AND Status='Registered'""",
                (event_id,)
            )
            registered = cur.fetchone()["n"]
            if registered >= event["Max_Participants"]:
                raise ValueError("This event has reached its participant limit.")
            cur.execute(
                """SELECT Registration_ID FROM REGISTRATION
                   WHERE Student_ID=%s AND Event_ID=%s""",
                (student_id, event_id)
            )
            existing = cur.fetchone()
            if existing:
                raise ValueError("This student already has a registration record for this event.")
            cur.execute(
                """INSERT INTO REGISTRATION (Student_ID,Event_ID,Status)
                   VALUES (%s,%s,'Registered')""",
                (student_id, event_id)
            )
            self.connection.commit()
            return cur.lastrowid
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def change_registration_status(self, registration_id, new_status, username):
        cur = self.cursor()
        try:
            cur.execute("SET @app_user = %s", (username,))
            cur.execute(
                "UPDATE REGISTRATION SET Status=%s WHERE Registration_ID=%s",
                (new_status, registration_id)
            )
            if cur.rowcount == 0:
                raise ValueError("Registration not found or status unchanged.")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def check_venue_conflict(self, venue_id, event_date, start_time, end_time,
                             exclude_event_id=None):
        query = """
            SELECT Event_ID, Event_Name, Start_Time, End_Time
            FROM EVENT
            WHERE Venue_ID=%s AND Event_Date=%s
              AND Status <> 'Cancelled'
              AND Start_Time < %s AND End_Time > %s
        """
        params = [venue_id, event_date, end_time, start_time]
        if exclude_event_id is not None:
            query += " AND Event_ID <> %s"
            params.append(exclude_event_id)
        return self.fetch_all(query, tuple(params))

    def create_event(self, values):
        conflicts = self.check_venue_conflict(
            values["venue_id"], values["event_date"],
            values["start_time"], values["end_time"]
        )
        if conflicts:
            raise ValueError(
                "Venue is already booked during this time by: "
                + ", ".join(row["Event_Name"] for row in conflicts)
            )
        query = """
            INSERT INTO EVENT
            (Event_ID,Event_Name,Event_Type,Description,Event_Date,
             Start_Time,End_Time,Registration_Deadline,Max_Participants,
             Status,Organizer_ID,Venue_ID)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        params = (
            values["event_id"], values["event_name"], values["event_type"],
            values["description"], values["event_date"], values["start_time"],
            values["end_time"], values["deadline"], values["capacity"],
            values["status"], values["organizer_id"], values["venue_id"]
        )
        self.execute(query, params)

    def update_event(self, event_id, values):
        conflicts = self.check_venue_conflict(
            values["venue_id"], values["event_date"],
            values["start_time"], values["end_time"], event_id
        )
        if conflicts:
            raise ValueError(
                "Venue is already booked during this time by: "
                + ", ".join(row["Event_Name"] for row in conflicts)
            )
        query = """
            UPDATE EVENT SET Event_Name=%s, Event_Type=%s, Description=%s,
                Event_Date=%s, Start_Time=%s, End_Time=%s,
                Registration_Deadline=%s, Max_Participants=%s,
                Status=%s, Organizer_ID=%s, Venue_ID=%s
            WHERE Event_ID=%s
        """
        params = (
            values["event_name"], values["event_type"], values["description"],
            values["event_date"], values["start_time"], values["end_time"],
            values["deadline"], values["capacity"], values["status"],
            values["organizer_id"], values["venue_id"], event_id
        )
        self.execute(query, params)

    def event_roster(self, event_id):
        cur = self.cursor()
        try:
            cur.callproc("sp_event_registration_roster", (event_id,))
            result = []
            for stored_result in cur.stored_results():
                result.extend(stored_result.fetchall())
            return result
        finally:
            cur.close()

    def available_seats(self, event_id):
        rows = self.fetch_all(
            "SELECT fn_available_seats(%s) AS Available_Seats", (event_id,)
        )
        return rows[0]["Available_Seats"] if rows else None
