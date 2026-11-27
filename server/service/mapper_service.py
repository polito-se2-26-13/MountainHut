from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import TimeSlotDAO
from server.models.DTO.error_dto import ErrorDTO
from server.models.DTO.user_dto import UserCreateDTO, UserDetailReservationDTO, UserResponseDTO,UserLoginResponse,UserDTO, UserDetailDTO, UserSearchResponse
from server.models.DAO.user import UserDAO
from server.models.DTO.reservation_dto import ReservationCreate, ReservationHinkerCreate, ReservationResponse, AssignedTableInfo,ReservationMailDTO,SpecialRequirementDTO
from server.models.DAO.reservation import ReservationDAO,ReservationTableAssignmentDAO,SpecialRequirementDAO
from server.models.DTO.slot_dto import SlotResponse,Table,SlotDetail
from server.models.DTO.table_dto import TableResponse
from server.models.DTO.time_dto import TimeResponse
from typing import List

from server.models.enum.user_type import UserType

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
        special_requirements=reservation.requirements,
        contact_email=reservation.contact_email,
        contact_name=reservation.contact_name,
        contact_phone=reservation.contact_phone,
        status=reservation.status,
        assigned_tables=assigments
        )
def slotTableDto_to_response(slotTime:TimeSlotDAO,table_list:list[Table])->SlotResponse:
    return SlotResponse(
        slotId=slotTime.id,
        date=slotTime.date,
        startTime=slotTime.start_time.strftime("%H:%M"),
        endTime=slotTime.end_time.strftime("%H:%M"),
        mealType=slotTime.meal_type,
        tables=table_list,
        message="Slot created successfully"
    ) 

def slots_deatils_to_response(slots:list[tuple[TimeSlotDAO, list[Table]]])->list[SlotDetail]:
    results:list[SlotDetail]=[]
    for slot,tables in slots:
        results.append(SlotDetail(
            slotId=slot.id,
            date= slot.date,
            startTime=slot.start_time.strftime("%H:%M"),
            endTime=slot.end_time.strftime("%H:%M"),
            mealType=slot.meal_type,
            tables=tables
        ))
    return results

def reservationEmailDto_to_email(
        ref:str,
        email:str,
        date:str,
        timeSlot:str,
        partySize:int,
        spReq:list,
        hikerName:str,
        booking_name:str,
        changed:bool=False,):
    
    return ReservationMailDTO(
        booking_reference=ref,
        contact_email=email,
        date_str=date,
        time_slot=timeSlot,
        party_size=partySize,
        special_reqs=spReq,
        hiker_name=hikerName,
        changed=changed,
        booking_name=booking_name
    )

def specialRequirementDTO_to_DAO(requirements:list[SpecialRequirementDTO])->list[SpecialRequirementDAO]:
    return [SpecialRequirementDAO(has_allergy=r.has_allergy,description=r.description) for r in requirements]

def reservationTableAssignmentDAO_to_AssignedTableInfo(assigned:ReservationTableAssignmentDAO,number:str)->AssignedTableInfo:
    return AssignedTableInfo(
                    table_id=assigned.slot_table_id,
                    table_number=number,
                    assigned_seats=assigned.assigned_seats,
                )
def timeSlotDAO_to_response(timeDao:TimeSlotDAO)->TimeResponse:
    return TimeResponse(
        id=timeDao.id,
        date=timeDao.date,
        startTime=timeDao.start_time.strftime("%H:%M"),
        endTime=timeDao.end_time.strftime("%H:%M"),
        mealType=timeDao.meal_type,
    )
def tableDAO_to_response(tableDao:TableDAO)->TableResponse:
    return TableResponse(
        id=tableDao.id,
        tableNumber=tableDao.table_number,
        capacity=tableDao.capacity,
        location=tableDao.location,
    )
def userDAO_to_searchResponse(userDAO:UserDAO)->UserSearchResponse:
    return UserSearchResponse(
        id=userDAO.id,
        email=userDAO.email,
        firstName=userDAO.first_name,
        lastName=userDAO.last_name,
        phone=userDAO.phone,
        emergencyContact=userDAO.emergency_contact,
    )
def UserDetailRes_to_UserCreateDTO(userDetail:UserDetailReservationDTO,psw:str)->UserCreateDTO:
    return UserCreateDTO(
        email=userDetail.email,
        password=psw,
        role=UserType.HIKER,
        firstName=userDetail.firstName,
        lastName=userDetail.lastName,
        phone=userDetail.phone,
        emergencyContact=userDetail.emergencyConctat
    )
def reservationHinkerCreate_to_reservationCreate(reservation:ReservationHinkerCreate,user_id:int)->ReservationCreate:
    return ReservationCreate(
        slot_id=reservation.slot_id,
        party_size=reservation.party_size,
        contact_name=reservation.contact_name,
        user_id=user_id,
        contact_email=reservation.contact_email,
        contact_phone=reservation.contact_phone,
        special_requirements=reservation.special_requirements
    )