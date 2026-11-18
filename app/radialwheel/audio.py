"""Windows Core Audio: сила на звука (IAudioEndpointVolume) и смяна на default устройство.

Изискване: pycaw==20240210 (и comtypes). При грешка всичко се логва с traceback, а UI-ът
показва неактивен контрол – приложението не пада.
"""
import logging
import sys

log = logging.getLogger(__name__)
IS_WIN = sys.platform == "win32"

_RENDER_PREFIX = "{0.0.0.00000000}"      # render (възпроизвеждащи) endpoint-и


def available() -> bool:
    if not IS_WIN:
        return False
    try:
        import pycaw  # noqa: F401
        return True
    except Exception:
        return False


def _endpoint_volume():
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    dev = AudioUtilities.GetSpeakers()
    iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(iface, POINTER(IAudioEndpointVolume))


def get_volume() -> int:
    """0..100 или -1 при грешка."""
    if not IS_WIN:
        return -1
    try:
        return int(round(_endpoint_volume().GetMasterVolumeLevelScalar() * 100))
    except Exception:
        log.exception("get_volume неуспешно")
        return -1


def set_volume(percent: int):
    if not IS_WIN:
        return
    try:
        _endpoint_volume().SetMasterVolumeLevelScalar(max(0, min(100, percent)) / 100.0, None)
    except Exception:
        log.exception("set_volume неуспешно")


def get_mute() -> bool:
    if not IS_WIN:
        return False
    try:
        return bool(_endpoint_volume().GetMute())
    except Exception:
        log.exception("get_mute неуспешно")
        return False


def set_mute(state: bool):
    if not IS_WIN:
        return
    try:
        _endpoint_volume().SetMute(1 if state else 0, None)
    except Exception:
        log.exception("set_mute неуспешно")


def list_outputs():
    """Връща ([(id, име), ...], текущ_default_id)."""
    if not IS_WIN:
        return [], None
    try:
        from pycaw.pycaw import AudioUtilities
        devices = []
        for d in AudioUtilities.GetAllDevices():
            if d.id.startswith(_RENDER_PREFIX) and getattr(d.state, "value", d.state) == 1:   # 1 = DEVICE_STATE_ACTIVE
                devices.append((d.id, d.FriendlyName or d.id))
        try:
            default_id = AudioUtilities.GetSpeakers().GetId()
        except Exception:
            default_id = None
        return devices, default_id
    except Exception:
        log.exception("list_outputs неуспешно")
        return [], None


def set_default_output(device_id: str) -> bool:
    """Задава default устройство за всички роли чрез IPolicyConfig (недокументиран, но стабилен COM интерфейс)."""
    if not IS_WIN:
        return False
    try:
        import comtypes
        from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
        from ctypes import c_int, c_wchar_p

        class IPolicyConfig(IUnknown):
            _iid_ = GUID("{F8679F50-850A-41CF-9C72-430F290290C8}")
            _methods_ = tuple(
                COMMETHOD([], HRESULT, name) for name in (
                    "GetMixFormat", "GetDeviceFormat", "ResetDeviceFormat", "SetDeviceFormat",
                    "GetProcessingPeriod", "SetProcessingPeriod", "GetShareMode", "SetShareMode",
                    "GetPropertyValue", "SetPropertyValue")
            ) + (
                COMMETHOD([], HRESULT, "SetDefaultEndpoint",
                          (["in"], c_wchar_p, "pszDeviceName"), (["in"], c_int, "role")),
                COMMETHOD([], HRESULT, "SetEndpointVisibility",
                          (["in"], c_wchar_p, "pszDeviceName"), (["in"], c_int, "bVisible")),
            )

        clsid = GUID("{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}")
        policy = comtypes.CoCreateInstance(clsid, IPolicyConfig, comtypes.CLSCTX_ALL)
        for role in (0, 1, 2):   # eConsole, eMultimedia, eCommunications
            policy.SetDefaultEndpoint(device_id, role)
        return True
    except Exception:
        log.exception("set_default_output неуспешно")
        return False
