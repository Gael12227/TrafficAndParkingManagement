import streamlit as st
import requests
import datetime
import pandas as pd

# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Smart City Traffic & Parking System",
    page_icon="🚗",
    layout="wide"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global font */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(160deg,#0f2027,#203a43,#2c5364); }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    /* Metric cards */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg,#1e3a5f,#16213e);
        border-radius: 12px; padding: 1rem; color: #fff;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    [data-testid="metric-container"] label { color: #90caf9 !important; }
    [data-testid="metric-container"] [data-testid="metric-value"] { color: #ffffff !important; }
    /* Section headers */
    h2, h3 { color: #1565c0; }
    /* Tab selected */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1565c0; color: white; border-radius: 6px 6px 0 0;
    }
    /* Dataframe */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    /* Buttons – force white text in ALL states */
    .stButton > button,
    .stButton > button:hover,
    .stButton > button:active,
    .stButton > button:focus,
    .stButton > button:visited,
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stFormSubmitButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:active,
    div[data-testid="stFormSubmitButton"] > button:focus {
        background: linear-gradient(90deg,#1565c0,#0d47a1) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px !important;
    }
    .stButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(21,101,192,.45) !important;
        background: linear-gradient(90deg,#1976d2,#1565c0) !important;
        color: #ffffff !important;
    }
    /* Disabled button state */
    .stButton > button:disabled,
    .stButton > button[disabled],
    div[data-testid="stFormSubmitButton"] > button:disabled,
    div[data-testid="stFormSubmitButton"] > button[disabled] {
        background: linear-gradient(90deg,#546e7a,#455a64) !important;
        color: rgba(255,255,255,0.75) !important;
        cursor: not-allowed !important;
    }
    /* Logout / danger button override */
    .stButton > button p, div[data-testid="stFormSubmitButton"] > button p {
        color: #ffffff !important;
    }
    /* Success / error boxes */
    .stSuccess, .stError, .stInfo, .stWarning { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
for k, v in {
    "logged_in": False,
    "gmail": "",
    "user_name": "",
    "user_dl_no": "",      # ← stored at login so vehicle reg can pre-fill it
    "is_admin": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── API Helper ─────────────────────────────────────────────────────────────────
def api_request(method, endpoint, params=None, json=None):
    """
    Returns (data, error_string).
    404 responses are returned as (None, None) so callers can treat them
    as "empty result" rather than a hard error.
    """
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = requests.request(method, url, params=params, json=json, timeout=10)
        if resp.status_code in (200, 201):
            return resp.json(), None
        elif resp.status_code == 204:
            return {}, None
        elif resp.status_code == 404:
            # Treat 404 as "no data found" – not a real error
            return None, None
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            return None, f"Error {resp.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot reach the backend server. Make sure it is running on port 8000."
    except Exception as e:
        return None, f"Request failed: {str(e)}"


# ── Auth Utilities ─────────────────────────────────────────────────────────────
def logout():
    for k in ("logged_in", "gmail", "user_name", "user_dl_no", "is_admin"):
        st.session_state[k] = False if k == "logged_in" or k == "is_admin" else ""
    st.rerun()


# =============================================================================
# AUTH PAGE
# =============================================================================
def render_auth_page():
    st.markdown(
        "<h1 style='text-align:center;color:#1565c0;'>🚗 Smart City Traffic & Parking System</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#555;font-size:1.1rem;'>"
        "Manage reservations, vehicles, violations, and more – all in one place.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    tab_login, tab_signup, tab_admin = st.tabs(["🔑 Login", "📝 Sign Up", "🛡️ Admin Portal"])

    # ── Login ──────────────────────────────────────────────────────────────────
    with tab_login:
        with st.form("login_form"):
            login_gmail = st.text_input("Gmail Address")
            login_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if not login_gmail or not login_password:
                    st.error("Please enter both email and password.")
                else:
                    data, err = api_request(
                        "POST", "/api/identity/login",
                        json={"gmail": login_gmail, "password": login_password}
                    )
                    if err:
                        st.error(err)
                    elif data is None:
                        st.error("Invalid email or password.")
                    else:
                        user_data = data.get("user", {})
                        full_name = (
                            f"{user_data.get('f_name', '')} {user_data.get('l_name', '')}".strip()
                            or login_gmail
                        )
                        st.session_state.logged_in = True
                        st.session_state.gmail = login_gmail
                        st.session_state.user_name = full_name
                        st.session_state.user_dl_no = user_data.get("dl_no", "")
                        st.session_state.is_admin = False
                        st.success("Logged in successfully!")
                        st.rerun()

    # ── Sign Up ────────────────────────────────────────────────────────────────
    with tab_signup:
        with st.form("signup_form"):
            col1, col2 = st.columns(2)
            s_gmail    = col1.text_input("Gmail Address *")
            s_dl_no    = col2.text_input("Driver's License No. *")
            s_fname    = col1.text_input("First Name *")
            s_mname    = col1.text_input("Middle Name (optional)")
            s_lname    = col2.text_input("Last Name *")
            s_password = col2.text_input("Password *", type="password")
            s_phones   = st.text_input("Phone Numbers (comma-separated, ≥10 digits each) *")

            if st.form_submit_button("Create Account", use_container_width=True):
                phones = [p.strip() for p in s_phones.split(",") if p.strip()]
                if not all([s_gmail, s_fname, s_lname, s_dl_no, s_password]) or not phones:
                    st.error("Please fill in all mandatory fields and add at least one phone number.")
                else:
                    payload = {
                        "gmail": s_gmail, "f_name": s_fname,
                        "m_name": s_mname or None, "l_name": s_lname,
                        "dl_no": s_dl_no, "password": s_password, "phones": phones
                    }
                    data, err = api_request("POST", "/api/identity/users", json=payload)
                    if err:
                        st.error(err)
                    else:
                        st.success("Account created! Please log in from the Login tab.")

    # ── Admin ──────────────────────────────────────────────────────────────────
    with tab_admin:
        with st.form("admin_form"):
            admin_email = st.text_input("Admin Email", value="admin@smartcity.com")
            admin_pass  = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Login as Admin", use_container_width=True):
                if admin_email == "admin@smartcity.com" and admin_pass == "admin":
                    st.session_state.logged_in   = True
                    st.session_state.gmail        = admin_email
                    st.session_state.user_name    = "System Administrator"
                    st.session_state.is_admin     = True
                    st.success("Admin session started!")
                    st.rerun()
                else:
                    st.error("Invalid admin credentials.")


# =============================================================================
# USER DASHBOARD
# =============================================================================
def render_user_dashboard():
    gmail = st.session_state.gmail

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            f"<div style='text-align:center;padding:1rem 0;'>"
            f"<span style='font-size:3rem;'>👤</span><br>"
            f"<b style='font-size:1.1rem;'>{st.session_state.user_name}</b><br>"
            f"<span style='font-size:.8rem;opacity:.7;'>{gmail}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        menu = st.radio(
            "Navigate",
            ["🏠 Overview", "🚘 Vehicle Fleet", "🅿️ Parking & Reservations", "🧾 Tickets & Appeals", "⚙️ Account Settings"],
        )
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()

    # ─────────────────────────────────────────────────────────────────────────
    # OVERVIEW (summary dashboard)
    # ─────────────────────────────────────────────────────────────────────────
    if menu == "🏠 Overview":
        st.header("🏠 My Dashboard")

        col1, col2, col3 = st.columns(3)

        # Total parking spend
        spend_data, _ = api_request("GET", f"/api/booking/users/{gmail}/spent")
        total_spent = spend_data.get("total_spent", 0.0) if spend_data else 0.0
        col1.metric("💰 Total Parking Spend", f"₹{total_spent:.2f}")

        # Pending fines
        fines_data, _ = api_request("GET", f"/api/ticketing/users/{gmail}/fines/pending")
        total_fines = fines_data.get("total_pending_fine", 0.0) if fines_data else 0.0
        col2.metric("⚠️ Outstanding Fines", f"₹{total_fines:.2f}")

        # Number of vehicles
        fleet, _ = api_request("GET", f"/api/identity/users/{gmail}/vehicles")
        col3.metric("🚗 Registered Vehicles", len(fleet) if fleet else 0)

        st.divider()

        # My active reservations quick-view
        st.subheader("📋 My Recent Reservations")
        user_res, _ = api_request("GET", f"/api/booking/users/{gmail}/reservations")
        if user_res:
            df = pd.DataFrame(user_res)
            # Format datetimes nicely
            for col in ("start_time", "end_time"):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No reservations found. Book a parking slot from the Parking & Reservations section.")

        st.divider()
        st.subheader("🚘 My Vehicles")
        if fleet:
            st.dataframe(pd.DataFrame(fleet), use_container_width=True, hide_index=True)
        else:
            st.info("No vehicles registered yet. Add one from the Vehicle Fleet section.")

    # ─────────────────────────────────────────────────────────────────────────
    # VEHICLE FLEET
    # ─────────────────────────────────────────────────────────────────────────
    elif menu == "🚘 Vehicle Fleet":
        st.header("🚘 My Vehicle Fleet")

        # ── Registered vehicles ────────────────────────────────────────────────
        st.subheader("Your Registered Vehicles")
        fleet, err = api_request("GET", f"/api/identity/users/{gmail}/vehicles")
        if err:
            st.error(err)
        elif fleet:
            df = pd.DataFrame(fleet)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No vehicles registered under your account yet.")

        st.divider()

        # ── Register new vehicle ───────────────────────────────────────────────
        st.subheader("➕ Register New Vehicle")
        with st.form("register_vehicle_form"):
            col1, col2 = st.columns(2)
            plate_no = col1.text_input("Plate Number *")
            make     = col1.text_input("Make (e.g. Toyota) *")
            model    = col2.text_input("Model (e.g. Corolla) *")
            colour   = col2.text_input("Colour *")

            # Pre-fill the DL number from session so the vehicle is correctly linked
            dl_no = st.text_input(
                "Driver's License Number *",
                value=st.session_state.get("user_dl_no", ""),
                help="Must match your account DL number to link this vehicle to your profile."
            )

            if st.form_submit_button("Register Vehicle", use_container_width=True):
                if not all([plate_no, make, model, colour, dl_no]):
                    st.error("All fields including the DL Number are required to link the vehicle to your account.")
                else:
                    payload = {
                        "plate_no": plate_no.upper().strip(),
                        "make": make, "model": model,
                        "colour": colour, "dl_no": dl_no.strip()
                    }
                    res, err = api_request("POST", "/api/identity/vehicles", json=payload)
                    if err:
                        st.error(err)
                    else:
                        st.success(f"✅ Vehicle {plate_no.upper()} registered successfully!")
                        st.rerun()

        st.divider()

        # ── Update vehicle status ──────────────────────────────────────────────
        if fleet:
            st.subheader("🔄 Update Vehicle Status")
            plate_options = [v["plate_no"] for v in fleet]
            with st.form("update_vehicle_status_form"):
                sel_plate  = st.selectbox("Select Vehicle", plate_options)
                new_status = st.selectbox("New Status", ["CLAIMED", "UNCLAIMED", "ACTIVE", "SUSPENDED", "EXPIRED"])
                if st.form_submit_button("Update Status"):
                    res, err = api_request(
                        "PATCH", f"/api/identity/vehicles/{sel_plate}/status",
                        params={"gmail": gmail},
                        json={"reg_status": new_status}
                    )
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Vehicle status updated to {new_status}.")
                        st.rerun()

            st.divider()

            # ── Delete vehicle ─────────────────────────────────────────────────
            st.subheader("🗑️ Remove a Vehicle")
            with st.form("delete_vehicle_form"):
                del_plate = st.selectbox("Select Vehicle to Remove", plate_options, key="del_v")
                if st.form_submit_button("Remove Vehicle", use_container_width=True):
                    res, err = api_request(
                        "DELETE", f"/api/identity/vehicles/{del_plate}",
                        params={"gmail": gmail}
                    )
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Vehicle {del_plate} removed.")
                        st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # PARKING & RESERVATIONS
    # ─────────────────────────────────────────────────────────────────────────
    elif menu == "🅿️ Parking & Reservations":
        st.header("🅿️ Parking & Reservations")

        # ── KPI ────────────────────────────────────────────────────────────────
        spend_data, _ = api_request("GET", f"/api/booking/users/{gmail}/spent")
        total_spent = spend_data.get("total_spent", 0.0) if spend_data else 0.0
        st.metric("💰 Total Spending on Parking", f"₹{total_spent:.2f}")

        st.divider()

        # ── Tabs ────────────────────────────────────────────────────────────────
        tab_zones, tab_book, tab_my_res = st.tabs(["🗺️ Browse Zones & Slots", "📅 Book a Slot", "📋 My Reservations"])

        # TAB 1 – Browse Zones
        with tab_zones:
            st.subheader("Available Parking Zones (Sorted by Rate)")
            zones, _ = api_request("GET", "/api/parking/zones/rates/sorted")
            if zones:
                df_zones = pd.DataFrame(zones)
                st.dataframe(df_zones, use_container_width=True, hide_index=True)
            else:
                st.info("No parking zones available.")

            st.divider()
            st.subheader("🔍 Explore Slots in a Zone")

            col_z, col_f = st.columns([2, 1])
            zone_id_input   = col_z.number_input("Zone ID", min_value=1, step=1, key="browse_zone")
            status_filter_i = col_f.selectbox("Filter by Status", ["ALL", "FREE", "RESERVED", "OCCUPIED", "UNDER MAINTENANCE"])

            if st.button("View Slots"):
                params = {}
                if status_filter_i != "ALL":
                    params["status_filter"] = status_filter_i
                slots, err = api_request("GET", f"/api/parking/zones/{int(zone_id_input)}/slots", params=params)
                if err:
                    st.error(err)
                elif slots:
                    st.dataframe(pd.DataFrame(slots), use_container_width=True, hide_index=True)
                else:
                    st.info("No slots found for the selected filter.")

            st.divider()
            st.subheader("🔎 Search Zone by Location Name")
            search_loc = st.text_input("Enter full or partial location name")
            if st.button("Search"):
                if search_loc:
                    found, err = api_request("GET", f"/api/parking/zones/search/{search_loc}")
                    if err:
                        st.error(err)
                    elif found:
                        st.dataframe(pd.DataFrame(found), use_container_width=True, hide_index=True)
                    else:
                        st.info("No zones found matching that name.")

            st.divider()
            st.subheader("📊 Zone Capacity Details")
            zone_id_cap = st.number_input("Zone ID for Capacity Info", min_value=1, step=1, key="cap_zone")
            if st.button("Fetch Capacity"):
                cap, err = api_request("GET", f"/api/parking/zones/{int(zone_id_cap)}/capacity")
                if err:
                    st.error(err)
                elif cap:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Zone", cap.get("location_name"))
                    c2.metric("Total Slots", cap.get("total_capacity", 0))
                    c3.metric("Free Slots", cap.get("available_free_slots", 0))

        # TAB 2 – Book a Slot
        with tab_book:
            st.subheader("📅 Create a New Reservation")

            # Show user's vehicles for convenience
            fleet, _ = api_request("GET", f"/api/identity/users/{gmail}/vehicles")
            if fleet:
                plate_options = [v["plate_no"] for v in fleet]
                st.info(f"Your registered plates: **{', '.join(plate_options)}**")
            else:
                plate_options = []
                st.warning("⚠️ You have no registered vehicles. Register one in the Vehicle Fleet section first.")

            with st.form("create_reservation_form"):
                if plate_options:
                    res_plate = st.selectbox("Select Vehicle Plate", plate_options)
                else:
                    res_plate = st.text_input("Plate Number")

                col_z2, col_s = st.columns(2)
                res_zone = col_z2.number_input("Zone ID", min_value=1, step=1)
                res_slot = col_s.number_input("Slot ID", min_value=1, step=1)

                col_sd, col_st = st.columns(2)
                start_date = col_sd.date_input("Start Date", datetime.date.today())
                start_time = col_st.time_input("Start Time", datetime.time(9, 0))

                col_ed, col_et = st.columns(2)
                end_date = col_ed.date_input("End Date", datetime.date.today())
                end_time = col_et.time_input("End Time", datetime.time(10, 0))

                if st.form_submit_button("🅿️ Book Slot", use_container_width=True):
                    start_dt = datetime.datetime.combine(start_date, start_time)
                    end_dt   = datetime.datetime.combine(end_date, end_time)
                    if end_dt <= start_dt:
                        st.error("End time must be after start time.")
                    elif not res_plate:
                        st.error("Please select or enter a plate number.")
                    else:
                        payload = {
                            "start_time": start_dt.isoformat(),
                            "end_time":   end_dt.isoformat(),
                            "plate_no":   res_plate,
                            "zone_id":    int(res_zone),
                            "slot_id":    int(res_slot),
                        }
                        result, err = api_request("POST", "/api/booking/reservations", json=payload)
                        if err:
                            st.error(err)
                        else:
                            cost = result.get("total_cost", 0)
                            st.success(
                                f"✅ Reservation #{result.get('res_id')} created! "
                                f"Zone {result.get('zone_id')} / Slot {result.get('slot_id')} – "
                                f"Cost: ₹{cost}"
                            )
                            st.rerun()

        # TAB 3 – My Reservations
        with tab_my_res:
            st.subheader("📋 Your Reservations")

            user_res, err = api_request("GET", f"/api/booking/users/{gmail}/reservations")
            if err:
                st.error(err)
            elif user_res:
                df_res = pd.DataFrame(user_res)
                for col in ("start_time", "end_time"):
                    if col in df_res.columns:
                        df_res[col] = pd.to_datetime(df_res[col]).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(df_res, use_container_width=True, hide_index=True)

                st.divider()
                col_ext, col_can = st.columns(2)

                with col_ext:
                    st.subheader("⏩ Extend Reservation")
                    with st.form("extend_res_form"):
                        res_ids = [r["res_id"] for r in user_res]
                        ext_id   = st.selectbox("Reservation ID", res_ids)
                        ext_date = st.date_input("New End Date", datetime.date.today())
                        ext_time = st.time_input("New End Time", datetime.time(12, 0))
                        if st.form_submit_button("Extend", use_container_width=True):
                            new_end = datetime.datetime.combine(ext_date, ext_time).isoformat()
                            res, err = api_request(
                                "PATCH", f"/api/booking/reservations/{ext_id}/extend",
                                params={"new_end_time": new_end}
                            )
                            if err:
                                st.error(err)
                            else:
                                st.success("Reservation extended successfully!")
                                st.rerun()

                with col_can:
                    st.subheader("❌ Cancel Reservation")
                    with st.form("cancel_res_form"):
                        res_ids2 = [r["res_id"] for r in user_res]
                        cancel_id = st.selectbox("Reservation ID to Cancel", res_ids2)
                        if st.form_submit_button("Cancel Reservation", use_container_width=True):
                            res, err = api_request("DELETE", f"/api/booking/reservations/{cancel_id}")
                            if err:
                                st.error(err)
                            else:
                                st.success("Reservation cancelled.")
                                st.rerun()
            else:
                st.info("You have no reservations yet. Book a slot from the 'Book a Slot' tab.")

    # ─────────────────────────────────────────────────────────────────────────
    # TICKETS & APPEALS
    # ─────────────────────────────────────────────────────────────────────────
    elif menu == "🧾 Tickets & Appeals":
        st.header("🧾 Tickets & Dispute Resolution")

        # KPI
        fines_data, _ = api_request("GET", f"/api/ticketing/users/{gmail}/fines/pending")
        total_fines = fines_data.get("total_pending_fine", 0.0) if fines_data else 0.0
        st.metric("⚠️ Total Outstanding Fines", f"₹{total_fines:.2f}")

        tab_tix, tab_appeals = st.tabs(["🎫 My Tickets", "⚖️ My Appeals"])

        with tab_tix:
            st.subheader("Pending Tickets")
            tickets, err = api_request("GET", f"/api/ticketing/users/{gmail}/tickets/pending")
            if err:
                st.error(err)
            elif tickets:
                df_tix = pd.DataFrame(tickets)
                for col in ("issue_date", "due_date"):
                    if col in df_tix.columns:
                        df_tix[col] = pd.to_datetime(df_tix[col]).dt.strftime("%Y-%m-%d")
                st.dataframe(df_tix, use_container_width=True, hide_index=True)

                st.divider()
                st.subheader("💳 Pay a Ticket")
                with st.form("pay_ticket_form"):
                    tix_ids = [t["ticket_id"] for t in tickets]
                    pay_id  = st.selectbox("Select Ticket to Pay", tix_ids)
                    if st.form_submit_button("Pay Now", use_container_width=True):
                        res, err = api_request("PATCH", f"/api/ticketing/tickets/{pay_id}/pay")
                        if err:
                            st.error(err)
                        else:
                            st.success(f"Ticket #{pay_id} paid!")
                            st.rerun()
            else:
                st.success("✅ No pending tickets. You're all clear!")

        with tab_appeals:
            st.subheader("📝 File an Appeal")
            with st.form("appeal_form"):
                t_id    = st.number_input("Ticket ID to Dispute", min_value=1, step=1)
                reason  = st.text_area("Reason for Appeal *")
                app_date = st.date_input("Date of Appeal", datetime.date.today())
                if st.form_submit_button("Submit Appeal", use_container_width=True):
                    if not reason.strip():
                        st.error("Please enter a reason for the appeal.")
                    else:
                        payload = {
                            "ticket_id":   int(t_id),
                            "reason_text": reason,
                            "appeal_date": datetime.datetime.combine(app_date, datetime.time(0, 0)).isoformat()
                        }
                        res, err = api_request("POST", "/api/ticketing/appeals", json=payload)
                        if err:
                            st.error(err)
                        else:
                            st.success("Appeal submitted successfully!")
                            st.rerun()

            st.divider()
            st.subheader("📂 My Appeal History")
            appeals, err = api_request("GET", f"/api/ticketing/users/{gmail}/appeals")
            if err:
                st.error(err)
            elif appeals:
                df_ap = pd.DataFrame(appeals)
                if "appeal_date" in df_ap.columns:
                    df_ap["appeal_date"] = pd.to_datetime(df_ap["appeal_date"]).dt.strftime("%Y-%m-%d")
                # Color-code decision
                def style_decision(val):
                    colors = {"ACCEPTED": "green", "REJECTED": "red", "PENDING": "orange"}
                    return f"color: {colors.get(val, 'black')}; font-weight:bold"
                styled = df_ap.style.map(style_decision, subset=["appeal_decision"]) if "appeal_decision" in df_ap.columns else df_ap
                st.dataframe(styled, use_container_width=True, hide_index=True)
            else:
                st.info("No appeal history found.")

    # ─────────────────────────────────────────────────────────────────────────
    # ACCOUNT SETTINGS
    # ─────────────────────────────────────────────────────────────────────────
    elif menu == "⚙️ Account Settings":
        st.header("⚙️ Account Settings")

        st.subheader("📱 Update Phone Number")
        with st.form("update_phone_form"):
            old_phone = st.text_input("Current Phone Number to Replace")
            new_phone = st.text_input("New Phone Number")
            if st.form_submit_button("Update Phone"):
                if old_phone and new_phone:
                    res, err = api_request(
                        "PATCH",
                        f"/api/identity/users/{gmail}/phones/{old_phone}",
                        json={"new_phone": new_phone}
                    )
                    if err:
                        st.error(err)
                    else:
                        st.success("Phone number updated successfully!")
                else:
                    st.warning("Please enter both old and new phone numbers.")

        st.divider()
        st.subheader("🗑️ Delete Account")
        st.warning(
            "⚠️ **Danger Zone** – Deleting your account is permanent and will remove all associated data."
        )
        confirm = st.checkbox("I understand this action cannot be undone.")
        if st.button("Delete My Account Permanently", disabled=not confirm):
            res, err = api_request("DELETE", f"/api/identity/users/{gmail}")
            if err:
                st.error(err)
            else:
                st.success("Account deleted.")
                logout()


# =============================================================================
# ADMIN DASHBOARD
# =============================================================================
def render_admin_dashboard():
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center;padding:1rem 0;'>"
            "<span style='font-size:2.5rem;'>🛡️</span><br>"
            "<b style='font-size:1rem;'>ADMIN PANEL</b>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        admin_menu = st.radio("Modules", [
            "📊 System Overview",
            "🏗️ Parking Infrastructure",
            "🚘 Vehicle & Booking Oversight",
            "📹 Enforcement Operations",
            "⚖️ Dispute Resolution",
        ])
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()

    # ── Pre-fetch shared dropdown data ─────────────────────────────────────────
    all_zones, _     = api_request("GET", "/api/parking/zones/rates/sorted")
    zone_map         = {f"Zone {z['zone_id']} – {z['location_name']}": z['zone_id'] for z in (all_zones or [])}

    all_sensors, _   = api_request("GET", "/api/parking/sensors")
    sensor_ids       = [s['sensor_id'] for s in (all_sensors or [])]

    all_slots, _     = api_request("GET", "/api/parking/slots")
    slot_map         = {
        f"Zone {s['zone_id']} / Slot {s['slot_id']} ({s.get('status','')})": {"z": s['zone_id'], "s": s['slot_id']}
        for s in (all_slots or [])
    }

    all_cameras, _   = api_request("GET", "/api/enforcement/cameras")
    cam_map          = {f"Cam {c['camera_id']} – {c['intersection']}": c['camera_id'] for c in (all_cameras or [])}

    all_violations, _ = api_request("GET", "/api/enforcement/violations")
    viol_map         = {f"ID {v['violation_id']} – Plate {v['plate_no']} ({v.get('rules_broken','')[:30]})": v['violation_id'] for v in (all_violations or [])}

    # ─────────────────────────────────────────────────────────────────────────
    # SYSTEM OVERVIEW
    # ─────────────────────────────────────────────────────────────────────────
    if admin_menu == "📊 System Overview":
        st.header("📊 System Overview")

        cap, _ = api_request("GET", "/api/parking/capacity/total")
        if cap:
            c1, c2, c3 = st.columns(3)
            c1.metric("🏙️ Total Capacity", cap.get("system_total_capacity", 0))
            c2.metric("🚗 Occupied/Reserved", cap.get("system_occupied_or_reserved", 0))
            c3.metric("✅ Free Slots", cap.get("system_free_slots", 0))

        st.divider()

        col_rev, col_users = st.columns([1, 1])

        with col_rev:
            st.subheader("💵 Zone Revenue Lookup")
            if zone_map:
                z_sel = st.selectbox("Select Zone", list(zone_map.keys()), key="rev_z")
                if st.button("Fetch Revenue"):
                    rev, err = api_request("GET", f"/api/booking/zones/{zone_map[z_sel]}/revenue")
                    if err:
                        st.error(err)
                    else:
                        st.metric("Gross Revenue", f"₹{rev.get('total_revenue', 0):.2f}")
            else:
                st.info("No zones available.")

        with col_users:
            st.subheader("👥 All Registered Users")
            users, _ = api_request("GET", "/api/identity/users")
            if users:
                st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)
            else:
                st.info("No users found.")

        st.divider()
        st.subheader("📋 All Reservations")
        all_res, _ = api_request("GET", "/api/booking/reservations")
        if all_res:
            df_all = pd.DataFrame(all_res)
            for c in ("start_time", "end_time"):
                if c in df_all.columns:
                    df_all[c] = pd.to_datetime(df_all[c]).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(df_all, use_container_width=True, hide_index=True)
        else:
            st.info("No reservations in the system.")

        st.divider()
        st.subheader("🔴 Active Reservations Right Now")
        if st.button("Fetch Active Reservations"):
            active, _ = api_request("GET", "/api/booking/reservations/active")
            if active:
                df_act = pd.DataFrame(active)
                for c in ("start_time", "end_time"):
                    if c in df_act.columns:
                        df_act[c] = pd.to_datetime(df_act[c]).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(df_act, use_container_width=True, hide_index=True)
            else:
                st.info("No currently active reservations.")

    # ─────────────────────────────────────────────────────────────────────────
    # PARKING INFRASTRUCTURE
    # ─────────────────────────────────────────────────────────────────────────
    elif admin_menu == "🏗️ Parking Infrastructure":
        st.header("🏗️ Parking Infrastructure Management")
        t_zone, t_slot, t_sens = st.tabs(["🗺️ Zones", "🅿️ Slots", "📡 Sensors"])

        # ── Zones ──────────────────────────────────────────────────────────────
        with t_zone:
            st.subheader("All Parking Zones")
            if all_zones:
                st.dataframe(pd.DataFrame(all_zones), use_container_width=True, hide_index=True)
            else:
                st.info("No zones created yet.")

            st.divider()
            col_create_z, col_del_z = st.columns(2)

            with col_create_z:
                st.subheader("➕ Create Zone")
                with st.form("create_zone_form"):
                    loc_name   = st.text_input("Location Name *")
                    total_cap  = st.number_input("Total Capacity", min_value=1, step=1, value=10)
                    base_rate  = st.number_input("Base Rate (₹/hr)", min_value=0.0, step=5.0, value=50.0)
                    if st.form_submit_button("Create Zone", use_container_width=True):
                        if not loc_name:
                            st.error("Location name is required.")
                        else:
                            res, err = api_request("POST", "/api/parking/zones", json={
                                "location_name": loc_name, "total_cap": int(total_cap), "base_rate": float(base_rate)
                            })
                            if err: st.error(err)
                            else:
                                st.success(f"Zone '{loc_name}' created with {total_cap} slots!")
                                st.rerun()

            with col_del_z:
                st.subheader("🗑️ Delete Zone")
                if zone_map:
                    with st.form("delete_zone_form"):
                        del_z = st.selectbox("Zone to Delete", list(zone_map.keys()))
                        if st.form_submit_button("Delete Zone", use_container_width=True):
                            res, err = api_request("DELETE", f"/api/parking/zones/{zone_map[del_z]}")
                            if err: st.error(err)
                            else:
                                st.success("Zone deleted.")
                                st.rerun()
                else:
                    st.info("No zones to delete.")

            st.divider()
            st.subheader("🔍 Search Zone by Location")
            srch = st.text_input("Location keyword")
            if st.button("Search Zones"):
                if srch:
                    found, err = api_request("GET", f"/api/parking/zones/search/{srch}")
                    if err: st.error(err)
                    elif found: st.dataframe(pd.DataFrame(found), use_container_width=True, hide_index=True)
                    else: st.info("No zones matched.")

        # ── Slots ──────────────────────────────────────────────────────────────
        with t_slot:
            st.subheader("View Slots in a Zone")
            if zone_map:
                view_z = st.selectbox("Select Zone", list(zone_map.keys()), key="view_slots_z")
                sf = st.selectbox("Status Filter", ["ALL", "FREE", "OCCUPIED", "RESERVED", "UNDER MAINTENANCE"])
                params_sf = {} if sf == "ALL" else {"status_filter": sf}
                slots_in_zone, _ = api_request("GET", f"/api/parking/zones/{zone_map[view_z]}/slots", params=params_sf)
                if slots_in_zone:
                    st.dataframe(pd.DataFrame(slots_in_zone), use_container_width=True, hide_index=True)
                else:
                    st.info("No slots found with the selected filter.")

            st.divider()
            col_cs, col_us = st.columns(2)

            with col_cs:
                st.subheader("➕ Create Slot")
                if zone_map and sensor_ids:
                    with st.form("create_slot_form"):
                        c_z = st.selectbox("Zone", list(zone_map.keys()), key="cs_zone")
                        c_sens = st.selectbox("Sensor", sensor_ids)
                        c_stat = st.selectbox("Status", ["FREE", "OCCUPIED", "UNDER MAINTENANCE"])
                        if st.form_submit_button("Create Slot", use_container_width=True):
                            res, err = api_request("POST", "/api/parking/slots", json={
                                "zone_id": zone_map[c_z], "sensor_id": c_sens, "status": c_stat
                            })
                            if err: st.error(err)
                            else:
                                st.success("Slot created!")
                                st.rerun()
                else:
                    st.warning("Create at least one zone and one sensor first.")

            with col_us:
                st.subheader("🔄 Update Slot Status")
                if slot_map:
                    with st.form("update_slot_form"):
                        u_slot = st.selectbox("Slot", list(slot_map.keys()), key="us_slot")
                        u_stat = st.selectbox("New Status", ["FREE", "OCCUPIED", "UNDER MAINTENANCE", "RESERVED"])
                        if st.form_submit_button("Update Status", use_container_width=True):
                            z_id = slot_map[u_slot]["z"]
                            s_id = slot_map[u_slot]["s"]
                            res, err = api_request(
                                "PATCH", f"/api/parking/slots/{z_id}/{s_id}/status",
                                json={"status": u_stat}
                            )
                            if err: st.error(err)
                            else:
                                st.success("Slot status updated!")
                                st.rerun()
                else:
                    st.info("No slots available to update.")

            st.divider()
            st.subheader("🗑️ Delete Slot")
            if slot_map:
                with st.form("delete_slot_form"):
                    d_slot = st.selectbox("Slot to Delete", list(slot_map.keys()), key="ds_slot")
                    if st.form_submit_button("Delete Slot", use_container_width=True):
                        z_id = slot_map[d_slot]["z"]
                        s_id = slot_map[d_slot]["s"]
                        res, err = api_request("DELETE", f"/api/parking/slots/{z_id}/{s_id}")
                        if err: st.error(err)
                        else:
                            st.success("Slot deleted!")
                            st.rerun()

            st.divider()
            st.subheader("🔓 Release Expired Reservations")
            st.caption("Frees slots whose reservation started more than 1 hour ago and are still marked RESERVED.")
            if st.button("Release Expired Slots"):
                res, err = api_request("POST", "/api/parking/slots/release-expired-reservations")
                if err: st.error(err)
                elif res:
                    freed = res.get("freed_slots", [])
                    st.success(f"Released {len(freed)} slot(s). {res.get('message','')}")

        # ── Sensors ────────────────────────────────────────────────────────────
        with t_sens:
            st.subheader("All Sensors")
            if all_sensors:
                st.dataframe(pd.DataFrame(all_sensors), use_container_width=True, hide_index=True)
            else:
                st.info("No sensors registered.")

            st.divider()
            col_as, col_ds = st.columns(2)

            with col_as:
                st.subheader("➕ Add Sensor")
                with st.form("add_sensor_form"):
                    s_id  = st.text_input("Sensor ID (e.g. SENS-001)")
                    s_mfr = st.text_input("Manufacturer")
                    s_dom_raw = st.date_input("Date of Manufacture")
                    s_dom = datetime.datetime.combine(s_dom_raw, datetime.time(0, 0)).isoformat()
                    s_mod = st.text_input("Model")
                    if st.form_submit_button("Add Sensor", use_container_width=True):
                        res, err = api_request("POST", "/api/parking/sensors", json={
                            "sensor_id": s_id, "manufacture": s_mfr,
                            "date_of_manufacture": s_dom, "model": s_mod
                        })
                        if err: st.error(err)
                        else:
                            st.success("Sensor added!")
                            st.rerun()

            with col_ds:
                st.subheader("🗑️ Delete Sensor")
                if sensor_ids:
                    with st.form("delete_sensor_form"):
                        del_s = st.selectbox("Sensor to Delete", sensor_ids)
                        if st.form_submit_button("Delete Sensor", use_container_width=True):
                            res, err = api_request("DELETE", f"/api/parking/sensors/{del_s}")
                            if err: st.error(err)
                            else:
                                st.success("Sensor deleted!")
                                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # VEHICLE & BOOKING OVERSIGHT
    # ─────────────────────────────────────────────────────────────────────────
    elif admin_menu == "🚘 Vehicle & Booking Oversight":
        st.header("🚘 Vehicle & Booking Oversight")

        tab_veh, tab_book = st.tabs(["🚗 Vehicles", "📋 Reservations"])

        with tab_veh:
            st.subheader("All Vehicles")
            all_vehs, _ = api_request("GET", "/api/identity/vehicles")
            if all_vehs:
                st.dataframe(pd.DataFrame(all_vehs), use_container_width=True, hide_index=True)
            else:
                st.info("No vehicles in the system.")

            st.divider()
            st.subheader("Filter by Registration Status")
            reg_stat = st.selectbox("Status", ["CLAIMED", "UNCLAIMED", "ACTIVE", "SUSPENDED", "EXPIRED"])
            vehs_filt, _ = api_request("GET", f"/api/identity/vehicles/status/{reg_stat}")
            if vehs_filt:
                st.dataframe(pd.DataFrame(vehs_filt), use_container_width=True, hide_index=True)
            else:
                st.info(f"No vehicles with status '{reg_stat}'.")

            st.divider()
            st.subheader("🔍 Vehicle Reservations by Plate")
            plate_lookup = st.text_input("Enter Plate Number")
            if st.button("Fetch Reservations for Plate"):
                if plate_lookup:
                    v_res, err = api_request("GET", f"/api/booking/vehicles/{plate_lookup}/reservations")
                    if err: st.error(err)
                    elif v_res:
                        st.dataframe(pd.DataFrame(v_res), use_container_width=True, hide_index=True)
                    else:
                        st.info("No reservations found for this plate.")

        with tab_book:
            st.subheader("All Reservations in System")
            all_res, _ = api_request("GET", "/api/booking/reservations")
            if all_res:
                df_ar = pd.DataFrame(all_res)
                for c in ("start_time", "end_time"):
                    if c in df_ar.columns:
                        df_ar[c] = pd.to_datetime(df_ar[c]).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(df_ar, use_container_width=True, hide_index=True)
            else:
                st.info("No reservations yet.")

            st.divider()
            st.subheader("🔎 Look Up User Reservations by Gmail")
            lookup_gmail = st.text_input("User Gmail")
            if st.button("Lookup Reservations"):
                if lookup_gmail:
                    u_res, err = api_request("GET", f"/api/booking/users/{lookup_gmail}/reservations")
                    if err: st.error(err)
                    elif u_res:
                        st.dataframe(pd.DataFrame(u_res), use_container_width=True, hide_index=True)
                        spend, _ = api_request("GET", f"/api/booking/users/{lookup_gmail}/spent")
                        if spend:
                            st.metric("Total Parking Spend", f"₹{spend.get('total_spent', 0):.2f}")
                    else:
                        st.info("No reservations for this user.")

    # ─────────────────────────────────────────────────────────────────────────
    # ENFORCEMENT OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    elif admin_menu == "📹 Enforcement Operations":
        st.header("📹 Enforcement & Traffic Operations")
        t_cam, t_viol, t_tix = st.tabs(["📷 Cameras", "🚨 Violations", "🎫 Tickets"])

        # ── Cameras ────────────────────────────────────────────────────────────
        with t_cam:
            st.subheader("All Cameras")
            if all_cameras:
                st.dataframe(pd.DataFrame(all_cameras), use_container_width=True, hide_index=True)
            else:
                st.info("No cameras registered.")

            st.divider()
            col_cc, col_uc = st.columns(2)

            with col_cc:
                st.subheader("➕ Add Camera")
                with st.form("add_cam_form"):
                    inter = st.text_input("Intersection")
                    ip    = st.text_input("IP Address")
                    cst   = st.selectbox("Status", ["ACTIVE", "INACTIVE", "MAINTENANCE"])
                    if st.form_submit_button("Add Camera", use_container_width=True):
                        res, err = api_request("POST", "/api/enforcement/cameras", json={
                            "intersection": inter, "ip_address": ip, "operational_status": cst
                        })
                        if err: st.error(err)
                        else:
                            st.success("Camera registered!")
                            st.rerun()

            with col_uc:
                st.subheader("🔄 Update Camera Status")
                if cam_map:
                    with st.form("update_cam_form"):
                        uc_cam = st.selectbox("Camera", list(cam_map.keys()))
                        uc_st  = st.selectbox("New Status", ["ACTIVE", "INACTIVE", "MAINTENANCE"])
                        if st.form_submit_button("Update Status", use_container_width=True):
                            res, err = api_request(
                                "PATCH", f"/api/enforcement/cameras/{cam_map[uc_cam]}/status",
                                json={"operational_status": uc_st}
                            )
                            if err: st.error(err)
                            else:
                                st.success("Camera status updated!")
                                st.rerun()

            st.divider()
            st.subheader("🔍 Inactive Cameras by Location")
            loc_input = st.text_input("Location / Intersection Name")
            if st.button("Find Inactive Cameras"):
                if loc_input:
                    inactive_cams, err = api_request(
                        "GET", f"/api/enforcement/locations/{loc_input}/cameras/inactive"
                    )
                    if err: st.error(err)
                    elif inactive_cams:
                        st.dataframe(pd.DataFrame(inactive_cams), use_container_width=True, hide_index=True)
                    else:
                        st.info("No inactive cameras found at that location.")

        # ── Violations ─────────────────────────────────────────────────────────
        with t_viol:
            st.subheader("All Violations")
            if all_violations:
                df_viol = pd.DataFrame(all_violations)
                if "violation_time" in df_viol.columns:
                    df_viol["violation_time"] = pd.to_datetime(df_viol["violation_time"]).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(df_viol, use_container_width=True, hide_index=True)
            else:
                st.info("No violations logged.")

            st.divider()
            col_lv, col_vl = st.columns(2)

            with col_lv:
                st.subheader("🚨 Log Violation")
                if cam_map:
                    with st.form("log_viol_form"):
                        rules   = st.text_input("Rules Broken *")
                        v_date  = st.date_input("Violation Date")
                        v_time  = st.time_input("Violation Time")
                        v_plate = st.text_input("Plate Number *")
                        v_cam   = st.selectbox("Camera", list(cam_map.keys()))
                        img     = st.text_input("Image Link (optional)")
                        if st.form_submit_button("Log Violation", use_container_width=True):
                            viol_dt = datetime.datetime.combine(v_date, v_time).isoformat()
                            res, err = api_request("POST", "/api/enforcement/violations", json={
                                "rules_broken": rules,
                                "violation_time": viol_dt,
                                "plate_no": v_plate.upper().strip(),
                                "camera_id": cam_map[v_cam],
                                "img_link": img or None
                            })
                            if err: st.error(err)
                            else:
                                st.success(f"Violation logged (ID: {res.get('violation_id')})!")
                                st.rerun()
                else:
                    st.warning("Register a camera before logging violations.")

            with col_vl:
                st.subheader("🔍 Violations by Location")
                loc_v = st.text_input("Intersection / Location", key="viol_loc")
                if st.button("Fetch Violations by Location"):
                    if loc_v:
                        loc_viols, err = api_request("GET", f"/api/enforcement/locations/{loc_v}/violations")
                        if err: st.error(err)
                        elif loc_viols:
                            st.dataframe(pd.DataFrame(loc_viols), use_container_width=True, hide_index=True)
                        else:
                            st.info("No violations at that location.")

            st.divider()
            st.subheader("🔍 Vehicle Violation History")
            veh_plate = st.text_input("Enter Plate Number", key="veh_viol")
            if st.button("Fetch Violations for Plate"):
                if veh_plate:
                    p_viols, err = api_request("GET", f"/api/enforcement/vehicles/{veh_plate}/violations")
                    if err: st.error(err)
                    elif p_viols:
                        st.dataframe(pd.DataFrame(p_viols), use_container_width=True, hide_index=True)
                    else:
                        st.info("No violations for this plate.")

        # ── Tickets ────────────────────────────────────────────────────────────
        with t_tix:
            st.subheader("All Tickets")
            all_tix, _ = api_request("GET", "/api/ticketing/tickets")
            if all_tix:
                df_tix = pd.DataFrame(all_tix)
                for c in ("issue_date", "due_date"):
                    if c in df_tix.columns:
                        df_tix[c] = pd.to_datetime(df_tix[c]).dt.strftime("%Y-%m-%d")
                st.dataframe(df_tix, use_container_width=True, hide_index=True)
            else:
                st.info("No tickets issued yet.")

            st.divider()
            col_it, col_ts = st.columns(2)

            with col_it:
                st.subheader("🎫 Issue Ticket")
                if viol_map:
                    with st.form("issue_ticket_form"):
                        fine_amt  = st.number_input("Fine Amount (₹)", min_value=0.0, step=100.0)
                        iss_date  = st.date_input("Issue Date", datetime.date.today())
                        due_date_ = st.date_input("Due Date", datetime.date.today() + datetime.timedelta(days=30))
                        t_v_key   = st.selectbox("Violation Record", list(viol_map.keys()))
                        if st.form_submit_button("Issue Ticket", use_container_width=True):
                            res, err = api_request("POST", "/api/ticketing/tickets", json={
                                "fine_amt":     float(fine_amt),
                                "issue_date":   datetime.datetime.combine(iss_date, datetime.time(0,0)).isoformat(),
                                "due_date":     datetime.datetime.combine(due_date_, datetime.time(0,0)).isoformat(),
                                "violation_id": viol_map[t_v_key]
                            })
                            if err: st.error(err)
                            else:
                                st.success(f"Ticket #{res.get('ticket_id')} issued!")
                                st.rerun()
                else:
                    st.warning("Log a violation before issuing tickets.")

            with col_ts:
                st.subheader("🔄 Update Ticket Status (Admin Override)")
                with st.form("update_tix_status_form"):
                    t_id    = st.number_input("Ticket ID", min_value=1, step=1)
                    t_stat  = st.selectbox("New Status", ["PAID", "NULLIFIED", "PENDING"])
                    if st.form_submit_button("Update Status", use_container_width=True):
                        res, err = api_request(
                            "PATCH", f"/api/ticketing/tickets/{int(t_id)}/status",
                            json={"ticket_status": t_stat}
                        )
                        if err: st.error(err)
                        else:
                            st.success(f"Ticket #{t_id} status set to {t_stat}.")
                            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # DISPUTE RESOLUTION
    # ─────────────────────────────────────────────────────────────────────────
    elif admin_menu == "⚖️ Dispute Resolution":
        st.header("⚖️ Dispute Resolution & Appeals")

        st.subheader("📋 All Pending Appeals")
        p_appeals, _ = api_request("GET", "/api/ticketing/appeals/pending")
        if p_appeals:
            df_pa = pd.DataFrame(p_appeals)
            if "appeal_date" in df_pa.columns:
                df_pa["appeal_date"] = pd.to_datetime(df_pa["appeal_date"]).dt.strftime("%Y-%m-%d")
            st.dataframe(df_pa, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("✅ Render Decision")
            appeal_map = {f"Appeal {a['appeal_id']} (Ticket {a['ticket_id']})": a['appeal_id'] for a in p_appeals}
            with st.form("resolve_appeal_form"):
                app_key  = st.selectbox("Select Appeal", list(appeal_map.keys()))
                decision = st.selectbox("Decision", ["ACCEPTED", "REJECTED", "PENDING"])
                if st.form_submit_button("Submit Decision", use_container_width=True):
                    res, err = api_request(
                        "PATCH", f"/api/ticketing/appeals/{appeal_map[app_key]}/decision",
                        json={"appeal_decision": decision}
                    )
                    if err: st.error(err)
                    else:
                        st.success(f"Appeal marked as **{decision}**.")
                        st.rerun()
        else:
            st.success("✅ No pending appeals in the system.")

        st.divider()
        st.subheader("🔍 Look Up Appeals by User Gmail")
        lookup_g = st.text_input("User Gmail", key="appeal_lookup")
        if st.button("Fetch User Appeals"):
            if lookup_g:
                u_apps, err = api_request("GET", f"/api/ticketing/users/{lookup_g}/appeals")
                if err: st.error(err)
                elif u_apps:
                    st.dataframe(pd.DataFrame(u_apps), use_container_width=True, hide_index=True)
                else:
                    st.info("No appeals found for this user.")


# =============================================================================
# MAIN
# =============================================================================
def main():
    if not st.session_state.logged_in:
        render_auth_page()
    elif st.session_state.is_admin:
        render_admin_dashboard()
    else:
        render_user_dashboard()


if __name__ == "__main__":
    main()