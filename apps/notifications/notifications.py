import traceback
from html2text import HTML2Text
from typing import Iterable
from itertools import chain
import textwrap

from celery import shared_task
from django.utils.translation import gettext_lazy as _

from common.utils.timezone import local_now
from common.utils import lazyproperty
from settings.utils import get_login_title
from users.models import User
from notifications.backends import BACKEND
from .models import SystemMsgSubscription, UserMsgSubscription

__all__ = ('SystemMessage', 'UserMessage', 'system_msgs', 'Message')


system_msgs = []
user_msgs = []


class MessageType(type):
    def __new__(cls, name, bases, attrs: dict):
        clz = type.__new__(cls, name, bases, attrs)

        if 'message_type_label' in attrs \
                and 'category' in attrs \
                and 'category_label' in attrs:
            message_type = clz.get_message_type()

            msg = {
                'message_type': message_type,
                'message_type_label': attrs['message_type_label'],
                'category': attrs['category'],
                'category_label': attrs['category_label'],
            }
            if issubclass(clz, SystemMessage):
                system_msgs.append(msg)
            elif issubclass(clz, UserMessage):
                user_msgs.append(msg)

        return clz


@shared_task
def publish_task(msg):
    msg.publish()


class Message(metaclass=MessageType):
    message_type_label: str
    category: str
    category_label: str
    text_msg_ignore_links = True

    @classmethod
    def get_message_type(cls):
        return cls.__name__

    def publish_async(self):
        return publish_task.delay(self)

    @classmethod
    def gen_test_msg(cls):
        raise NotImplementedError

    def publish(self):
        raise NotImplementedError

    def send_msg(self, users: Iterable, backends: Iterable = BACKEND):
        backends = set(backends)
        backends.add(BACKEND.SITE_MSG)

        for backend in backends:
            try:
                backend = BACKEND(backend)
                if not backend.is_enable:
                    continue
                get_msg_method = getattr(self, f'get_{backend}_msg', self.get_common_msg)
                msg = get_msg_method()
                client = backend.client()
                client.send_msg(users, **msg)
            except NotImplementedError:
                continue
            except:
                traceback.print_exc()

    @classmethod
    def send_test_msg(cls):
        msg = cls.gen_test_msg()
        if not msg:
            return

        from users.models import User
        users = User.objects.filter(username='admin')
        backends = []
        msg.send_msg(users, backends)

    @staticmethod
    def get_common_msg() -> dict:
        return {'subject': '', 'message': ''}

    def get_html_msg(self) -> dict:
        return self.get_common_msg()

    def get_markdown_msg(self) -> dict:
        h = HTML2Text()
        h.body_width = 300
        msg = self.get_html_msg()
        content = msg['message']
        msg['message'] = h.handle(content)
        return msg

    def get_text_msg(self) -> dict:
        h = HTML2Text()
        h.body_width = 90
        msg = self.get_html_msg()
        content = msg['message']
        h.ignore_links = self.text_msg_ignore_links
        msg['message'] = h.handle(content)
        return msg

    @lazyproperty
    def common_msg(self) -> dict:
        return self.get_common_msg()

    @lazyproperty
    def text_msg(self) -> dict:
        msg = self.get_text_msg()
        return msg

    @lazyproperty
    def markdown_msg(self):
        return self.get_markdown_msg()

    @lazyproperty
    def html_msg(self) -> dict:
        msg = self.get_html_msg()
        return msg

    @lazyproperty
    def html_msg_with_sign(self):
        msg = self.get_html_msg()
        msg['message'] = textwrap.dedent("""
        {}
        <small>
        <br />
        ???
        <br />
        {}
        </small>
        """).format(msg['message'], self.signature)
        return msg

    @lazyproperty
    def text_msg_with_sign(self):
        msg = self.get_text_msg()
        msg['message'] = textwrap.dedent("""
        {}
        ???
        {}
        """).format(msg['message'], self.signature)
        return msg

    @lazyproperty
    def signature(self):
        return get_login_title()

    def get_email_msg(self) -> dict:
        return self.html_msg_with_sign

    def get_site_msg_msg(self) -> dict:
        return self.html_msg

    @classmethod
    def get_all_sub_messages(cls):
        def get_subclasses(cls):
            """returns all subclasses of argument, cls"""
            if issubclass(cls, type):
                subclasses = cls.__subclasses__(cls)
            else:
                subclasses = cls.__subclasses__()
            for subclass in subclasses:
                subclasses.extend(get_subclasses(subclass))
            return subclasses

        messages_cls = get_subclasses(cls)
        return messages_cls

    @classmethod
    def test_all_messages(cls):
        messages_cls = cls.get_all_sub_messages()

        for _cls in messages_cls:
            try:
                _cls.send_test_msg()
            except NotImplementedError:
                continue


class SystemMessage(Message):
    def publish(self):
        subscription = SystemMsgSubscription.objects.get(
            message_type=self.get_message_type()
        )

        receive_backends = subscription.receive_backends
        receive_backends = BACKEND.filter_enable_backends(receive_backends)

        users = [
            *subscription.users.all(),
            *chain(*[g.users.all() for g in subscription.groups.all()])
        ]
        self.send_msg(users, receive_backends)

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        pass

    @classmethod
    def gen_test_msg(cls):
        raise NotImplementedError


class UserMessage(Message):
    user: User

    def __init__(self, user):
        self.user = user

    def publish(self):
        sub = UserMsgSubscription.objects.get(user=self.user)
        self.send_msg([self.user], sub.receive_backends)

    @classmethod
    def get_test_user(cls):
        from users.models import User
        return User.objects.all().first()

    @classmethod
    def gen_test_msg(cls):
        raise NotImplementedError
