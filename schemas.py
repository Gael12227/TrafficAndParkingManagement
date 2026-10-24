from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Literal, List

class UserBase(BaseModel):
    gmail: str
    f_name: str
    m_name: Optional[str] = None
    l_name: str
    dl_no: str
    phones: List[str]

class VehicleBase(BaseModel):
    plate_no: str
    make: str
    model: str
    colour: str
    reg_status: Literal["VERIFIED", "UNCLAIMED", "OUT_OF_STATE"] = "UNCLAIMED"
    user_id: int

class ParkingZoneBase(BaseModel):
    location_name: str
    total_cap: int
    base_rate: float

class ParkingZoneResponse(ParkingZoneBase):
    zone_id: int

class ParkingSlotBase(BaseModel):
    sensor_id: str
    status: Literal["FREE", "OCCUPIED", "MAINTENANCE"] = "FREE"
    zone_id: int

class ParkingSlotResponse(ParkingSlotBase):
    slot_id: int

class SlotStatusUpdate(BaseModel):
    status: Literal["FREE", "OCCUPIED", "MAINTENANCE"]

class ReservationRequest(BaseModel):
    user_id: int
    plate_no: str
    slot_id: int
    start_time: datetime
    end_time: datetime

class ReservationResponse(ReservationRequest):
    res_id: int
    total_cost: float

class CameraBase(BaseModel):
    intersection: str
    ip_address: str
    operational_status: Literal["ACTIVE", "INACTIVE", "MAINTENANCE"] = "ACTIVE"

class CameraResponse(CameraBase):
    camera_id: int

class ViolationRequest(BaseModel):
    rules_broken: str
    img_link: str
    plate_no: str
    camera_id: int

class ViolationBase(ViolationRequest):
    violation_id: int
    violation_time: datetime

class TicketBase(BaseModel):
    ticket_id: int
    fine_amt: float
    issue_date: datetime
    due_date: datetime
    ticket_status: Literal["UNPAID", "PAID", "APPEALED", "FLAGGED"] = "UNPAID"
    violation_id: int

class AppealRequest(BaseModel):
    ticket_id: int
    reason_text: str

class AppealBase(AppealRequest):
    appeal_id: int
    appeal_date: datetime
    appeal_decision: Literal["PENDING", "APPROVED", "REJECTED"] = "PENDING"