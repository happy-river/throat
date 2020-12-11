"""Peewee migrations -- 027_message_types.py

Modify the Message model to support more types of messages. Second of a set of two migrations.
"""

import datetime as dt
from enum import IntEnum
import peewee as pw
from decimal import ROUND_HALF_EVEN

try:
    import playhouse.postgres_ext as pw_pext
except ImportError:
    pass

SQL = pw.SQL


class MessageType(IntEnum):
    """Types of private messages.
    Value of the 'mtype' field in Message."""
    USER_TO_USER = 100
    USER_TO_MODS = 101
    MOD_TO_USER_AS_USER = 102
    MOD_TO_USER_AS_MOD = 103
    MOD_DISCUSSION = 104
    USER_BAN_APPEAL = 105
    MOD_NOTIFICATION = 106


class MessageStatus(IntEnum):
    """Statuses of private messages.
    Value of the 'sender_status' and 'receiver_status' fields in Message."""
    DEFAULT = 200  # Inbox for received messages and modmail and Sent for sent messages.
    SAVED = 201  # Called "Archived" in Modmail.
    TRASHED = 202  # User to user only.
    DELETED = 203  # User to user only.


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    Message = migrator.orm['message']

    if not fake:
        for msg in Message.select():
            old_mtype = msg.mtype
            msg.mtype = MessageType.USER_TO_USER
            if old_mtype == 9:
                msg.receiver_status = MessageStatus.SAVED
            elif old_mtype == 6:
                msg.receiver_status = MessageStatus.DELETED
            msg.save()

    migrator.remove_fields('message', 'read')


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""
    Message = migrator.orm['message']
    UserIgnores = migrator.orm['user_ignores']

    if not fake:
        for msg in Message.select():
            if msg.receiver_status == MessageStatus.SAVED:
                msg.mtype = 9
            elif msg.receiver_status == MessageStatus.DELETED:
                msg.mtype = 6
            else:
                msg.mtype = 1
            msg.save()

        for msg in Message.select().join(UserIgnores, pw.JOIN.RIGHT_OUTER, on=(
            (UserIgnores.uid == Message.receivedby) & (UserIgnores.target == Message.sentby))):
            msg.mtype = 41
            msg.save()

    migrator.add_fields('message', read=pw.DateTimeField(null=True))
