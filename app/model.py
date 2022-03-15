import json
import uuid
from enum import Enum, IntEnum
from typing import Optional
from unittest import result

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import false, text, true
from sqlalchemy.exc import NoResultFound

from .db import engine

# from app.api import RoomResultResponse


# from app.api import RoomWaitResponse


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


def Room_join(user_id: int, room_id: int, select_difficulty: int) -> JoinRoomResult:
    with engine.begin() as conn:
        result = conn.execute(
            text("select * from `room` where `room_id`=:room_id"), dict(room_id=room_id)
        )
        row = result.one()
        try:
            res = row.room_status
        except NoResultFound:
            conn.execute(text("commit"))
            return JoinRoomResult(4)
        if res == 1:
            conn.execute(
                text(
                    "insert into `room_member` set `room_id`=:room_id, `user_id`=:user_id, `difficulty`=:select_difficulty"
                ),
                dict(
                    room_id=room_id,
                    user_id=user_id,
                    select_difficulty=select_difficulty,
                ),
            )
            conn.execute(
                text(
                    "update `room` set `joined_user_count` = `joined_user_count` + 1 where `room_id`=:room_id"
                ),
                dict(room_id=room_id),
            )
            # try:
            #     row = result2.room_id
            # except NoResultFound:
            #     return None
            return JoinRoomResult(1)
        if res == 2:
            conn.execute(text("commit"))
            return JoinRoomResult(2)
        if res == 3:
            conn.execute(text("commit"))
            return JoinRoomResult(3)


class RoomWaitResponse(BaseModel):
    status: WaitRoomStatus
    room_user_list: list[RoomUser]


def Room_wait(user_id: int, room_id: int) -> RoomWaitResponse:
    with engine.begin() as conn:
        result1 = conn.execute(
            text("select * from `room_member` where `room_id` =:room_id"),
            dict(room_id=room_id),
        )
        row1 = result1.fetchall()
        res = list([])
        result3 = conn.execute(
            text("select * from `room` where `room_id` =:room_id"),
            dict(room_id=room_id),
        )
        row3 = result3.one()
        res3 = row3.room_status
        for row in row1:
            result2 = conn.execute(
                text("select * from `user` where `id` =:user_id"),
                dict(user_id=row.user_id),
            )
            row2 = result2.one()

            if row3.host_id == user_id:
                hostf = 1
            else:
                hostf = 0
            if row.user_id == user_id:
                qryf = 1
            else:
                qryf = 0

            res.append(
                RoomUser(
                    user_id=row.user_id,
                    name=row2.name,
                    leader_card_id=row2.leader_card_id,
                    select_difficulty=row.difficulty,
                    is_me=qryf,
                    is_host=hostf,
                )
            )

        return RoomWaitResponse(status=res3, room_user_list=res)


def Room_start(user_id: int, room_id: int) -> None:
    with engine.begin() as conn:
        result = conn.execute(
            text("select * from `room` where `room_id`=:room_id"),
            dict(room_id=room_id),
        )
        row = result.one()
        host = row.host_id
        if host == user_id:
            conn.execute(text("update `room` set `room_status`=2"))
    return


def Room_end(user_id: int, room_id: int, score: int, judge: list[int]) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "update `room_member` set `score`=:score, `perfect`=:perfect, `great`=:great, `good`=:good, `bad`=:bad, `miss`=:miss where `room_id`=:room_id AND `user_id`=:user_id"
            ),
            dict(
                score=score,
                room_id=room_id,
                user_id=user_id,
                perfect=judge[0],
                great=judge[1],
                good=judge[2],
                bad=judge[3],
                miss=judge[4],
            ),
        )

    return


class RoomResultResponse(BaseModel):
    result_user_list: list[ResultUser]


def Room_result(room_id: int) -> list[ResultUser]:
    with engine.begin() as conn:
        result = conn.execute(
            text("select * from `room_member` where `room_id`=:room_id"),
            dict(room_id=room_id),
        )
        rows = result.fetchall()
        res = list([])
        for row in rows:
            res.append(
                ResultUser(
                    user_id=row.user_id,
                    judge_count_list=list(
                        [row.perfect, row.great, row.good, row.bad, row.miss]
                    ),
                    score=row.score,
                )
            )
    return res
