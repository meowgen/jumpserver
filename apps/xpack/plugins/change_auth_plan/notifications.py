from django.utils.translation import ugettext_lazy as _

from users.models import User
from common.tasks import send_mail_attachment_async


class PlanExecutionTaskMsg(object):
    subject = _('Notification of implementation result of encryption change plan')

    def __init__(self, name: str, user: User):
        self.name = name
        self.user = user

    @property
    def message(self):
        name = self.name
        if self.user.secret_key:
            return _('{} - The encryption change task has been completed. See the attachment for details').format(name)
        return _("{} - The encryption change task has been completed: the encryption password has not been set - "
                 "please go to personal information -> file encryption password to set the encryption password").format(name)

    def publish(self, attachments=None):
        send_mail_attachment_async.delay(
            self.subject, self.message, [self.user.email], attachments
        )
