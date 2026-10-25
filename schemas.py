import re
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List

class UserBase(BaseModel):
    gmail: str
    f_name: str
    m_name: Optional[str] = None
    l_name: str
    dl_no: str
    phones: List[str]

    @field_validator('phones')
    @classmethod
    def validate_phones(cls, phones: List[str]) -> List[str]:
        if not phones:
            raise ValueError("At least one phone number is required.")
        for phone in phones:
            cleaned_phone = re.sub(r'\D', '', phone)
            if len(cleaned_phone) < 10:
                raise ValueError(f"Phone number '{phone}' must contain at least 10 digits.")
        return phones
        
    model_config = ConfigDict(from_attributes=True)


class VehicleBase(BaseModel):
    plate_no: str
    make: str
    model: str
    colour: str
    user_id: Optional[int] = None
    reg_status: str = "UNCLAIMED"
    
    model_config = ConfigDict(from_attributes=True)



class ParkingZoneBase(BaseModel):
    location_name: str
    total_cap: int
    base_rate: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class ParkingSlotBase(BaseModel):
    zone_id: int
    slot_id: Optional[int] = None
    sensor_id: str
    status: str = "FREE"
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, status: str) -> str:
        allowed = ["FREE", "OCCUPIED", "UNDER MAINTENANCE", "RESERVED"]
        if status.upper() not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return status.upper()
        
    model_config = ConfigDict(from_attributes=True)


class SensorBase(BaseModel):
    sensor_id: str
    manufacture: str
    date_of_manufacture: datetime
    model: str
    status: str = "active"
    
    model_config = ConfigDict(from_attributes=True)


class ReservationBase(BaseModel):
    start_time: datetime
    end_time: datetime
    plate_no: str
    user_id: int
    zone_id: int
    slot_id: int
    total_cost: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)


class CameraBase(BaseModel):
    intersection: str
    ip_address: str
    operational_status: str = "ACTIVE"
    
    model_config = ConfigDict(from_attributes=True)


class ViolationBase(BaseModel):
    rules_broken: str
    violation_time: datetime
    img_link: Optional[str] = None
    plate_no: str
    camera_id: int
    
    model_config = ConfigDict(from_attributes=True)

class TicketBase(BaseModel):
    fine_amt: Decimal
    issue_date: datetime
    due_date: datetime
    ticket_status: str = "UNPAID"
    violation_id: int
    
    model_config = ConfigDict(from_attributes=True)


class AppealBase(BaseModel):
    reason_text: str
    appeal_date: datetime
    appeal_decision: str = "PENDING"
    ticket_id: int
    
    model_config = ConfigDict(from_attributes=True)