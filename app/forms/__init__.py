""" Uhh... Here we import stuff """
from flask_wtf import FlaskForm

from .user import RegistrationForm, LoginForm, LogOutForm, PasswordResetForm
from .user import CreateUserMessageForm, EditUserForm, PasswordRecoveryForm
from .user import CreateUserMessageReplyForm, ResendConfirmationForm
from .user import EditAccountForm, DeleteAccountForm
from .sub import CreateSubForm, EditSubForm, EditSubTextPostForm, EditSubFlair, EditSubRule
from .sub import CreateSubPostForm, EditCommentForm
from .sub import PostComment, DeletePost, UndeletePost, EditSubLinkPostForm, SearchForm
from .sub import BanUserSubForm, EditPostFlair, EditSubCSSForm, EditMod2Form
from .sub import CreateSubFlair, DeleteSubFlair, VoteForm, DeleteCommentForm, CreateSubRule, DeleteSubRule
from .sub import UndeleteCommentForm, CreateReportNote, DistinguishForm
from .admin import EditModForm, EditBadgeForm, NewBadgeForm
from .admin import BanDomainForm, UseInviteCodeForm, AssignUserBadgeForm
from .admin import SecurityQuestionForm, TOTPForm, WikiForm
from .admin import CreateInviteCodeForm, UpdateInviteCodeForm


class DummyForm(FlaskForm):
    """ This is here only for the csrf token. """
    pass
