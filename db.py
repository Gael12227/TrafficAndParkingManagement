import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import DateTime, ForeignKey, Integer, MetaData, Numeric, String, Identity
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

load_dotenv()

ORACLE_URL = f"oracle+oracledb_async://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/?service_name={os.getenv('DB_SERVICE')}"
engine = create_async_engine(ORACLE_URL, echo=False)

class Base(DeclarativeBase):
    metadata = MetaData()

class User(Base):
    __tablename__ = "System_User"
    user_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    gmail: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    f_name: Mapped[str] = mapped_column(String(50), nullable=False)
    m_name: Mapped[Optional[str]] = mapped_column(String(50))
    l_name: Mapped[str] = mapped_column(String(50), nullable=False)
    dl_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    phones: Mapped[List["UserPhone"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="user")
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="user")

class UserPhone(Base):
    __tablename__ = "User_Phone"
    user_id: Mapped[int] = mapped_column(ForeignKey("System_User.user_id", ondelete="CASCADE"), primary_key=True)
    phone_no: Mapped[str] = mapped_column(String(10), primary_key=True)
    user: Mapped["User"] = relationship(back_populates="phones")

class Vehicle(Base):
    __tablename__ = "Vehicle"
    plate_no: Mapped[str] = mapped_column(String(15), primary_key=True)
    make: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(50))
    colour: Mapped[str] = mapped_column(String(30))
    reg_status: Mapped[str] = mapped_column(String(20), default="UNCLAIMED")
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("System_User.user_id", ondelete="SET NULL"))
    user: Mapped["User"] = relationship(back_populates="vehicles")
    violations: Mapped[List["Violation"]] = relationship(back_populates="vehicle")
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="vehicle")

class ParkingZone(Base):
    __tablename__ = "Parking_zone"
    zone_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    location_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    total_cap: Mapped[int] = mapped_column(Integer, nullable=False)
    base_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    slots: Mapped[List["ParkingSlot"]] = relationship(back_populates="zone", cascade="all, delete-orphan")

class ParkingSlot(Base):
    __tablename__ = "Parking_slot"
    slot_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    sensor_id: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="FREE")
    zone_id: Mapped[int] = mapped_column(ForeignKey("Parking_zone.zone_id", ondelete="CASCADE"), nullable=False)
    zone: Mapped["ParkingZone"] = relationship(back_populates="slots")
    reservations: Mapped[List["Reservation"]] = relationship(back_populates="slot")

class Camera(Base):
    __tablename__ = "Camera"
    camera_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    intersection: Mapped[str] = mapped_column(String(150), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True)
    operational_status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    violations: Mapped[List["Violation"]] = relationship(back_populates="camera")

class Violation(Base):
    __tablename__ = "Violations"
    violation_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    rules_broken: Mapped[str] = mapped_column(String(100), nullable=False)
    violation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    img_link: Mapped[Optional[str]] = mapped_column(String(255))
    plate_no: Mapped[str] = mapped_column(ForeignKey("Vehicle.plate_no"), nullable=False)
    camera_id: Mapped[int] = mapped_column(ForeignKey("Camera.camera_id"), nullable=False)
    vehicle: Mapped["Vehicle"] = relationship(back_populates="violations")
    camera: Mapped["Camera"] = relationship(back_populates="violations")
    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="violation", uselist=False, cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "Ticket"
    ticket_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    fine_amt: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ticket_status: Mapped[str] = mapped_column(String(20), default="UNPAID")
    violation_id: Mapped[int] = mapped_column(ForeignKey("Violations.violation_id", ondelete="CASCADE"), unique=True, nullable=False)
    violation: Mapped["Violation"] = relationship(back_populates="ticket")
    appeals: Mapped[List["Appeal"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")

class Appeal(Base):
    __tablename__ = "Appeals"
    appeal_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    reason_text: Mapped[str] = mapped_column(String(500), nullable=False)
    appeal_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    appeal_decision: Mapped[str] = mapped_column(String(20), default="PENDING")
    ticket_id: Mapped[int] = mapped_column(ForeignKey("Ticket.ticket_id", ondelete="CASCADE"), nullable=False)
    ticket: Mapped["Ticket"] = relationship(back_populates="appeals")

class Reservation(Base):
    __tablename__ = "Reservation"
    res_id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    slot_id: Mapped[int] = mapped_column(ForeignKey("Parking_slot.slot_id"), nullable=False)
    plate_no: Mapped[str] = mapped_column(ForeignKey("Vehicle.plate_no"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("System_User.user_id"), nullable=False)
    slot: Mapped["ParkingSlot"] = relationship(back_populates="reservations")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="reservations")
    user: Mapped["User"] = relationship(back_populates="reservations")

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

async def get_db():
    async with SessionLocal() as session:
        yield session