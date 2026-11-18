"""Windows Core Audio: сила на звука (IAudioEndpointVolume) и смяна на default устройство.

Изискване: pycaw==20240210 (и comtypes). При грешка всичко се логва с traceback, а UI-ът
показва неактивен контрол – приложението не пада.
"""
import logging
import sys

log = logging.getLogger(__name__)
IS_WIN = sys.platform == "win32"

_RENDER_PREFIX = "{0.0.0.00000000}"      # render (възпроизвеждащи) endpoint-и


_avail = None


def available() -> bool:
    if not IS_WIN:
        return False
    # ВАЖНО: тук НЕ се импортира pycaw/comtypes. Импортът в GUI нишката инициализира COM там в MTA режим,
    # което е в конфликт със STA на Qt (грешки 0x8001010e „wrong thread“ в системните диалози и access violation).
    # comtypes се зарежда само във фоновата аудио нишка.
    global _avail
    if _avail is None:
        try:
            import importlib.util
            _avail = importlib.util.find_spec("pycaw") is not None and importlib.util.find_spec("comtypes") is not None
        except Exception:
            _avail = False
    return _avail


# ВАЖНО: COM обектите (comtypes) трябва да се освобождават (Release) в нишката, в която са създадени.
# Ако garbage collector-ът в GUI нишката ги намери като „боклук“, Release() от друга нишка води до
# "Windows fatal exception: access violation". Затова всеки COM обект се пази в _hold, докато аудио
# нишката сама го освободи (del + gc.collect()) след края на задачата.
_hold = []


def _keep(obj):
    _hold.append(obj)
    return obj


def _release_all():
    """Вика се САМО от аудио нишката."""
    import gc
    del _hold[:]
    gc.collect()


def _endpoint_volume():
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    dev = _keep(AudioUtilities.GetSpeakers())
    iface = _keep(dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None))
    return _keep(cast(iface, POINTER(IAudioEndpointVolume)))


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
        for d in _keep(AudioUtilities.GetAllDevices()):
            _keep(d)
            if d.id.startswith(_RENDER_PREFIX) and getattr(d.state, "value", d.state) == 1:   # 1 = DEVICE_STATE_ACTIVE
                devices.append((d.id, d.FriendlyName or d.id))
        try:
            default_id = _keep(AudioUtilities.GetSpeakers()).GetId()
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
        policy = _keep(comtypes.CoCreateInstance(clsid, IPolicyConfig, comtypes.CLSCTX_ALL))
        for role in (0, 1, 2):   # eConsole, eMultimedia, eCommunications
            policy.SetDefaultEndpoint(device_id, role)
        return True
    except Exception:
        log.exception("set_default_output неуспешно")
        return False


# ====================================================================== асинхронен достъп (никога от GUI нишката)
# COM заявките към Core Audio (особено GetAllDevices) могат да отнемат стотици ms или да увиснат при
# проблемен драйвер. Затова се изпълняват в една фонова нишка, а панелът ползва последния известен
# резултат (кеш) и се опреснява, когато дойдат нови данни.
import queue
import threading
import time

_cache = {"vol": -1, "muted": False, "devices": [], "default": None, "dev_ts": 0.0, "ready": False}
_q = queue.Queue()
_thread = None
_thread_lock = threading.Lock()
_pending_vol = [None]


def _worker():
    try:
        sys.coinit_flags = 2                 # COINIT_APARTMENTTHREADED – преди първия импорт на comtypes
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        log.exception("CoInitialize в аудио нишката неуспешно")
    while True:
        job = _q.get()
        try:
            job()
        except Exception:
            log.exception("Аудио задача неуспешна")
        finally:
            try:
                _release_all()               # COM обектите се освобождават тук, в тяхната нишка
            except Exception:
                log.exception("Освобождаване на COM обекти неуспешно")


def _submit(job):
    global _thread
    with _thread_lock:
        if _thread is None:
            _thread = threading.Thread(target=_worker, daemon=True, name="audio-worker")
            _thread.start()
    _q.put(job)


def snapshot() -> dict:
    return dict(_cache)


def refresh_async(done=None, force_devices=False):
    """Опреснява сила/mute (винаги) и списъка с изходи (най-много веднъж на 30 s); `done(snapshot)` се вика във фонова нишка."""
    if not IS_WIN:
        return

    def job():
        v = get_volume()
        _cache.update(vol=v, muted=get_mute() if v >= 0 else False)
        if force_devices or not _cache["devices"] or time.monotonic() - _cache["dev_ts"] > 30:
            devices, default_id = list_outputs()
            _cache.update(devices=devices, default=default_id, dev_ts=time.monotonic())
        _cache["ready"] = True
        if done:
            done(snapshot())
    _submit(job)


def set_volume_async(percent: int):
    _pending_vol[0] = percent                  # слива бързите движения на плъзгача в последната стойност

    def job():
        v, _pending_vol[0] = _pending_vol[0], None
        if v is not None:
            set_volume(v)
            _cache["vol"] = v
    _submit(job)


def set_mute_async(state: bool):
    def job():
        set_mute(state)
        _cache["muted"] = state
    _submit(job)


def set_default_output_async(device_id: str, done=None):
    def job():
        ok = set_default_output(device_id)
        if ok:
            _cache["default"] = device_id
        if done:
            done(ok)
    _submit(job)
