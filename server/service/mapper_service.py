from server.models.DAO.time_slot import TimeSlotDAO
from server.models.DTO.error_dto import ErrorDTO
from server.models.DTO.user_dto import UserResponseDTO,UserLoginResponse,UserDTO, UserDetailDTO
from server.models.DAO.user import UserDAO
from server.models.DTO.reservation_dto import ReservationResponse, AssignedTableInfo
from server.models.DAO.reservation import ReservationDAO,ReservationTableAssignmentDAO
from server.models.DTO.slot_dto import SlotResponse,Table
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
def reservationDTO_to_response(reservation:ReservationDAO, assigments: List[dict]):
    assigmentList:List[AssignedTableInfo]=[]
    for a in assigments:
        assigmentList.append(
            AssignedTableInfo(
                table_id=a["slotTableId"],
                table_number=a["tableNumber"],
                assigned_seats=a["assignedSeats"],
                location=None
            )
        )
    return ReservationResponse(
        id=reservation.id,
        booking_reference=reservation.booking_reference,
        user_id=reservation.user_id,
        slot_id=reservation.slot_id,
        party_size=reservation.party_size,
        special_requirements=reservation.special_requirements,
        contact_email=reservation.contact_email,
        contact_name=reservation.contact_name,
        contact_phone=reservation.contact_phone,
        status=reservation.status,
        assigned_tables=assigmentList
        )
def slotTableDto_to_response(slotTime:TimeSlotDAO,table_list:list)->SlotResponse:
    tables:list[Table]=[]
    for t in table_list:
        tables.append(Table(
            tableNumber=t["tableNumber"],
            seats=t["seats"]
        ))
    return SlotResponse(
        slotid=slotTime.id,
        date=slotTime.date,
        startTime=slotTime.start_time,
        endTime=slotTime.end_time,
        mealType=slotTime.meal_type,
        tables=tables,
        message="Slot created successfully"
    ) 