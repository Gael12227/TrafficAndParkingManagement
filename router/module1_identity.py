from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from schemas import UserBase, VehicleBase
from db import get_db, User, Vehicle, UserPhone

router = APIRouter(prefix="/api/v1/identity", tags=["Module 1: Identity & Vehicle Registry"])

# 1. INSERT: Register a new user and map their multivalued phone numbers
@router.post("/users", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase, session: AsyncSession = Depends(get_db)):
    stmt = select(User).where((User.gmail == user.gmail) | (User.dl_no == user.dl_no))
    result = await session.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this Gmail or DL Number already exists")

    new_user = User(
        f_name=user.f_name, 
        m_name=user.m_name, 
        l_name=user.l_name, 
        dl_no=user.dl_no, 
        gmail=user.gmail
    )
    session.add(new_user)
    await session.flush() 

    for phone in user.phones:
        session.add(UserPhone(user_id=new_user.user_id, phone_no=phone))
        
    await session.commit()
    return user

# 2. UPDATE: Change a user's registered phone number
@router.patch("/users/{user_id}/phones/{old_phone}")
async def update_user_phone(user_id: int, old_phone: str, new_phone: str, session: AsyncSession = Depends(get_db)):
    stmt = select(UserPhone).where((UserPhone.user_id == user_id) & (UserPhone.phone_no == old_phone))
    result = await session.execute(stmt)
    phone_record = result.scalars().first()
    
    if not phone_record:
        raise HTTPException(status_code=404, detail="Phone record not found for this user")
        
    await session.delete(phone_record)
    session.add(UserPhone(user_id=user_id, phone_no=new_phone))
    await session.commit()
    
    return {"message": f"Phone updated from {old_phone} to {new_phone}"}

# 3. DELETE: Remove an old or unclaimed vehicle from the system
@router.delete("/vehicles/{plate_no}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(plate_no: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Vehicle).where(Vehicle.plate_no == plate_no)
    result = await session.execute(stmt)
    vehicle = result.scalars().first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    await session.delete(vehicle)
    await session.commit()
    return None

# 4. SELECT (1): View a specific user's entire fleet
@router.get("/users/{user_id}/vehicles", response_model=list[VehicleBase])
async def get_user_fleet(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User ID {user_id} not found")
    stmt = select(Vehicle).where(Vehicle.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()

# 5. SELECT (2): Search for vehicles by registration status
@router.get("/vehicles/status/{reg_status}", response_model=list[VehicleBase])
async def get_vehicles_by_status(reg_status: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Vehicle).where(Vehicle.reg_status == reg_status.upper())
    result = await session.execute(stmt)
    return result.scalars().all()

# 6. SELECT (3): List all users with missing data (Middle Name IS NULL)
@router.get("/users/missing-mname")
async def get_users_missing_mname(session: AsyncSession = Depends(get_db)):
    stmt = select(User.user_id, User.f_name, User.l_name).where(User.m_name == None)
    result = await session.execute(stmt)
    users = result.all()
    return [{"user_id": u.user_id, "f_name": u.f_name, "l_name": u.l_name} for u in users]

# 7. SELECT (4): Retrieve full user profile by Gmail
@router.get("/users/email/{gmail}", response_model=UserBase)
async def get_user_by_email(gmail: str, session: AsyncSession = Depends(get_db)):
    stmt = select(User).options(selectinload(User.phones)).where(User.gmail == gmail)
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    phone_list = [p.phone_no for p in user.phones]
    return UserBase(
        gmail=user.gmail, f_name=user.f_name, m_name=user.m_name, 
        l_name=user.l_name, dl_no=user.dl_no, phones=phone_list
    )

# 8. SELECT (5): List all registered vehicles in the system
@router.get("/vehicles", response_model=list[VehicleBase])
async def get_all_vehicles(session: AsyncSession = Depends(get_db)):
    stmt = select(Vehicle)
    result = await session.execute(stmt)
    return result.scalars().all()

# 9. INSERT: Register a new vehicle
@router.post("/vehicles", response_model=VehicleBase, status_code=status.HTTP_201_CREATED)
async def register_vehicle(vehicle: VehicleBase, session: AsyncSession = Depends(get_db)):
    if vehicle.user_id is not None:
        user = await session.get(User, vehicle.user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User ID {vehicle.user_id} does not exist in the registry")
    stmt = select(Vehicle).where(Vehicle.plate_no == vehicle.plate_no)
    if (await session.execute(stmt)).scalars().first():
        raise HTTPException(status_code=400, detail="Vehicle already registered")
        
    new_vehicle = Vehicle(**vehicle.model_dump())
    session.add(new_vehicle)
    await session.commit()
    return new_vehicle

# 10. UPDATE: Change vehicle registration status
@router.patch("/vehicles/{plate_no}/status", response_model=VehicleBase)
async def update_vehicle_status(plate_no: str, reg_status: str, session: AsyncSession = Depends(get_db)):
    vehicle = await session.get(Vehicle, plate_no)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    vehicle.reg_status = reg_status.upper()
    await session.commit()
    await session.refresh(vehicle)
    return vehicle

# 11. SELECT: List all users in the system
@router.get("/users", response_model=list[UserBase])
async def get_all_users(session: AsyncSession = Depends(get_db)):
    stmt = select(User).options(selectinload(User.phones))
    result = await session.execute(stmt)
    users = result.scalars().all()
    response = []
    for u in users:
        phone_list = [p.phone_no for p in u.phones]
        response.append(
            UserBase(
                gmail=u.gmail, 
                f_name=u.f_name, 
                m_name=u.m_name, 
                l_name=u.l_name, 
                dl_no=u.dl_no, 
                phones=phone_list
            )
        )
    return response