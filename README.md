# Smart City Traffic & Parking Management System

A full-stack web application designed to manage smart city infrastructure, including vehicle registries, parking zone reservations, hardware sensors, traffic camera enforcement, and ticketing/appeals. 

The project consists of a **FastAPI** backend and a **Streamlit** frontend, all connected to an **Oracle Database**.

## 🛠 Tech Stack
* **Frontend:** Streamlit, Pandas, Requests
* **Backend:** FastAPI, Uvicorn, Pydantic (schemas)
* **Database:** Oracle Database, SQLAlchemy (Async), `oracledb`

## 📁 Repository Structure
Based on the current repository:
* `main.py` - The FastAPI backend application entry point.
* `app.py` - The Streamlit frontend application.
* `db.py` - SQLAlchemy database connection and ORM models.
* `schemas.py` - Pydantic models for request/response validation.
* `router/` - Directory containing the modular API endpoints (Identity, Parking, Booking, Enforcement, Ticketing).
* `requirements.txt` - Python dependencies list.

## 🚀 Getting Started (Local Node Setup)

Follow these instructions to download and run the project on your local machine.

### 1. Prerequisites
* Python 3.9 or higher installed.
* An active Oracle Database instance (local or cloud).
* Git installed.

### 2. Clone the Repository
Open your terminal and clone the project:
```bash
git clone [https://github.com/Gael12227/TrafficAndParkingManagement.git](https://github.com/Gael12227/TrafficAndParkingManagement.git)
cd TrafficAndParkingManagement
