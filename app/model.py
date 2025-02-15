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


MAX_USER_COUNT = 4


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
                "INSERT INTO `user` SET `name`=:name, `token`=:token, `leader_card_id`=:leader_card_id"
            ),
            dict(
                name=name,
                token=token,
                leader_card_id=leader_card_id,
            ),
        )
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    result = conn.execute(
        text(
            "SELECT u.`id`, u.`name`, u.`leader_card_id` FROM `user` u WHERE u.`token`=:token"
        ),
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
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE `user` u SET u.`name`=:name, u.`leader_card_id`=:leader_card_id WHERE u.`token`=:token"
            ),
            dict(name=name, leader_card_id=leader_card_id, token=token),
        )
    return


def Room_create(host_id: int, live_id: int, select_difficulty: int) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `room` SET `live_id`=:live_id, `host_id`=:host_id, `room_status`=:room_status, `joined_user_count` = 1, `max_user_count`=:MAX_USER_COUNT"
            ),
            dict(
                live_id=live_id,
                host_id=host_id,
                room_status=JoinRoomResult.Ok.value,
                MAX_USER_COUNT=MAX_USER_COUNT,
            ),
        )
        # row id取得（ここではroom_idに対応)
        room_id = result.lastrowid
        conn.execute(
            text(
                "INSERT INTO `room_member` SET `room_id`=:room_id, `user_id`=:user_id, `difficulty`=:select_difficulty"
            ),
            dict(
                room_id=room_id,
                user_id=host_id,
                select_difficulty=select_difficulty,
            ),
        )
        return room_id


def Room_list(live_id: int) -> list[RoomInfo]:
    with engine.begin() as conn:
        if live_id == 0:
            result = conn.execute(
                text(
                    "SELECT r.`room_id`, r.`live_id`, r.`joined_user_count`, r.`max_user_count` FROM `room` r WHERE r.`room_status`=:room_status AND r.`joined_user_count` < r.`max_user_count`"
                ),
                dict(room_status=JoinRoomResult.Ok.value),
            )
        else:
            result = conn.execute(
                text(
                    "SELECT r.`room_id`, r.`live_id`, r.`joined_user_count`, r.`max_user_count` FROM `room` r WHERE r.`room_status`=:room_status AND (r.`live_id`=:live_id AND r.`joined_user_count` < r.`max_user_count`)"
                ),
                dict(live_id=live_id, room_status=JoinRoomResult.Ok.value),
            )
    rows = result.fetchall()
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
            text(
                "SELECT r.`room_status`, r.`max_user_count`, r.`joined_user_count` FROM `room` r WHERE r.`room_id`=:room_id FOR UPDATE"
            ),
            dict(room_id=room_id),
        )
        row = result.one()
        status = row.room_status
        if status is None:
            return JoinRoomResult(4)
        if (row.joined_user_count == row.max_user_count) or (
            status == WaitRoomStatus.LiveStart.value
        ):
            return JoinRoomResult(2)
        if (row.joined_user_count == 0) or (status == WaitRoomStatus.Dissolution.value):
            return JoinRoomResult(3)
        if status == WaitRoomStatus.Waiting.value:
            conn.execute(
                text(
                    "INSERT INTO `room_member` SET `room_id`=:room_id, `user_id`=:user_id, `difficulty`=:select_difficulty"
                ),
                dict(
                    room_id=room_id,
                    user_id=user_id,
                    select_difficulty=select_difficulty,
                ),
            )
            conn.execute(
                text(
                    "UPDATE `room` r SET r.`joined_user_count` = r.`joined_user_count` + 1 WHERE r.`room_id`=:room_id"
                ),
                dict(room_id=room_id),
            )
            # conn.execute(text("commit"))
            # update文はすぐ更新されるのと上でfor updateしているからトランザクション続けておｋ
            count_check = conn.execute(
                text(
                    "SELECT r.`joined_user_count` FROM `room` r WHERE r.`room_id`=:room_id"
                ),
                dict(room_id=room_id),
            )
            if count_check == row.max_user_count:
                conn.execute(
                    text(
                        "UPDATE `room` r SET r.`room_status`=:room_status WHERE r.`room_id`=:room_id"
                    ),
                    dict(room_id=room_id, room_status=JoinRoomResult.RoomFull.value),
                )
            return JoinRoomResult(1)


class RoomWaitResponse(BaseModel):
    status: WaitRoomStatus
    room_user_list: list[RoomUser]


def Room_wait(user_id: int, room_id: int) -> RoomWaitResponse:
    with engine.begin() as conn:
        result1 = conn.execute(
            text(
                "SELECT rm.`user_id`, rm.`difficulty` FROM `room_member` rm WHERE rm.`room_id` =:room_id"
            ),
            dict(room_id=room_id),
        )
        row1 = result1.fetchall()
        res = list([])
        result3 = conn.execute(
            text(
                "SELECT r.`host_id`, r.`room_status` FROM `room` r WHERE r.`room_id` =:room_id"
            ),
            dict(room_id=room_id),
        )
        row3 = result3.one()
        res3 = row3.room_status
        for row in row1:
            result2 = conn.execute(
                text(
                    "SELECT u.`name`, u.`leader_card_id` FROM `user` u WHERE u.`id` =:user_id"
                ),
                dict(user_id=row.user_id),
            )
            row2 = result2.one()

            if row3.host_id == row.user_id:
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
            text("SELECT r.`host_id` FROM `room` r WHERE r.`room_id`=:room_id"),
            dict(room_id=room_id),
        )
        row = result.one()
        host = row.host_id
        if host == user_id:
            conn.execute(
                text(
                    "UPDATE `room` r SET r.`room_status`=:room_status WHERE r.`room_id`=:room_id"
                ),
                dict(room_id=room_id, room_status=JoinRoomResult.RoomFull.value),
            )
    return


def Room_end(user_id: int, room_id: int, score: int, judge: list[int]) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE `room_member` rm SET rm.`score`=:score, rm.`perfect`=:perfect, rm.`great`=:great, rm.`good`=:good, rm.`bad`=:bad, rm.`miss`=:miss WHERE rm.`room_id`=:room_id AND rm.`user_id`=:user_id"
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
        nullcheck = conn.execute(
            text(
                "SELECT rm.`room_id` FROM `room_member` rm WHERE rm.`room_id`=:room_id AND rm.`score` IS NULL"
            ),
            dict(room_id=room_id),
        )
        try:
            nullcheck.one()
        except:
            pass
        else:
            return list([])
        result = conn.execute(
            text(
                "SELECT rm.`user_id`, rm.`score`, rm.`perfect`, rm.`great`, rm.`good`, rm.`bad`, rm.`miss` FROM `room_member` rm WHERE rm.`room_id`=:room_id"
            ),
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


def Room_leave(user_id: int, room_id: int) -> None:
    with engine.begin() as conn:
        counts = conn.execute(
            text(
                "SELECT r.`joined_user_count` FROM `room` r WHERE r.`room_id`=:room_id"
            ),
            dict(room_id=room_id),
        )
        row = counts.one()
        conn.execute(
            text(
                "DELETE FROM `room_member` rm WHERE rm.`room_id`=:room_id AND rm.`user_id`=:user_id"
            ),
            dict(room_id=room_id, user_id=user_id),
        )
        host = conn.execute(
            text("SELECT r.`host_id` FROM `room` r WHERE r.`room_id`=:room_id"),
            dict(room_id=room_id),
        )
        if host.one() == user_id:
            conn.execute(
                text("UPDATE `room` r SET r.`room_status`=:room_status"),
                dict(room_status=JoinRoomResult.Disbanded.value),
            )
        if row == 1:
            conn.execute(
                text("DELETE FROM `room` r WHERE r.`room_id`=:room_id"),
                dict(room_id=room_id),
            )
        else:
            conn.execute(
                text(
                    "UPDATE `room` r SET r.`joined_user_count` = r.`joined_user_count` - 1 WHERE r.`room_id`=:room_id"
                ),
                dict(room_id=room_id),
            )
    return
