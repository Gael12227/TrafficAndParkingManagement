from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from pydantic import BaseModel
from schemas import UserBase, VehicleBase
from schemas import UserCreate, UserLogin 
from schemas import VehicleCreate, VehicleBase
from db import get_db, User, Vehicle, UserPhone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

router = APIRouter(prefix="/api/identity", tags=["Module 1: Identity & Vehicle Registry"])

# ---------------------------------------------------------
# USER AUTHENTICATION & IDENTITY
# ---------------------------------------------------------
@router.post("/users", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_db)):
    stmt = select(User).where((User.gmail == user.gmail) | (User.dl_no == user.dl_no))
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="User with this Gmail or DL Number already exists")

    new_user = User(
        f_name=user.f_name, 
        m_name=user.m_name, 
        l_name=user.l_name, 
        dl_no=user.dl_no, 
        gmail=user.gmail,
        hashed_password=get_password_hash(user.password)
    )
    session.add(new_user)
    await session.flush() 

    for phone in user.phones:
        session.add(UserPhone(user_id=new_user.user_id, phone_no=phone))
        
    await session.commit()
    return UserBase(
        gmail=new_user.gmail, f_name=new_user.f_name, m_name=new_user.m_name, 
        l_name=new_user.l_name, dl_no=new_user.dl_no, phones=user.phones
    )

@router.post("/login")
async def login(credentials: UserLogin, session: AsyncSession = Depends(get_db)):
    stmt = select(User).options(selectinload(User.phones)).where(User.gmail == credentials.gmail)
    user = (await session.execute(stmt)).scalars().first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    return {
        "message": "Login successful",
        "user_id": user.user_id,
        "user": UserBase(
            gmail=user.gmail, f_name=user.f_name, m_name=user.m_name, 
            l_name=user.l_name, dl_no=user.dl_no, phones=[p.phone_no for p in user.phones]
        )
    }

@router.get("/users", response_model=list[UserBase])
async def get_all_users(session: AsyncSession = Depends(get_db)):
    stmt = select(User).options(selectinload(User.phones))
    users = (await session.execute(stmt)).scalars().all()
    
    return [
        UserBase(
            gmail=u.gmail, f_name=u.f_name, m_name=u.m_name, 
            l_name=u.l_name, dl_no=u.dl_no, phones=[p.phone_no for p in u.phones]
        ) for u in users
    ]

@router.get("/users/{user_id}/vehicles", response_model=list[VehicleBase])
async def get_user_fleet(user_id: int, session: AsyncSession = Depends(get_db)):
    if not await session.get(User, user_id):
        raise HTTPException(status_code=404, detail=f"User ID {user_id} not found")
        
    stmt = select(Vehicle).where(Vehicle.user_id == user_id)
    return (await session.execute(stmt)).scalars().all()

@router.get("/users/email/{gmail}", response_model=UserBase)
async def get_user_by_email(gmail: str, session: AsyncSession = Depends(get_db)):
    stmt = select(User).options(selectinload(User.phones)).where(User.gmail == gmail)
    user = (await session.execute(stmt)).scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return UserBase(
        gmail=user.gmail, f_name=user.f_name, m_name=user.m_name, 
        l_name=user.l_name, dl_no=user.dl_no, phones=[p.phone_no for p in user.phones]
    )

@router.patch("/users/{user_id}/phones/{old_phone}")
async def update_user_phone(user_id: int, old_phone: str, new_phone: str, session: AsyncSession = Depends(get_db)):
    stmt = select(UserPhone).where((UserPhone.user_id == user_id) & (UserPhone.phone_no == old_phone))
    phone_record = (await session.execute(stmt)).scalars().first()
    
    if not phone_record:
        raise HTTPException(status_code=404, detail="Phone record not found")
        
    await session.delete(phone_record)
    session.add(UserPhone(user_id=user_id, phone_no=new_phone))
    await session.commit()
    return {"message": "Phone updated"}

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()
    return None

# ---------------------------------------------------------
# VEHICLE REGISTRY
# ---------------------------------------------------------
@router.post("/vehicles", response_model=VehicleBase, status_code=status.HTTP_201_CREATED)
async def register_vehicle(vehicle: VehicleCreate, session: AsyncSession = Depends(get_db)):
    # 1. Prevent duplicate registrations
    stmt = select(Vehicle).where(Vehicle.plate_no == vehicle.plate_no)
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="Vehicle already registered")

    # 2. Resolve DL Number to User ID
    owner_id = None
    reg_status = getattr(vehicle, "reg_status", "CLAIMED").upper()

    if reg_status != "UNCLAIMED" and vehicle.dl_no:
        user_stmt = select(User).where(User.dl_no == vehicle.dl_no)
        user = (await session.execute(user_stmt)).scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail=f"User with DL {vehicle.dl_no} not found")
        
        owner_id = user.user_id
        reg_status = "CLAIMED"
    else:
        owner_id = None
        reg_status = "UNCLAIMED"

    # 3. Create and commit the vehicle record
    new_vehicle = Vehicle(
        plate_no=vehicle.plate_no,
        make=vehicle.make,
        model=vehicle.model,
        colour=vehicle.colour,
        reg_status=reg_status,
        user_id=owner_id
    )
    
    session.add(new_vehicle)
    await session.commit()
    await session.refresh(new_vehicle)
    
    return new_vehicle

@router.get("/vehicles", response_model=list[VehicleBase])
async def get_all_vehicles(session: AsyncSession = Depends(get_db)):
    return (await session.execute(select(Vehicle))).scalars().all()

@router.get("/vehicles/status/{reg_status}", response_model=list[VehicleBase])
async def get_vehicles_by_status(reg_status: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Vehicle).where(Vehicle.reg_status == reg_status.upper())
    return (await session.execute(stmt)).scalars().all()

@router.patch("/vehicles/{plate_no}/status", response_model=VehicleBase)
async def update_vehicle_status(plate_no: str, reg_status: str, session: AsyncSession = Depends(get_db)):
    vehicle = await session.get(Vehicle, plate_no)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    vehicle.reg_status = reg_status.upper()
    await session.commit()
    await session.refresh(vehicle)
    return vehicle

@router.delete("/vehicles/{plate_no}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(plate_no: str, session: AsyncSession = Depends(get_db)):
    vehicle = await session.get(Vehicle, plate_no)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    await session.delete(vehicle)
    await session.commit()
    return None