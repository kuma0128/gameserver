import json
import uuid
from enum import Enum, IntEnum
from typing import Optional
from unittest import result

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine


# Enumと構造体を定義
class LiveDifficulty(Enum):
    normal = 1
    hard = 2


class JoinRoomResult(Enum):
    Ok = 1
    RoomFull = 2
    Disbanded = 3
    OtherError = 4


class WaitRoomStatus(Enum):
    Waiting = 1
    LiveStart = 2
    Dissolution = 3


class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count: int
    max_user_count: int


class RoomUser(BaseModel):
    user_id: int
    name: str
    leader_card_id: int
    select_difficulty: LiveDifficulty
    is_me: bool
    is_host: bool


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: list[int]
    score: int


class InvalidToken(Exception):
    """指定されたtokenが不正だったときに投げる"""


class SafeUser(BaseModel):
    """token を含まないUser"""

    id: int
    name: str
    leader_card_id: int

    class Config:
        orm_mode = True


def create_user(name: str, leader_card_id: int) -> str:
    """Create new user and returns their token"""
    token = str(uuid.uuid4())
    # NOTE: tokenが衝突したらリトライする必要がある.
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `user` (name, token, leader_card_id) VALUES (:name, :token, :leader_card_id)"
            ),
            {"name": name, "token": token, "leader_card_id": leader_card_id},
        )
        # print(result)
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    result = conn.execute(
        text("SELECT `id`, `name`, `leader_card_id` FROM `user` WHERE `token`=:token"),
        dict(token=token),
    )
    try:
        row = result.one()
    except NoResultFound:
        return None
    return SafeUser.from_orm(row)


def get_user_by_token(token: str) -> Optional[SafeUser]:
    with engine.begin() as conn:
        return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
    # このコードを実装してもらう
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE `user` SET `name`=:name, `leader_card_id`=:leader_card_id WHERE `token`=:token"
            ),
            dict(name=name, leader_card_id=leader_card_id, token=token),
        )
    return


def Room_create(host_id: int, live_id: int, select_difficulty: int) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "insert into `room` (live_id, host_id, room_status, joined_user_count, max_user_count) values (:live_id, :host_id, 1, 1, 4)"
            ),
            {
                "live_id": live_id,
                "host_id": host_id,
            },
        )
        # print(result)
        # print(type(result))
        # row id取得（ここではroom_idに対応)
        try:
            room_id = result.lastrowid
        except NoResultFound:
            return None
        return room_id


def Room_list(live_id: int) -> list[RoomInfo]:
    if live_id == 0:
        with engine.begin() as conn:
            result = conn.execute(
                text("select * from `room`"),
            )
            try:
                rows = result.fetchall()
            except NoResultFound:
                return None
            res = list([])
            for row in rows:
                res.append(
                    RoomInfo(
                        room_id=row.room_id,
                        live_id=row.live_id,
                        joined_user_count=row.joined_user_count,
                        max_user_count=row.max_user_count,
                    )
                )
            return res
    else:
        with engine.begin() as conn:
            result = conn.execute(
                text("select * from `room` where `live_id`=:live_id"),
                dict(live_id=live_id),
            )
            try:
                rows = result.fetchall()
            except NoResultFound:
                return None
            res = list([])
            for row in rows:
                res.append(
                    RoomInfo(
                        room_id=row.room_id,
                        live_id=row.live_id,
                        joined_user_count=row.joined_user_count,
                        max_user_count=row.max_user_count,
                    )
                )
            return res
