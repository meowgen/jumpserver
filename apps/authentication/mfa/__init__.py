from .otp import MFAOtp, otp_failed_msg
from .radius import MFARadius

MFA_BACKENDS = [MFAOtp, MFARadius]
