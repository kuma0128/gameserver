from enum import Enum

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import (
    JoinRoomResult,
    LiveDifficulty,
    ResultUser,
    RoomInfo,
    RoomResultResponse,
    RoomUser,
    RoomWaitResponse,
    SafeUser,
    WaitRoomStatus,
)

app = FastAPI()

# Sample APIs


@app.get("/")
async def root():
    return {"message": "Hello World!"}


# User APIs


class UserCreateRequest(BaseModel):
    user_name: str
    leader_card_id: int


class UserCreateResponse(BaseModel):
    user_token: str


@app.post("/user/create", response_model=UserCreateResponse)
def user_create(req: UserCreateRequest):
    """新規ユーザー作成"""
    token = model.create_user(req.user_name, req.leader_card_id)
    return UserCreateResponse(user_token=token)


bearer = HTTPBearer()


def get_auth_token(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    assert cred is not None
    if not cred.credentials:
        raise HTTPException(status_code=401, detail="invalid credential")
    return cred.credentials


@app.get("/user/me", response_model=SafeUser)
def user_me(token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=404)
    # print(f"user_me({token=}, {user=})")
    return user


class Empty(BaseModel):
    pass


@app.post("/user/update", response_model=Empty)
def update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    # print(req)
    model.update_user(token, req.user_name, req.leader_card_id)
    return {}


class CreateRoomRequest(BaseModel):
    live_id: int
    select_difficulty: LiveDifficulty


class CreateRoomResponse(BaseModel):
    room_id: int


# -> 返り値の型
@app.post("/room/create", response_model=CreateRoomResponse)
def room_create(
    req: CreateRoomRequest, token: str = Depends(get_auth_token)
) -> CreateRoomResponse:
    # print(req)
    host = model.get_user_by_token(token)
    # print(host)
    # response_modelとreturn値の型を合わせる必要がある！
    return CreateRoomResponse(
        room_id=model.Room_create(host.id, req.live_id, req.select_difficulty.value)
    )


class RoomListRequest(BaseModel):
    live_id: int


class RoomListResponse(BaseModel):
    room_info_list: list[RoomInfo]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(req: RoomListRequest) -> RoomListResponse:
    # print(req)
    return RoomListResponse(room_info_list=model.Room_list(req.live_id))


class RoomJoinRequest(BaseModel):
    room_id: int
    select_difficulty: LiveDifficulty


class RoomJoinResponse(BaseModel):
    join_room_result: JoinRoomResult


@app.post("/room/join", response_model=RoomJoinResponse)
def room_join(
    req: RoomJoinRequest, token: str = Depends(get_auth_token)
) -> RoomJoinResponse:
    host = model.get_user_by_token(token)
    return RoomJoinResponse(
        join_room_result=model.Room_join(
            host.id, req.room_id, req.select_difficulty.value
        )
    )


class RoomID(BaseModel):
    room_id: int


@app.post("/room/wait", response_model=RoomWaitResponse)
def room_wait(req: RoomID, token: str = Depends(get_auth_token)) -> RoomWaitResponse:
    host = model.get_user_by_token(token)
    return model.Room_wait(host.id, req.room_id)


@app.post("/room/start", response_model=Empty)
def room_start(req: RoomID, token: str = Depends(get_auth_token)):
    host = model.get_user_by_token(token)
    model.Room_start(host.id, req.room_id)
    return {}


class RoomEndRequest(BaseModel):
    room_id: int
    score: int
    judge_count_list: list[int]


@app.post("/room/end", response_model=Empty)
def room_end(req: RoomEndRequest, token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    model.Room_end(user.id, req.room_id, req.score, req.judge_count_list)
    return {}


@app.post("/room/result", response_model=RoomResultResponse)
def room_result(req: RoomID) -> RoomResultResponse:
    return RoomResultResponse(result_user_list=model.Room_result(req.room_id))


@app.post("/room/leave", response_model=Empty)
def room_leave(req: RoomID, token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    model.Room_leave(user.id, req.room_id)
    return {}
