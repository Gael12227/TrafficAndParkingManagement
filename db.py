import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric, ForeignKeyConstraint
DATABASE_URL = os.getenv("DATABASE_URL", "oracle+oracledb_async://username:password@hostname:port/?service_name=servicename")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session
class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    f_name = Column(String(50), nullable=False)
    m_name = Column(String(50), nullable=True)
    l_name = Column(String(50), nullable=False)
    dl_no = Column(String(50), unique=True, nullable=False)
    gmail = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False) 
    
    phones = relationship("UserPhone", back_populates="user", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="owner")
    reservations = relationship("Reservation", back_populates="user")

class UserPhone(Base):
    __tablename__ = "user_phones"
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    phone_no = Column(String(20), primary_key=True)
    
    user = relationship("User", back_populates="phones")

class Vehicle(Base):
    __tablename__ = "vehicles"
    plate_no = Column(String(20), primary_key=True)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    colour = Column(String(30), nullable=False)
    reg_status = Column(String(20), default="UNCLAIMED")
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    
    owner = relationship("User", back_populates="vehicles")
    reservations = relationship("Reservation", back_populates="vehicle")
    violations = relationship("Violation", back_populates="vehicle")

class ParkingZone(Base):
    __tablename__ = "parking_zones"
    zone_id = Column(Integer, primary_key=True, autoincrement=True)
    location_name = Column(String(100), unique=True, nullable=False)
    total_cap = Column(Integer, default=0)
    base_rate = Column(Numeric(10, 2), nullable=False)
    
    slots = relationship("ParkingSlot", back_populates="zone", cascade="all, delete-orphan")

class ParkingSlot(Base):
    __tablename__ = "parking_slots"
    zone_id = Column(Integer, ForeignKey("parking_zones.zone_id"), primary_key=True)
    slot_id = Column(Integer, primary_key=True)
    sensor_id = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="FREE")
    
    zone = relationship("ParkingZone", back_populates="slots")
    reservations = relationship("Reservation", back_populates="slot")

class Sensor(Base):
    __tablename__ = "sensors"
    sensor_id = Column(String(50), primary_key=True)
    manufacture = Column(String(100), nullable=False)
    date_of_manufacture = Column(DateTime, nullable=False)
    model = Column(String(100), nullable=False)
    status = Column(String(20), default="active")

class Reservation(Base):
    __tablename__ = "reservations"
    res_id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)
    zone_id = Column(Integer, nullable=False)
    slot_id = Column(Integer, nullable=False)
    plate_no = Column(String(20), ForeignKey("vehicles.plate_no"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['zone_id', 'slot_id'],
            ['parking_slots.zone_id', 'parking_slots.slot_id']
        ),
    )
    
    slot = relationship("ParkingSlot", back_populates="reservations")
    user = relationship("User", back_populates="reservations")
    vehicle = relationship("Vehicle", back_populates="reservations")

class Camera(Base):
    __tablename__ = "cameras"
    camera_id = Column(Integer, primary_key=True, autoincrement=True)
    intersection = Column(String(100), nullable=False)
    ip_address = Column(String(50), unique=True, nullable=False)
    operational_status = Column(String(20), default="ACTIVE")
    
    violations = relationship("Violation", back_populates="camera")

class Violation(Base):
    __tablename__ = "violations"
    violation_id = Column(Integer, primary_key=True, autoincrement=True)
    rules_broken = Column(String(255), nullable=False)
    violation_time = Column(DateTime(timezone=True), nullable=False)
    img_link = Column(String(255), nullable=True)
    plate_no = Column(String(20), ForeignKey("vehicles.plate_no"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.camera_id"), nullable=False)
    
    camera = relationship("Camera", back_populates="violations")
    vehicle = relationship("Vehicle", back_populates="violations")
    tickets = relationship("Ticket", back_populates="violation", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id = Column(Integer, primary_key=True, autoincrement=True)
    fine_amt = Column(Numeric(10, 2), nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    ticket_status = Column(String(20), default="UNPAID")
    violation_id = Column(Integer, ForeignKey("violations.violation_id"), unique=True, nullable=False)
    
    violation = relationship("Violation", back_populates="tickets")
    appeals = relationship("Appeal", back_populates="ticket", cascade="all, delete-orphan")

class Appeal(Base):
    __tablename__ = "appeals"
    appeal_id = Column(Integer, primary_key=True, autoincrement=True)
    reason_text = Column(String(500), nullable=False)
    appeal_date = Column(DateTime(timezone=True), nullable=False)
    appeal_decision = Column(String(20), default="PENDING")
    ticket_id = Column(Integer, ForeignKey("tickets.ticket_id"), nullable=False)
    
    ticket = relationship("Ticket", back_populates="appeals")