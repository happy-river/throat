""" Database table definitions """

import datetime
import uuid
from urllib.parse import urlparse
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user
import bcrypt
from .caching import CacheableMixin, query_callable, regions, cache


db = SQLAlchemy()


class User(db.Model, CacheableMixin):
    """ Basic user data (Used for login or password recovery) """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'uid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    uid = Column(String(40), primary_key=True)
    name = Column(String(64), unique=True)
    email = Column(String(128))
    # In case we migrate to a different cipher for passwords
    # 1 = bcrypt
    crypto = Column(Integer)
    password = Column(String(255))
    # Account status
    # 0 = OK; 1 = banned; 2 = shadowbanned?; 3 = sent to oblivion?
    status = Column(Integer)
    joindate = Column(DateTime)

    score = Column(Integer)  # The user's score
    subscribed = db.relationship('SubSubscriber', backref='user',
                                 lazy='dynamic')
    posts = db.relationship('SubPost', backref='_user', lazy='dynamic')

    properties = db.relationship('UserMetadata',
                                 backref='user', lazy='dynamic')
    comments = db.relationship('SubPostComment', backref='user',
                               lazy='dynamic')

    def __init__(self, username, email, password):
        self.uid = str(uuid.uuid4())
        self.name = username
        self.email = email
        self.crypto = 1
        self.status = 0
        self.joindate = datetime.datetime.utcnow()
        self.setPassword(password)

    def setPassword(self, password):
        password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        if isinstance(password, bytes):
            self.password = password.decode('utf-8')
        else:
            self.password = password

    def isPasswordCorrect(self, password):
        if self.crypto == 1:  # bcrypt
            thash = bcrypt.hashpw(password.encode('utf-8'),
                                  self.password.encode('utf-8'))
            if thash == self.password.encode('utf-8'):
                return True
        return False

    def __repr__(self):
        return '<User %r>' % self.name

    @hybrid_property
    @cache.memoize(20)
    def showLinksNewTab(self):
        """ Returns true user selects to open links in a new window """
        x = UserMetadata.query.filter_by(key='exlinks', uid=self.uid).first()
        if x:
            return bool(int(x.value))
        return False

    @hybrid_property
    @cache.memoize(20)
    def showStyles(self):
        """ Returns true user selects to see sustom sub stylesheets """
        x = UserMetadata.query.filter_by(key='styles', uid=self.uid).first()
        if x:
            return bool(int(x.value))
        return False

    @hybrid_property
    @cache.memoize(20)
    def showNSFW(self):
        """ Returns true user selects to see sustom sub stylesheets """
        x = UserMetadata.query.filter_by(key='nsfw', uid=self.uid).first()
        if x:
            return bool(int(x.value))
        return True




class UserMetadata(db.Model, CacheableMixin):
    """ User metadata. Here we store badges, admin status, etc. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    cache_pk = 'xid'
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    uid = Column(String(40), db.ForeignKey('user.uid'))  # Subverse id
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    def __init__(self, uid, key, value):
        self.uid = uid
        self.key = key
        self.value = value

    @hybrid_property
    def getBadgeClass(self):
        """ Returns the badge's css class """
        if self.key != "badge":
            return False
        x = UserBadge.query.get(self.value)
        return str(x.badge)

    @hybrid_property
    def getBadgeName(self):
        """ Returns the badge's name """
        if self.key != "badge":
            return False
        x = UserBadge.query.get(self.value)
        return str(x.name)

    @hybrid_property
    def getBadgeText(self):
        """ Returns the badge's hover text """
        if self.key != "badge":
            return False
        x = UserBadge.query.get(self.value)
        return str(x.text)


class UserBadge(db.Model):
    """ Here we store badge definitions """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    bid = Column(String(40), primary_key=True)
    badge = Column(String(255))  # fa-xxx, badge icon id.
    name = Column(String(255))  # Badge name
    # Short text displayed when hovering the badge
    text = Column(String(255))

    def __init__(self, badge, name, text):
        self.bid = str(uuid.uuid4())
        self.badge = badge
        self.name = name
        self.text = text


class Sub(db.Model):
    """ Basic sub data """

    sid = Column(String(40), primary_key=True)  # sub id
    name = Column(String(32), unique=True)  # sub name
    title = Column(String(128))  # sub title/desc

    status = Column(Integer)  # Sub status. 0 = ok; 1 = banned; etc

    sidebar = Column(Text)

    nsfw = Column(Integer)  # nsfw = 1

    subscribers = db.relationship('SubSubscriber', backref='sub',
                                  lazy='dynamic')
    _posts = db.relationship('SubPost', backref='__sub', lazy='joined')
    __posts = db.relationship('SubPost', backref='_sub', lazy='dynamic')
    properties = db.relationship('SubMetadata', backref='sub', lazy='dynamic')
    flairs = db.relationship('SubFlair', backref='sub', lazy='dynamic')
    __stylesheet = db.relationship('SubStylesheet', backref='sub',
                                   lazy='dynamic')

    def __init__(self, name, title):
        self.sid = str(uuid.uuid4())
        self.name = name
        self.sidebar = ''
        self.title = title

    def __repr__(self):
        return '<Sub {0}-{1}>'.format(self.name, self.title)

    @hybrid_property
    def posts(self):
        """ gets posts from sub, replaces the db relationship """
        return SubPost.query.filter_by(sid=self.sid)

    @hybrid_property
    def stylesheet(self):
        """ gets stylesheet from sub, replaces the db relationship """
        return SubStylesheet.query.filter_by(sid=self.sid).first()

    @cache.memoize(30)
    def isNSFW(self):
        """ returns true if sub is nsfw """
        if self.nsfw is None:
            nsfw = SubMetadata.query.filter_by(sid=self.sid,
                                               key='nsfw').first()
            if nsfw:
                self.nsfw = int(nsfw.value)
            else:
                self.nsfw = 0
            db.session.commit()
        return self.nsfw


class SubFlair(db.Model, CacheableMixin):
    """ Stores all the flairs for all da subs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # Subverse id
    text = Column(String(64))


class SubMetadata(db.Model, CacheableMixin):
    """ Sub metadata. Here we store if the sub is nsfw, the modlist,
    the founder, etc. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    cache_pk = 'xid'
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # Subverse id
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    def __init__(self, sub, key, value):
        self.sid = sub.sid
        self.key = key
        self.value = value

    @hybrid_property
    def getUsername(self):
        """ Returns username from str """
        x = User.query.get(self.value)
        return x.name

    @hybrid_property
    def getSubName(self):
        """ Returns the sub's name from str """
        x = Sub.query.get(self.sid)
        return str(x.name)


class SubSubscriber(db.Model, CacheableMixin):
    """ Stores subscribers for a sub. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    status = Column(Integer)  # 1=subscribed 2=blocked 3=custom
    time = Column(DateTime)
    order = Column(Integer)  # Order in the subs bar.

    def __init__(self, sid, uid, status):
        self.time = datetime.datetime.utcnow()
        self.sid = sid
        self.uid = uid
        self.status = status

    @hybrid_property
    def getSubName(self):
        """ Returns the sub's name from str """
        x = Sub.query.get(self.sid)
        return str(x.name)

    @hybrid_property
    def name(self):
        return self.getSubName


class SubStylesheet(db.Model, CacheableMixin):
    """ Stores sub's custom CSS """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # Subverse id
    content = Column(Text)

    def __init__(self, sub, content):
        self.sid = sub.sid
        self.content = content


class SubPost(db.Model):
    """ Represents a post on a sub """
    pid = Column(Integer, primary_key=True)  # post id
    sid = Column(String(40), db.ForeignKey('sub.sid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))

    # There's a 'sub' field with a reference to the sub and a 'user' one
    # with a refernece to the user that created this post

    title = Column(String(512))  # post title
    link = Column(String(256))  # post target (if it is a link post)
    # post content (if it is a text post)
    content = Column(Text())

    posted = Column(DateTime)

    ptype = Column(Integer)  # Post type. 0=txt; 1=link; etc

    score = Column(Integer)  # Post score
    thumbnail = Column(String(128))  # Thumbnail filename

    deleted = Column(Integer)  # Deletion status. 1=user, 2=mod, etc
    nsfw = Column(Integer)  # nsfw. 1=nsfw, 2=???!

    properties = db.relationship('SubPostMetadata',
                                 backref='post', lazy='dynamic')

    comments = db.relationship('SubPostComment', backref='post',
                               lazy='dynamic')

    votes = db.relationship('SubPostVote', backref='post',
                            lazy='subquery')

    def __init__(self, sid):
        self.sid = sid
        self.score = 1
        self.deleted = 0
        self.nsfw = 0
        self.thumbnail = ''
        self.uid = current_user.get_id()
        self.posted = datetime.datetime.utcnow()
        if current_user.user.score is not None:
            current_user.user.score = User.score + 1
            db.session.add(current_user.user)

    def __repr__(self):
        return "<SubPost {0}>".format(self.pid)

    def wasDeleted(self):
        """ Returns post deletion status """
        # XXX: compatibility code
        if self.deleted is None:
            del1 = SubPostMetadata.query.filter_by(key='deleted',
                                                   pid=self.pid).first()
            if del1:
                self.deleted = 1
            else:
                del2 = SubPostMetadata.query.filter_by(key='moddeleted',
                                                       pid=self.pid).first()
                if del2:
                    self.deleted = 1
                else:
                    self.deleted = 0
            db.session.commit()
        return self.deleted

    @cache.memoize(30)
    def is_sticky(self):
        """ Returns True if this post is stickied """
        x = SubMetadata.query.filter_by(key='sticky', sid=self.sid,
                                        value=self.pid).first()
        return bool(x)

    @cache.memoize(5)
    def voteCount(self):
        """ Returns the post's vote count """
        if self.score is None:  # Compat code
            votes = SubPostMetadata.query.filter_by(key='score', pid=self.pid)
            if votes.first():
                self.score = votes.value
            else:
                self.score = 1
            db.session.commit()
        return self.score

    def getComments(self, parent=None):
        """ Returns cached post comments """
        comms = SubPostComment.query.filter_by(pid=self.pid, parentcid=parent)
        comms = list(comms)
        return comms

    def getCommentCount(self):
        c = SubPostComment.query.filter(SubPostComment.pid == self.pid).count()
        return c

    @cache.memoize(300)
    def getDomain(self):
        """ Gets Domain """
        x = urlparse(self.link)
        return x.netloc

    @hybrid_property
    @cache.memoize(600)
    def sub(self):
        """ Returns post's sub, replaces db relationship """
        return Sub.query.get(self.sid)

    @hybrid_property
    @cache.memoize(600)
    def user(self):
        """ Returns post's sub, replaces db relationship """
        return User.query.get(self.uid)

    @cache.memoize(300)
    def getThumbnail(self):
        """ Returns thumbnail address for post """
        if self.thumbnail is None:  # Compat code
            thumb = SubPostMetadata.query.filter_by(key='thumbnail',
                                                    pid=self.pid).first()
            if thumb:
                self.thumbnail = thumb.value
            else:
                self.thumbnail = ''
            db.session.commit()
        return self.thumbnail

    @cache.memoize(300)
    def isImage(self):
        """ Returns True if link ends with img suffix """
        suffix = ('.png', '.jpg', '.gif', '.tiff', '.bmp')
        return self.link.lower().endswith(suffix)

    @cache.memoize(300)
    def isGifv(self):
        """ Returns True if link ends with video suffix """
        domains = ['imgur.com', 'i.imgur.com', 'i.sli.mg', 'sli.mg']
        if self.link.lower().endswith('.gifv'):
            for domain in domains:
                if domain in self.link.lower():
                    return True
        else:
            return False

    @cache.memoize(300)
    def isVideo(self):
        """ Returns True if link ends with video suffix """
        suffix = ('.mp4', '.webm')
        return self.link.lower().endswith(suffix)

    @cache.memoize(600)
    def isAnnouncement(self):
        """ Returns True if post is an announcement """
        ann = SiteMetadata.query.filter_by(key='announcement').first()
        if ann:
            return ann.value == str(self.pid)
        return False

    @cache.memoize(30)
    def isPostNSFW(self):
        """ Returns true if the post is marked as NSFW """
        if self.nsfw is None:  # Compat code
            nsfw = SubPostMetadata.query.filter_by(key='nsfw',
                                                   pid=self.pid).first()
            if nsfw:
                self.nsfw = nsfw.value
            else:
                self.nsfw = 0
            db.session.commit()
        return bool(self.nsfw)


class SubPostMetadata(db.Model, CacheableMixin):
    """ Post metadata. Here we store if it is a sticky post, mod post, tagged
    as nsfw, etc. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    key = Column(String(255))  # Metadata key
    value = Column(String(255))

    def __init__(self, pid, key, value):
        self.pid = pid
        self.key = key
        self.value = value

    def __repr__(self):
        return '<SubPostMetadata ({0}); {1} = {2}>'.format(self.pid, self.key,
                                                           self.value)


class SubPostComment(db.Model, CacheableMixin):
    """ A comment. In a post. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    cache_pk = 'cid'
    query_class = query_callable(regions)

    cid = Column(String(64), primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    time = Column(DateTime)
    lastedit = Column(DateTime)
    content = Column(Text())
    status = Column(Integer)  # 1 = deleted

    score = Column(Integer)
    # parent comment id
    parentcid = Column(String(40), db.ForeignKey('sub_post_comment.cid'),
                       nullable=True)
    children = db.relationship("SubPostComment",
                               backref=db.backref("parent", remote_side=cid))

    def __init__(self):
        self.cid = str(uuid.uuid4())

    @hybrid_property
    def getUname(self):
        """ Returns username from str """
        x = User.query.filter_by(uid=self.uid).first()
        return str(x.name)

    @hybrid_property
    def deleted(self):
        return True if self.status == 1 else False

    def getScore(self):
        return self.score if self.score else 0


class SubPostCommentVote(db.Model, CacheableMixin):
    """ A comment. In a post. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    cache_pk = 'xid'
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    cid = Column(String(64))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    positive = Column(Boolean)
    datetime = Column(DateTime)


class SubPostVote(db.Model, CacheableMixin):
    """ Up/Downvotes in a post. """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    pid = Column(Integer, db.ForeignKey('sub_post.pid'))
    uid = Column(String(40), db.ForeignKey('user.uid'))
    positive = Column(Boolean)
    datetime = Column(DateTime)

    @hybrid_property
    def getUsername(self):
        """ Returns username from str """
        x = User.query.get(self.uid)
        return x.name


class Message(db.Model, CacheableMixin):
    """ Represents a post on a sub """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'mid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    mid = Column(Integer, primary_key=True)  # msg id
    sentby = Column(String(40), db.ForeignKey('user.uid'))
    receivedby = Column(String(40), db.ForeignKey('user.uid'))

    subject = Column(String(550))  # msg subject
    content = Column(Text())  # msg content

    posted = Column(DateTime)  # sent
    read = Column(DateTime)  # todo markasread time
    # mtype: 1=pm, 2=mods/subs, 3=user mention, 4=postreply, 5=commreply, 6=del
    # 7=sub bans, 8=tagging notifications
    mtype = Column(Integer)
    mlink = Column(String(128))  # link to be included

    def __repr__(self):
        return '<Messages {0}>'.format(self.subject)

    @hybrid_property
    def getMsgSentBy(self):
        """ Returns this message's sender. """
        x = User.query.filter_by(uid=self.sentby).first()
        return str(x.name)

    @hybrid_property
    def getMsgRecBy(self):
        """ Returns this message's recipient """
        x = User.query.filter_by(uid=self.receivedby).first()
        return str(x.name)


class SiteMetadata(db.Model, CacheableMixin):
    """ Site-wide configs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    cache_pk = 'xid'
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)
    key = Column(String(255))  # Metadata key
    value = Column(String(255))


class SubLog(db.Model):
    """ Sub modlogs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    lid = Column(Integer, primary_key=True)  # log id
    sid = Column(String(40), db.ForeignKey('sub.sid'))  # sub.sid
    time = Column(DateTime)
    # 1 = deletion, 2 = user ban, 3 = flair, 4 = modedit, 5 = comment, 6 = mods
    action = Column(Integer)
    desc = Column(String(255))  # description
    link = Column(String(255))

    def __init__(self, sid):
        self.sid = sid
        self.time = datetime.datetime.utcnow()


class SiteLog(db.Model):
    """ Sub modlogs """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    lid = Column(Integer, primary_key=True)  # log id
    time = Column(DateTime)
    # 1 deletion, 2 users, 3 ann, 4 subs, 5 mods/admins
    action = Column(Integer)
    desc = Column(String(255))  # description
    link = Column(String(255))


class UserMulti(db.Model):
    """ User Multi sub lists """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    mid = Column(Integer, primary_key=True)  # multi id
    uid = Column(String(40), db.ForeignKey('user.uid'))
    name = Column(String(40))
    subs = Column(String(255))  # sub+sub+sub
    sids = Column(Text)


class LiveChat(db.Model):
    """ /live chat v1 """
    cache_label = "default"  # region's label to use
    cache_regions = regions  # regions to store cache
    # Query handeling dogpile caching
    query_class = query_callable(regions)

    xid = Column(Integer, primary_key=True)  # chat message id
    username = Column(String(64))  # so it doesnt need to get every msg
    message = Column(String(255))


# OAuth stuff

class Client(db.Model):
    name = Column(String(40))

    # creator of the client, not required
    user_id = Column(db.ForeignKey('user.uid'))
    # required if you need to support client credential
    user = db.relationship('User')

    client_id = db.Column(String(40), primary_key=True)
    client_secret = db.Column(db.String(55), unique=True, index=True,
                              nullable=False)

    # public or confidential
    is_confidential = db.Column(db.Boolean)

    _redirect_uris = db.Column(db.Text)
    _default_scopes = db.Column(db.Text)

    @property
    def client_type(self):
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes.split()
        return []


class Grant(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        String(40), db.ForeignKey('user.uid')
    )
    user = db.relationship('User')

    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')

    code = db.Column(db.String(255), index=True, nullable=False)

    redirect_uri = db.Column(db.String(255))
    expires = db.Column(db.DateTime)

    _scopes = db.Column(db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')

    user_id = db.Column(
        String(40), db.ForeignKey('user.uid')
    )
    user = db.relationship('User')

    # currently only bearer is supported
    token_type = db.Column(db.String(40))

    access_token = db.Column(db.String(255), unique=True)
    refresh_token = db.Column(db.String(255), unique=True)
    expires = db.Column(db.DateTime)
    _scopes = db.Column(db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []
