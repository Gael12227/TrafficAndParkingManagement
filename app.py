import streamlit as st
import requests
import datetime

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
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Helper function to handle API calls smoothly
def api_request(method, endpoint, params=None, json=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, params=params, json=json)
        if response.status_code in [200, 201]:
            return response.json(), None
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

    # 1. User Login Flow
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
                # Assuming Admin authenticates using dedicated route or administrative credentials
                data, err = api_request("POST", "/api/identity/login", json={"gmail": admin_email, "password": admin_pass})
                if err:
                    st.error(err)
                else:
                    st.session_state.logged_in = True
                    st.session_state.gmail = admin_email
                    st.session_state.is_admin = True
                    st.success("Admin Session Initialized!")
                    st.rerun()

# -----------------------------------------------------------------------------
# User Dashboard
# -----------------------------------------------------------------------------
def render_user_dashboard():
    st.sidebar.title("User Dashboard")
    st.sidebar.info(f"Logged in as: **{st.session_state.gmail}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.gmail = ""
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
        total_fines = fines.get("total_pending_fines", 0) if isinstance(fines, dict) else (fines or 0)
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
    st.sidebar.warning(f"Logged in as ADMIN: **{st.session_state.gmail}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.gmail = ""
        st.session_state.is_admin = False
        st.rerun()

    admin_menu = st.sidebar.radio("Admin Modules", [
        "System Overview",
        "Parking Infrastructure",
        "Vehicle & Booking Oversight",
        "Enforcement Operations",
        "Dispute Resolution"
    ])

    # --- 1. System Overview ---
    if admin_menu == "System Overview":
        st.header("📊 System Overview")
        
        # System Capacity Metrics
        cap, _ = api_request("GET", "/api/parking/capacity/total")
        if cap:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Capacity", cap.get("total", 0))
            col2.metric("Occupied Slots", cap.get("occupied", 0))
            col3.metric("Free Slots", cap.get("free", 0))

        st.divider()
        st.subheader("Zone Revenue Lookup")
        z_id = st.number_input("Enter Zone ID to fetch revenue", min_value=1, step=1)
        if st.button("Fetch Revenue"):
            rev, err = api_request("GET", f"/api/booking/zones/{z_id}/revenue")
            if err:
                st.error(err)
            else:
                st.info(f"Gross Revenue for Zone {z_id}: ${rev.get('revenue', rev)}")

        st.divider()
        st.subheader("System Users")
        users, _ = api_request("GET", "/api/identity/users")
        if users:
            st.dataframe(users, use_container_width=True)

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
                    res, err = api_request("POST", "/api/parking/zones", json={
                        "location_name": loc_name,
                        "total_cap": total_cap,
                        "base_rate": base_rate
                    })
                    if err: st.error(err)
                    else: st.success("Zone Created!")
            
            st.subheader("Delete Zone")
            del_z = st.number_input("Zone ID to Delete", min_value=1, step=1)
            if st.button("Delete Zone"):
                res, err = api_request("DELETE", f"/api/parking/zones/{del_z}")
                if err: st.error(err)
                else: st.success("Zone deleted.")

        with t2:
            st.subheader("Create Slot")
            with st.form("create_slot_form"):
                sz_id = st.number_input("Zone ID", min_value=1, step=1)
                ss_id = st.text_input("Sensor ID")
                s_status = st.selectbox("Status", ["FREE", "OCCUPIED", "UNDER MAINTENANCE", "RESERVED"])
                if st.form_submit_button("Create Slot"):
                    res, err = api_request("POST", "/api/parking/slots", json={
                        "zone_id": sz_id, "sensor_id": ss_id, "status": s_status
                    })
                    if err: st.error(err)
                    else: st.success("Slot Created!")

            st.subheader("Update Slot Status")
            with st.form("update_slot_status_form"):
                u_zid = st.number_input("Zone ID", min_value=1, step=1)
                u_sid = st.number_input("Slot ID", min_value=1, step=1)
                u_stat = st.selectbox("New Status", ["FREE", "OCCUPIED", "UNDER MAINTENANCE", "RESERVED"])
                if st.form_submit_button("Update Status"):
                    res, err = api_request("PATCH", f"/api/parking/slots/{u_zid}/{u_sid}/status", json={"status": u_stat})
                    if err: st.error(err)
                    else: st.success("Slot updated!")

        with t3:
            st.subheader("Hardware Sensors")
            sensors, _ = api_request("GET", "/api/parking/sensors")
            if sensors: st.dataframe(sensors, use_container_width=True)
            
            with st.form("add_sensor_form"):
                sens_id = st.text_input("Sensor ID")
                mfr = st.text_input("Manufacturer")
                dom = st.date_input("Date of Manufacture").isoformat()
                model = st.text_input("Model")
                if st.form_submit_button("Add Sensor"):
                    res, err = api_request("POST", "/api/parking/sensors", json={
                        "sensor_id": sens_id, "manufacture": mfr,
                        "date_of_manufacture": dom, "model": model
                    })
                    if err: st.error(err)
                    else: st.success("Sensor added!")

    # --- 3. Vehicle & Booking Oversight ---
    elif admin_menu == "Vehicle & Booking Oversight":
        st.header("🚘 Vehicle & Booking Oversight")
        
        st.subheader("Filter Vehicles by Registration Status")
        status_filter = st.selectbox("Select Status Filter", ["ACTIVE", "SUSPENDED", "UNCLAIMED", "EXPIRED"])
        vehicles_filtered, _ = api_request("GET", f"/api/identity/vehicles/status/{status_filter}")
        if vehicles_filtered:
            st.dataframe(vehicles_filtered, use_container_width=True)

        st.subheader("Update Vehicle Status")
        with st.form("admin_veh_status"):
            target_plate = st.text_input("Target Plate Number")
            target_gmail = st.text_input("User Gmail (for Authorization)")
            new_reg_status = st.text_input("New Registration Status")
            if st.form_submit_button("Update Status"):
                res, err = api_request("PATCH", f"/api/identity/vehicles/{target_plate}/status", 
                                       params={"gmail": target_gmail}, json={"reg_status": new_reg_status})
                if err: st.error(err)
                else: st.success("Status updated!")

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

        t_cam, t_viol, t_tix = st.tabs(["Cameras", "Violations", "Issue Tickets"])
        
        with t_cam:
            st.subheader("Create Camera")
            with st.form("add_cam_form"):
                intersection = st.text_input("Intersection")
                ip = st.text_input("IP Address")
                cam_status = st.selectbox("Operational Status", ["ACTIVE", "INACTIVE", "MAINTENANCE"])
                if st.form_submit_button("Add Camera"):
                    res, err = api_request("POST", "/api/enforcement/cameras", json={
                        "intersection": intersection, "ip_address": ip, "operational_status": cam_status
                    })
                    if err: st.error(err)
                    else: st.success("Camera registered!")
            
            st.subheader("Inactive Cameras Overview")
            inc, _ = api_request("GET", "/api/enforcement/cameras/inactive")
            if inc: st.dataframe(inc, use_container_width=True)

        with t_viol:
            st.subheader("Log Traffic Violation")
            with st.form("log_viol_form"):
                rules = st.text_input("Rules Broken")
                v_time = st.date_input("Violation Date").isoformat()
                v_plate = st.text_input("Plate Number")
                v_cam = st.number_input("Camera ID", min_value=1, step=1)
                img = st.text_input("Image Link (Optional)")
                if st.form_submit_button("Log Violation"):
                    res, err = api_request("POST", "/api/enforcement/violations", json={
                        "rules_broken": rules, "violation_time": v_time,
                        "plate_no": v_plate, "camera_id": v_cam, "img_link": img if img else None
                    })
                    if err: st.error(err)
                    else: st.success("Violation logged!")

        with t_tix:
            st.subheader("Issue Ticket")
            with st.form("issue_ticket_form"):
                amt = st.number_input("Fine Amount ($)", min_value=0.0, step=10.0)
                iss_date = st.date_input("Issue Date", datetime.date.today()).isoformat()
                due_date = st.date_input("Due Date", datetime.date.today() + datetime.timedelta(days=30)).isoformat()
                viol_id = st.number_input("Violation ID", min_value=1, step=1)
                if st.form_submit_button("Issue Ticket"):
                    res, err = api_request("POST", "/api/ticketing/tickets", json={
                        "fine_amt": amt, "issue_date": iss_date, "due_date": due_date, "violation_id": viol_id
                    })
                    if err: st.error(err)
                    else: st.success("Ticket issued successfully!")

    # --- 5. Dispute Resolution ---
    elif admin_menu == "Dispute Resolution":
        st.header("⚖️ Dispute Resolution & Appeals")

        st.subheader("Pending Appeals")
        p_appeals, err = api_request("GET", "/api/ticketing/appeals/pending")
        if p_appeals:
            st.dataframe(p_appeals, use_container_width=True)

            st.divider()
            st.subheader("Resolve Appeal")
            with st.form("resolve_appeal_form"):
                app_id = st.number_input("Appeal ID", min_value=1, step=1)
                decision = st.selectbox("Decision", ["ACCEPTED", "REJECTED", "PENDING"])
                if st.form_submit_button("Render Decision"):
                    res, err = api_request("PATCH", f"/api/ticketing/appeals/{app_id}/decision", json={"appeal_decision": decision})
                    if err: st.error(err)
                    else: 
                        st.success(f"Appeal {app_id} marked as {decision}.")
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
    