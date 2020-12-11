"""Peewee migrations -- 026_message_statuses.py

Modify the Message model to separate message statuses for sender and
receiver, to support multiple receivers, and to support a future
implentation of modmail.  First of a set of two migrations.

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


class MessageStatus(IntEnum):
    """Statuses of private messages.
    Value of the 'sender_status' and 'receiver_status' field in Message."""
    DEFAULT = 200  # Inbox for received messages and modmail and Sent for sent messages.
    SAVED = 201  # Called "Archived" in Modmail.
    TRASHED = 202  # User to user only.
    DELETED = 203  # User to user only.


def migrate(migrator, database, fake=False, **kwargs):
    """Write your migrations here."""

    User = migrator.orm['user']
    Message = migrator.orm['message']
    Sub = migrator.orm['sub']

    @migrator.create_model
    class UserUnreadMessage(pw.Model):
        id = pw.AutoField()
        uid = pw.ForeignKeyField(db_column='uid', model=User, field='uid')
        mid = pw.ForeignKeyField(db_column='mid', model=Message, field='mid')

        class Meta:
            table_name = 'user_unread_message'

    migrator.add_fields('message', sender_status=pw.IntegerField(default=MessageStatus.DEFAULT))
    migrator.add_fields('message', receiver_status=pw.IntegerField(default=MessageStatus.DEFAULT))
    migrator.add_fields('message', reply_to=pw.ForeignKeyField(db_column='reply_to', null=True,
                                                               model='self', field='mid'))
    migrator.add_fields('message', sub=pw.ForeignKeyField(db_column='sid', null=True, model=Sub, field='sid'))
    migrator.add_fields('message', replies=pw.IntegerField(default=0))

    if not fake:
        UserUnreadMessage.create_table(True)
        for msg in Message.select(Message.mid, Message.receivedby).where(Message.read.is_null()):
            UserUnreadMessage.create(mid=msg.mid, uid=msg.receivedby)

    migrator.remove_fields('message', 'mlink')


def rollback(migrator, database, fake=False, **kwargs):
    """Write your rollback migrations here."""

    UserUnreadMessage = migrator.orm['user_unread_message']
    Message = migrator.orm['message']

    now = dt.datetime.utcnow()
    if not fake:
        for msg in (Message.select()
                    .join(UserUnreadMessage, pw.JOIN.LEFT_OUTER,
                          on=((UserUnreadMessage.mid == Message.mid) &
                              (UserUnreadMessage.uid == Message.receivedby)))
                    .where(UserUnreadMessage.mid.is_null())):
            msg.read = now
            msg.save()

    migrator.add_fields('message', mlink=pw.CharField(null=True))
    migrator.remove_fields('message', 'sender_status')
    migrator.remove_fields('message', 'receiver_status')
    migrator.remove_fields('message', 'reply_to')
    migrator.remove_fields('message', 'sub')
    migrator.remove_fields('message', 'replies')
    migrator.remove_model('user_unread_message')
