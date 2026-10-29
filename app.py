import streamlit as st
import requests
import datetime
import pandas as pd

# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"  # Adjust backend FastAPI base URL if needed

st.set_page_config(
    page_title="Smart City Traffic & Parking System",
    page_icon="🚗",
    layout="wide"
)

# Initialize Session State Variables
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "gmail" not in st.session_state:
    st.session_state.gmail = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Helper function to handle API calls smoothly
def api_request(method, endpoint, params=None, json=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, params=params, json=json)
        if response.status_code in [200, 201]:
            return response.json(), None
        elif response.status_code == 204:
            return {}, None
        else:
            try:
                err_detail = response.json().get("detail", response.text)
            except Exception:
                err_detail = response.text
            return None, f"Error {response.status_code}: {err_detail}"
    except Exception as e:
        return None, f"Connection Failed: {str(e)}"

# -----------------------------------------------------------------------------
# Authentication & State Management Page
# -----------------------------------------------------------------------------
def render_auth_page():
    st.title("🚗 Smart City Traffic & Parking Management System")
    
    tab_login, tab_signup, tab_admin = st.tabs(["User Login", "User Sign Up", "Admin Portal Login"])

    with tab_login:
        st.subheader("User Login")
        with st.form("login_form"):
            login_gmail = st.text_input("Gmail Address")
            login_password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if not login_gmail or not login_password:
                    st.error("Please enter both email and password.")
                else:
                    data, err = api_request("POST", "/api/identity/login", json={"gmail": login_gmail, "password": login_password})
                    if err:
                        st.error(err)
                    else:
                        st.session_state.logged_in = True
                        st.session_state.gmail = login_gmail
                        st.session_state.is_admin = False
                        
                        # Capture and format the user's full name
                        user_data = data.get("user", {})
                        full_name = f"{user_data.get('f_name', '')} {user_data.get('l_name', '')}".strip()
                        st.session_state.user_name = full_name if full_name else login_gmail
                        
                        st.success("Successfully logged in!")
                        st.rerun()

    # 2. User Sign-up Flow
    with tab_signup:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            s_gmail = st.text_input("Gmail Address*")
            s_fname = st.text_input("First Name*")
            s_mname = st.text_input("Middle Name (Optional)")
            s_lname = st.text_input("Last Name*")
            s_dl_no = st.text_input("Driver's License Number (DL No)*")
            s_password = st.text_input("Password*", type="password")
            s_phones_str = st.text_input("Phone Numbers (comma-separated, min 10 digits each)*")
            
            signup_submit = st.form_submit_button("Register Account")
            
            if signup_submit:
                phones = [p.strip() for p in s_phones_str.split(",") if p.strip()]
                if not all([s_gmail, s_fname, s_lname, s_dl_no, s_password]) or not phones:
                    st.error("Please fill in all mandatory fields.")
                else:
                    payload = {
                        "gmail": s_gmail,
                        "f_name": s_fname,
                        "m_name": s_mname if s_mname else None,
                        "l_name": s_lname,
                        "dl_no": s_dl_no,
                        "password": s_password,
                        "phones": phones
                    }
                    data, err = api_request("POST", "/api/identity/users", json=payload)
                    if err:
                        st.error(err)
                    else:
                        st.success("Registration successful! Please log in from the login tab.")

    # 3. Admin Login Separation
    with tab_admin:
        st.subheader("Admin Portal Access")
        with st.form("admin_login_form"):
            admin_email = st.text_input("Admin Email", value="admin@smartcity.com")
            admin_pass = st.text_input("Admin Password", type="password")
            admin_submit = st.form_submit_button("Login as Admin")
            
            if admin_submit:
                # Hardcoded admin credentials check
                if admin_email == "admin@smartcity.com" and admin_pass == "admin":
                    st.session_state.logged_in = True
                    st.session_state.gmail = admin_email
                    st.session_state.user_name = "System Administrator"
                    st.session_state.is_admin = True
                    st.success("Admin Session Initialized!")
                    st.rerun()
                else:
                    st.error("Invalid admin email or password.")

# -----------------------------------------------------------------------------
# User Dashboard
# -----------------------------------------------------------------------------
def render_user_dashboard():
    st.sidebar.title("User Dashboard")
    st.sidebar.info(f"Welcome, **{st.session_state.user_name}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.gmail = ""
        st.session_state.user_name = ""
        st.session_state.is_admin = False
        st.rerun()

    menu = st.sidebar.radio("Navigation", [
        "Account Settings",
        "Vehicle Fleet",
        "Parking & Reservations",
        "Tickets & Appeals"
    ])

    user_gmail = st.session_state.gmail

    # --- 1. Account Management ---
    if menu == "Account Settings":
        st.header("👤 Account Settings")
        
        st.subheader("Update Phone Number")
        with st.form("update_phone_form"):
            old_phone = st.text_input("Current Phone Number to Replace")
            new_phone = st.text_input("New Phone Number")
            btn_update_phone = st.form_submit_button("Update Phone")
            
            if btn_update_phone:
                if old_phone and new_phone:
                    endpoint = f"/api/identity/users/{user_gmail}/phones/{old_phone}"
                    res, err = api_request("PATCH", endpoint, json={"new_phone": new_phone})
                    if err:
                        st.error(err)
                    else:
                        st.success("Phone number updated successfully!")

        st.divider()
        st.subheader("Delete Account")
        st.warning("⚠️ Warning: Deleting your account will cascade and remove associated vehicles and details.")
        if st.button("Delete My Account Permanently"):
            res, err = api_request("DELETE", f"/api/identity/users/{user_gmail}")
            if err:
                st.error(err)
            else:
                st.success("Account deleted.")
                st.session_state.logged_in = False
                st.rerun()

    # --- 2. Vehicle Management ---
    elif menu == "Vehicle Fleet":
        st.header("🚘 Vehicle Fleet Management")
        
        # Display Fleet
        st.subheader("Your Registered Fleet")
        fleet, err = api_request("GET", f"/api/identity/users/{user_gmail}/vehicles")
        if err:
            st.error(err)
        elif fleet:
            st.dataframe(fleet, use_container_width=True)
        else:
            st.info("No vehicles registered under this account.")

        st.divider()
        # Register Vehicle
        st.subheader("Register New Vehicle")
        with st.form("register_vehicle_form"):
            plate_no = st.text_input("Plate Number")
            make = st.text_input("Make (e.g., Toyota)")
            model = st.text_input("Model (e.g., Corolla)")
            colour = st.text_input("Color")
            dl_no = st.text_input("Driver License Number (Optional, maps ownership)")
            btn_reg = st.form_submit_button("Register Vehicle")
            
            if btn_reg:
                payload = {
                    "plate_no": plate_no,
                    "make": make,
                    "model": model,
                    "colour": colour,
                    "dl_no": dl_no if dl_no else None
                }
                res, err = api_request("POST", "/api/identity/vehicles", json=payload)
                if err:
                    st.error(err)
                else:
                    st.success("Vehicle registered successfully!")
                    st.rerun()

        st.divider()
        # Delete Vehicle
        st.subheader("Remove a Vehicle")
        with st.form("delete_vehicle_form"):
            del_plate = st.text_input("Plate Number to Remove")
            btn_del_v = st.form_submit_button("Delete Vehicle")
            if btn_del_v:
                res, err = api_request("DELETE", f"/api/identity/vehicles/{del_plate}", params={"gmail": user_gmail})
                if err:
                    st.error(err)
                else:
                    st.success(f"Vehicle {del_plate} removed.")
                    st.rerun()

    # --- 3. Reservations ---
    elif menu == "Parking & Reservations":
        st.header("🅿️ Parking & Reservations")

        # Total Spend Metric
        spend_data, _ = api_request("GET", f"/api/booking/users/{user_gmail}/spent")
        if spend_data:
            total_spent = spend_data.get("total_spent", 0) if isinstance(spend_data, dict) else spend_data
            st.metric("Total Spending on Parking", f"${total_spent}")

        st.subheader("Available Parking Zones (Sorted by Rate)")
        zones, err = api_request("GET", "/api/parking/zones/rates/sorted")
        if zones:
            st.dataframe(zones, use_container_width=True)

        st.divider()
        st.subheader("Create a Reservation")
        with st.form("create_reservation_form"):
            res_plate = st.text_input("Plate Number")
            res_zone = st.number_input("Zone ID", min_value=1, step=1)
            res_slot = st.number_input("Slot ID", min_value=1, step=1)
            start_date = st.date_input("Start Date", datetime.date.today())
            start_time = st.time_input("Start Time", datetime.time(9, 0))
            end_date = st.date_input("End Date", datetime.date.today())
            end_time = st.time_input("End Time", datetime.time(10, 0))
            
            btn_res = st.form_submit_button("Book Slot")
            
            if btn_res:
                start_dt = datetime.datetime.combine(start_date, start_time).isoformat()
                end_dt = datetime.datetime.combine(end_date, end_time).isoformat()
                payload = {
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "plate_no": res_plate,
                    "zone_id": res_zone,
                    "slot_id": res_slot
                }
                res, err = api_request("POST", "/api/booking/reservations", json=payload)
                if err:
                    st.error(err)
                else:
                    st.success("Reservation created!")
                    st.rerun()

        st.divider()
        st.subheader("Your Reservations")
        user_res, _ = api_request("GET", f"/api/booking/users/{user_gmail}/reservations")
        if user_res:
            st.dataframe(user_res, use_container_width=True)
            
            st.subheader("Manage Active Reservation")
            c1, c2 = st.columns(2)
            with c1:
                with st.form("extend_res_form"):
                    ext_id = st.number_input("Reservation ID to Extend", min_value=1, step=1)
                    ext_date = st.date_input("New End Date", datetime.date.today())
                    ext_time = st.time_input("New End Time", datetime.time(12, 0))
                    btn_ext = st.form_submit_button("Extend Reservation")
                    if btn_ext:
                        new_end = datetime.datetime.combine(ext_date, ext_time).isoformat()
                        res, err = api_request("PATCH", f"/api/booking/reservations/{ext_id}/extend", params={"new_end_time": new_end})
                        if err:
                            st.error(err)
                        else:
                            st.success("Reservation extended!")
                            st.rerun()

            with c2:
                with st.form("cancel_res_form"):
                    cancel_id = st.number_input("Reservation ID to Cancel", min_value=1, step=1)
                    btn_cancel = st.form_submit_button("Cancel Reservation")
                    if btn_cancel:
                        res, err = api_request("DELETE", f"/api/booking/reservations/{cancel_id}")
                        if err:
                            st.error(err)
                        else:
                            st.success("Reservation cancelled.")
                            st.rerun()

    # --- 4. Ticketing & Appeals ---
    elif menu == "Tickets & Appeals":
        st.header("🧾 Ticketing & Dispute Resolution")
        
        # Pending Fines Total
        fines, _ = api_request("GET", f"/api/ticketing/users/{user_gmail}/fines/pending")
        total_fines = fines.get("total_pending_fine", 0) if isinstance(fines, dict) else (fines or 0)
        st.metric("Total Outstanding Fines", f"${total_fines}")

        st.subheader("Pending Tickets")
        tickets, err = api_request("GET", f"/api/ticketing/users/{user_gmail}/tickets/pending")
        if tickets:
            st.dataframe(tickets, use_container_width=True)
            
            st.subheader("Pay Ticket")
            with st.form("pay_ticket_form"):
                pay_id = st.number_input("Ticket ID to Pay", min_value=1, step=1)
                btn_pay = st.form_submit_button("Pay Ticket Now")
                if btn_pay:
                    res, err = api_request("PATCH", f"/api/ticketing/tickets/{pay_id}/pay")
                    if err:
                        st.error(err)
                    else:
                        st.success("Ticket paid successfully!")
                        st.rerun()
        else:
            st.info("No pending tickets.")

        st.divider()
        st.subheader("File an Appeal")
        with st.form("appeal_form"):
            t_id = st.number_input("Ticket ID to Dispute", min_value=1, step=1)
            reason = st.text_area("Reason for Appeal")
            appeal_dt = st.date_input("Date of Appeal", datetime.date.today()).isoformat()
            btn_appeal = st.form_submit_button("Submit Appeal")
            
            if btn_appeal:
                payload = {
                    "ticket_id": t_id,
                    "reason_text": reason,
                    "appeal_date": appeal_dt
                }
                res, err = api_request("POST", "/api/ticketing/appeals", json=payload)
                if err:
                    st.error(err)
                else:
                    st.success("Appeal submitted successfully.")
                    st.rerun()

        st.divider()
        st.subheader("Your Appeal History")
        appeals, _ = api_request("GET", f"/api/ticketing/users/{user_gmail}/appeals")
        if appeals:
            st.dataframe(appeals, use_container_width=True)

# -----------------------------------------------------------------------------
# Admin Dashboard
# -----------------------------------------------------------------------------
def render_admin_dashboard():
    st.sidebar.title("Admin Operations Panel")
    st.sidebar.warning(f"Logged in as ADMIN: **{st.session_state.user_name}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.gmail = ""
        st.session_state.user_name = ""
        st.session_state.is_admin = False
        st.rerun()

    admin_menu = st.sidebar.radio("Admin Modules", [
        "System Overview",
        "Parking Infrastructure",
        "Vehicle & Booking Oversight",
        "Enforcement Operations",
        "Dispute Resolution"
    ])

    # --- Fetch Global Dropdown Data ---
    # Fetching these at the top of the render ensures dropdowns have data
    all_zones, _ = api_request("GET", "/api/parking/zones/rates/sorted")
    zone_options = {f"Zone {z['zone_id']} - {z['location_name']}": z['zone_id'] for z in (all_zones or [])}
    
    all_sensors, _ = api_request("GET", "/api/parking/sensors")
    sensor_options = [s['sensor_id'] for s in (all_sensors or [])]

    all_slots, _ = api_request("GET", "/api/parking/slots")
    slot_options = {f"Zone {s['zone_id']} / Slot {s['slot_id']}": {"z": s['zone_id'], "s": s['slot_id']} for s in (all_slots or [])}
    
    all_cameras, _ = api_request("GET", "/api/enforcement/cameras")
    cam_options = {f"Cam {c['camera_id']} - {c['intersection']}": c['camera_id'] for c in (all_cameras or [])}
    
    all_violations, _ = api_request("GET", "/api/enforcement/violations")
    viol_options = {f"ID {v['violation_id']} - Plate {v['plate_no']}": v['violation_id'] for v in (all_violations or [])}

    # --- 1. System Overview ---
    if admin_menu == "System Overview":
        st.header("📊 System Overview")
        cap, _ = api_request("GET", "/api/parking/capacity/total")
        if cap:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Capacity", cap.get("system_total_capacity", 0))
            col2.metric("Occupied Slots", cap.get("system_occupied_or_reserved", 0))
            col3.metric("Free Slots", cap.get("system_free_slots", 0))

        st.divider()
        st.subheader("Zone Revenue Lookup")
        if zone_options:
            z_sel = st.selectbox("Select Zone to fetch revenue", options=list(zone_options.keys()))
            if st.button("Fetch Revenue"):
                rev, err = api_request("GET", f"/api/booking/zones/{zone_options[z_sel]}/revenue")
                if err: st.error(err)
                else: st.info(f"Gross Revenue: ${rev.get('total_revenue', 0)}")

        st.divider()
        st.subheader("System Users")
        users, _ = api_request("GET", "/api/identity/users")
        if users: st.dataframe(users, use_container_width=True)

    # --- 2. Parking Infrastructure ---
    elif admin_menu == "Parking Infrastructure":
        st.header("🏗️ Parking Infrastructure Management")
        t1, t2, t3 = st.tabs(["Zones", "Slots", "Sensors"])
        
        with t1:
            st.subheader("Create Zone")
            with st.form("create_zone_form"):
                loc_name = st.text_input("Location Name")
                total_cap = st.number_input("Total Capacity", min_value=1, step=1)
                base_rate = st.number_input("Base Rate ($/hr)", min_value=0.0, step=0.5)
                if st.form_submit_button("Create Zone"):
                    res, err = api_request("POST", "/api/parking/zones", json={"location_name": loc_name, "total_cap": total_cap, "base_rate": base_rate})
                    if err: st.error(err)
                    else: 
                        st.success("Zone Created!")
                        st.rerun()

            st.divider()
            st.subheader("Delete Zone")
            if zone_options:
                with st.form("delete_zone_form"):
                    del_z_key = st.selectbox("Select Zone to Delete", options=list(zone_options.keys()))
                    if st.form_submit_button("Delete Zone"):
                        res, err = api_request("DELETE", f"/api/parking/zones/{zone_options[del_z_key]}")
                        if err: st.error(err)
                        else: 
                            st.success("Zone deleted.")
                            st.rerun()

            st.divider()
            st.subheader("Search Zone by Location")
            search_loc = st.text_input("Enter partial or full location name")
            if st.button("Search Location"):
                if search_loc:
                    s_zones, err = api_request("GET", f"/api/parking/zones/search/{search_loc}")
                    if err: st.error(err)
                    else: st.dataframe(s_zones, use_container_width=True)
                else:
                    st.warning("Please enter a location to search.")

            st.divider()
            st.subheader("All Parking Zones")
            if all_zones: st.dataframe(all_zones, use_container_width=True)

        with t2:
            st.subheader("View Slots in a Zone")
            if zone_options:
                view_z_key = st.selectbox("Select Zone to view its slots", options=list(zone_options.keys()), key="view_slots")
                slots_in_zone, err = api_request("GET", f"/api/parking/zones/{zone_options[view_z_key]}/slots")
                if slots_in_zone:
                    st.dataframe(slots_in_zone, use_container_width=True)
                else:
                    st.info("No slots found or zone is empty.")

            st.divider()
            st.subheader("Create Slot")
            if zone_options and sensor_options:
                with st.form("create_slot_form"):
                    c_z_key = st.selectbox("Zone", options=list(zone_options.keys()))
                    c_sens = st.selectbox("Assign Sensor", options=sensor_options)
                    s_status = st.selectbox("Status", ["FREE", "OCCUPIED", "UNDER MAINTENANCE", "RESERVED"])
                    if st.form_submit_button("Create Slot"):
                        res, err = api_request("POST", "/api/parking/slots", json={"zone_id": zone_options[c_z_key], "sensor_id": c_sens, "status": s_status})
                        if err: st.error(err)
                        else: 
                            st.success("Slot Created!")
                            st.rerun()
            else:
                st.warning("You must have at least one Zone and one Sensor created before adding slots.")

            st.divider()
            st.subheader("Update Slot Status")
            if slot_options:
                with st.form("update_slot_status_form"):
                    u_slot_key = st.selectbox("Select Slot to Update", options=list(slot_options.keys()))
                    u_stat = st.selectbox("New Status", ["FREE", "OCCUPIED", "UNDER MAINTENANCE", "RESERVED"])
                    if st.form_submit_button("Update Status"):
                        z_id = slot_options[u_slot_key]["z"]
                        s_id = slot_options[u_slot_key]["s"]
                        res, err = api_request("PATCH", f"/api/parking/slots/{z_id}/{s_id}/status", json={"status": u_stat})
                        if err: st.error(err)
                        else: 
                            st.success("Slot updated!")
                            st.rerun()

            st.divider()
            st.subheader("Delete Slot")
            if slot_options:
                with st.form("delete_slot_form"):
                    d_slot_key = st.selectbox("Select Slot to Delete", options=list(slot_options.keys()), key="del_slot")
                    if st.form_submit_button("Delete Slot"):
                        z_id = slot_options[d_slot_key]["z"]
                        s_id = slot_options[d_slot_key]["s"]
                        res, err = api_request("DELETE", f"/api/parking/slots/{z_id}/{s_id}")
                        if err: st.error(err)
                        else: 
                            st.success("Slot deleted!")
                            st.rerun()

        with t3:
            st.subheader("Hardware Sensors")
            if all_sensors: st.dataframe(all_sensors, use_container_width=True)
            
            st.divider()
            st.subheader("Add Sensor")
            with st.form("add_sensor_form"):
                sens_id = st.text_input("Sensor ID (e.g., SENS-001)")
                mfr = st.text_input("Manufacturer")
                dom = st.date_input("Date of Manufacture").isoformat()
                model = st.text_input("Model")
                if st.form_submit_button("Add Sensor"):
                    res, err = api_request("POST", "/api/parking/sensors", json={"sensor_id": sens_id, "manufacture": mfr, "date_of_manufacture": dom, "model": model})
                    if err: st.error(err)
                    else: 
                        st.success("Sensor added!")
                        st.rerun()

            st.divider()
            st.subheader("Delete Sensor")
            if sensor_options:
                with st.form("delete_sensor_form"):
                    del_sens_id = st.selectbox("Select Sensor to Delete", options=sensor_options)
                    if st.form_submit_button("Delete Sensor"):
                        res, err = api_request("DELETE", f"/api/parking/sensors/{del_sens_id}")
                        if err: st.error(err)
                        else: 
                            st.success("Sensor deleted!")
                            st.rerun()

    # --- 3. Vehicle & Booking Oversight ---
    elif admin_menu == "Vehicle & Booking Oversight":
        st.header("🚘 Vehicle & Booking Oversight")
        
        st.subheader("Filter Vehicles by Registration Status")
        status_filter = st.selectbox("Select Status Filter", ["ACTIVE", "SUSPENDED", "UNCLAIMED", "EXPIRED", "CLAIMED"])
        vehicles_filtered, _ = api_request("GET", f"/api/identity/vehicles/status/{status_filter}")
        if vehicles_filtered:
            st.dataframe(vehicles_filtered, use_container_width=True)
        else:
            st.info(f"No vehicles found with status {status_filter}.")

        st.divider()
        st.subheader("System Reservations")
        if st.button("Fetch Active Reservations"):
            active_res, _ = api_request("GET", "/api/booking/reservations/active")
            st.dataframe(active_res, use_container_width=True)
            
        all_res, _ = api_request("GET", "/api/booking/reservations")
        if all_res:
            st.dataframe(all_res, use_container_width=True)

    # --- 4. Enforcement Operations ---
    elif admin_menu == "Enforcement Operations":
        st.header("📹 Enforcement & Traffic Operations")
        t_cam, t_viol, t_tix = st.tabs(["Cameras", "Violations", "Tickets"])
        
        with t_cam:
            st.subheader("All Cameras")
            if all_cameras: st.dataframe(all_cameras, use_container_width=True)

            st.divider()
            st.subheader("Create Camera")
            with st.form("add_cam_form"):
                intersection = st.text_input("Intersection")
                ip = st.text_input("IP Address")
                cam_status = st.selectbox("Operational Status", ["ACTIVE", "INACTIVE", "MAINTENANCE"])
                if st.form_submit_button("Add Camera"):
                    res, err = api_request("POST", "/api/enforcement/cameras", json={"intersection": intersection, "ip_address": ip, "operational_status": cam_status})
                    if err: st.error(err)
                    else: 
                        st.success("Camera registered!")
                        st.rerun()

        with t_viol:
            st.subheader("All Violations")
            if all_violations: st.dataframe(all_violations, use_container_width=True)

            st.divider()
            st.subheader("Log Traffic Violation")
            if cam_options:
                with st.form("log_viol_form"):
                    rules = st.text_input("Rules Broken")
                    v_time = st.date_input("Violation Date").isoformat()
                    v_plate = st.text_input("Plate Number")
                    v_cam_key = st.selectbox("Camera ID", options=list(cam_options.keys()))
                    img = st.text_input("Image Link (Optional)")
                    if st.form_submit_button("Log Violation"):
                        res, err = api_request("POST", "/api/enforcement/violations", json={"rules_broken": rules, "violation_time": v_time, "plate_no": v_plate, "camera_id": cam_options[v_cam_key], "img_link": img if img else None})
                        if err: st.error(err)
                        else: 
                            st.success("Violation logged!")
                            st.rerun()
            else:
                st.warning("Register a camera before logging violations.")

        with t_tix:
            st.subheader("All Issued Tickets")
            all_tickets, _ = api_request("GET", "/api/ticketing/tickets")
            if all_tickets: st.dataframe(all_tickets, use_container_width=True)

            st.divider()
            st.subheader("Issue Ticket")
            if viol_options:
                with st.form("issue_ticket_form"):
                    amt = st.number_input("Fine Amount ($)", min_value=0.0, step=10.0)
                    iss_date = st.date_input("Issue Date", datetime.date.today()).isoformat()
                    due_date = st.date_input("Due Date", datetime.date.today() + datetime.timedelta(days=30)).isoformat()
                    t_viol_key = st.selectbox("Violation Record", options=list(viol_options.keys()))
                    if st.form_submit_button("Issue Ticket"):
                        res, err = api_request("POST", "/api/ticketing/tickets", json={"fine_amt": amt, "issue_date": iss_date, "due_date": due_date, "violation_id": viol_options[t_viol_key]})
                        if err: st.error(err)
                        else: 
                            st.success("Ticket issued successfully!")
                            st.rerun()
            else:
                st.warning("Log a violation before issuing tickets.")

    # --- 5. Dispute Resolution ---
    elif admin_menu == "Dispute Resolution":
        st.header("⚖️ Dispute Resolution & Appeals")

        st.subheader("Pending Appeals")
        p_appeals, err = api_request("GET", "/api/ticketing/appeals/pending")
        if p_appeals:
            st.dataframe(p_appeals, use_container_width=True)
            
            appeal_options = {f"Appeal {a['appeal_id']} (Ticket {a['ticket_id']})": a['appeal_id'] for a in p_appeals}

            st.divider()
            st.subheader("Resolve Appeal")
            with st.form("resolve_appeal_form"):
                app_key = st.selectbox("Select Pending Appeal", options=list(appeal_options.keys()))
                decision = st.selectbox("Decision", ["ACCEPTED", "REJECTED", "PENDING"])
                if st.form_submit_button("Render Decision"):
                    res, err = api_request("PATCH", f"/api/ticketing/appeals/{appeal_options[app_key]}/decision", json={"appeal_decision": decision})
                    if err: st.error(err)
                    else: 
                        st.success(f"Appeal marked as {decision}.")
                        st.rerun()
        else:
            st.info("No pending appeals.")

# -----------------------------------------------------------------------------
# App Routing Execution
# -----------------------------------------------------------------------------
def main():
    if not st.session_state.logged_in:
        render_auth_page()
    elif st.session_state.is_admin:
        render_admin_dashboard()
    else:
        render_user_dashboard()

if __name__ == "__main__":
    main()