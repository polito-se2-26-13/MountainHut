from server.models.DAO.time_slot import TimeSlotDAO
from server.models.DTO.error_dto import ErrorDTO
from server.models.DTO.user_dto import UserResponseDTO,UserLoginResponse,UserDTO, UserDetailDTO
from server.models.DAO.user import UserDAO
from server.models.DTO.reservation_dto import ReservationResponse, AssignedTableInfo,ReservationMailDTO
from server.models.DAO.reservation import ReservationDAO,ReservationTableAssignmentDAO
from server.models.DTO.slot_dto import SlotResponse,Table,SlotDetail
from typing import List

def create_error_dto(code: int, message: str, name: str) -> ErrorDTO:
    """Create an ErrorDTO instance"""
    return ErrorDTO(code=code, message=message, name=name)

def userdao_to_responsedto(userDao:UserDAO)->UserResponseDTO:
    return UserResponseDTO(
        id=userDao.id
    )

def loging_response(token:str, user:UserDetailDTO)->UserLoginResponse:
    return UserLoginResponse(token=token,user=user)

def userdao_to_userdto(user:UserDAO)->UserDTO:
    return UserDTO(
        id=user.id,
        email=user.email,
        password=user.password_hash,
        role=user.role,
        firstName=user.first_name,
        lastName=user.last_name,
        phone=user.phone
    )
def userdao_to_userdto_detail(user:UserDAO)->UserDetailDTO:
    return UserDetailDTO(
        id=user.id,
        email=user.email,
        role=user.role,
        firstName=user.first_name,
        lastName=user.last_name,
        phone=user.phone
    )
def reservationDTO_to_response(reservation:ReservationDAO, assigments: List[AssignedTableInfo]):
    return ReservationResponse(
        id=reservation.id,
        booking_reference=reservation.booking_reference,
        user_id=reservation.user_id,
        slot_id=reservation.slot_id,
        date=reservation.slot.date.isoformat(),
        start_time=reservation.slot.start_time.strftime("%H:%M"),
        end_time=reservation.slot.end_time.strftime("%H:%M"),
        party_size=reservation.party_size,
        special_requirements=reservation.special_requirements,
        contact_email=reservation.contact_email,
        contact_name=reservation.contact_name,
        contact_phone=reservation.contact_phone,
        status=reservation.status,
        assigned_tables=assigments
        )
def slotTableDto_to_response(slotTime:TimeSlotDAO,table_list:list)->SlotResponse:
    tables:list[Table]=[]
    for t in table_list:
        tables.append(Table(
            tableNumber=t["tableNumber"],
            seats=t["seats"]
        ))
    return SlotResponse(
        slotId=slotTime.id,
        date=slotTime.date,
        startTime=slotTime.start_time.strftime("%H:%M"),
        endTime=slotTime.end_time.strftime("%H:%M"),
        mealType=slotTime.meal_type,
        tables=tables,
        message="Slot created successfully"
    ) 

def slots_deatils_to_response(slots:list[tuple[TimeSlotDAO, list[dict[str, int]]]])->SlotDetail:
    results:list[SlotDetail]=[]
    for slot,tables in slots:
        results.append(SlotDetail(
            slotId=slot.id,
            date= slot.date,
            startTime=slot.start_time.strftime("%H:%M"),
            endTime=slot.end_time.strftime("%H:%M"),
            mealType=slot.meal_type,
            tables=tableList(tables)
        ))
    return results

def tableList(tables: list[dict]):
    tablesDto = []

    for table in tables:
        tablesDto.append(
            Table(
                tableNumber=table["table_number"],
                seats=table["available_seats"]
            )
        )

    return tablesDto

def reservationEmailDto_to_email(
        ref:str,
        email:str,
        date:str,
        timeSlot:str,
        partySize:int,
        spReq:str,
        hikerName:str):
    
    return ReservationMailDTO(
        booking_reference=ref,
        contact_email=email,
        date_str=date,
        time_slot=timeSlot,
        party_size=partySize,
        special_reqs=spReq,
        hiker_name=hikerName
    )

def reservationTableAssignmentDAO_to_AssignedTableInfo(assigned:ReservationTableAssignmentDAO,number:str)->AssignedTableInfo:
    return AssignedTableInfo(
                    table_id=assigned.slot_table_id,
                    table_number=number,
                    assigned_seats=assigned.assigned_seats,
                    location=None
                )