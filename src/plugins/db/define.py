from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped

from .base import Base


# Notice Manager
class NoticeMethod(Base):
    __tablename__ = 'notice_method'

    id: Mapped[int] = mapped_column(primary_key=True)

    # notice type
    type: Mapped[int]

    # destination the notice to be pushed to.
    dst: Mapped[str]

    def __repr__(self):
        return f"NoticeMethod(id={self.id!r}, type={self.type!r}, dst={self.dst!r})"


# Amazon Listener
class AmazonListenTarget(Base):
    __tablename__ = 'amazon_listen_target'

    id: Mapped[int] = mapped_column(primary_key=True)

    # User Type, may be private/group/channel or any other defined by module.
    type: Mapped[int]

    # should be integer but may be logger than 32-bit integer
    user_id: Mapped[str]

    # listened target
    target: Mapped[str]

    notice_id = mapped_column(ForeignKey(NoticeMethod.__tablename__ + '.id'))

    def __repr__(self):
        return f"AmazonListenTarget(id={self.id!r}, type={self.type!r}, user_id={self.user_id!r}, " \
               f"target={self.target!r}, notice_id={self.notice_id!r})"


class AmazonCommodity(Base):
    __tablename__ = 'amazon_commodity'

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str]

    # Timestamp
    addTime: Mapped[int]

    # Timestamp
    deleteTime: Mapped[int]

    def __repr__(self):
        return f"AmazonCommodity(id={self.id!r}, name={self.name!r}, addTime={self.addTime!r}, " \
               f"deleteTime={self.deleteTime!r})"
