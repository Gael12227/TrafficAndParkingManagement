from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from schemas import UserBase, VehicleBase
from db import get_db, User, Vehicle, UserPhone

router = APIRouter(prefix="/api/identity", tags=["Module 1: Identity & Vehicle Registry"])

@router.post("/users", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase, session: AsyncSession = Depends(get_db)):
    stmt = select(User).where((User.gmail == user.gmail) | (User.dl_no == user.dl_no))
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="User with this Gmail or DL Number already exists")

    new_user = User(
        f_name=user.f_name, m_name=user.m_name, l_name=user.l_name, 
        dl_no=user.dl_no, gmail=user.gmail
    )
    session.add(new_user)
    await session.flush() 

    for phone in user.phones:
        session.add(UserPhone(user_id=new_user.user_id, phone_no=phone))
        
    await session.commit()
    return user

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

@router.post("/vehicles", response_model=VehicleBase, status_code=status.HTTP_201_CREATED)
async def register_vehicle(vehicle: VehicleBase, session: AsyncSession = Depends(get_db)):
    if vehicle.user_id is not None:
        if not await session.get(User, vehicle.user_id):
            raise HTTPException(status_code=404, detail=f"User ID {vehicle.user_id} does not exist")

    stmt = select(Vehicle).where(Vehicle.plate_no == vehicle.plate_no)
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="Vehicle already registered")
        
    new_vehicle = Vehicle(**vehicle.model_dump())
    session.add(new_vehicle)
    await session.commit()
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