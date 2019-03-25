from ScriptingBridge import SBApplication, SBObject
import weakref
import struct
import shlex
import subprocess
import objc
from contextlib import contextmanager
from enum import Enum
from typing import Mapping
from typing import List, Optional, Generator
from collections import namedtuple

SIZE = namedtuple('Size', ('width', 'height'))
Geometry = namedtuple('Geometry', ('x', 'y', 'size'))

# OSX has common codes as a packed 32bit big endian int.
SIZE_CODE, = struct.unpack('>L', b'ptsz')
POSITION_CODE, = struct.unpack('>L', b'posn')
ACTION_CODE, = struct.unpack('>L', b'actT')
APPLE_EVENT_CODE, = struct.unpack('>L', b'aevt')
QUIT_EVENT_ID, = struct.unpack('>L', b'quit')

# OSX sendEvent_id_format operates funny. You will see in sdef /Applications/Spotify.app
# things like aevtquit for the hidden code. Those are a lie.
# The real magic is app.sendEvent_id_format_(struct.unpack('>L', 'aevt')[0], struct.unpack('>L', 'quit')[0], 0)
# See how it splits? Fucking wow.

#


class TrackPosition(namedtuple('TrackPosition', ['current_ms', 'duration_ms', 'percentage'])):
    __slots__ = ()


class TrackInfo(namedtuple(
        'TrackInfo', [
            'title',
            'artist',
            'album',
            'disc_number',
            'track_number',
            'starred',
            'popularity',
            'play_count',
            'cover_url',
            'album_artist',
            'url',
        ])):
    __slots__ = ()


class SpotifyPlayStates(Enum):
    STOPPED, = struct.unpack('>L', b'kPSS')
    PLAYING, = struct.unpack('>L', b'kPSP')
    PAUSED, = struct.unpack('>L', b'kPSp')


def first(iterable):
    for i in iterable:
        return i


def list_unique_properties(app) -> Mapping[str, objc.selector]:
    return {
        key: type(getattr(app, key))
        for key in list(set(dir(app)) - set(dir(SBObject)))
    }


class SystemEvent(object):
    def send_keystroke(self, char):
        self.app.keystroke_using_(char, None)

    def __init__(self):
        self.app = SBApplication.applicationWithBundleIdentifier_('com.apple.systemevents')
        super().__init__()

    def stop_screen_saver(self):
        self.send_keystroke('\r')

    @property
    def processes(self) -> Mapping[str, SBObject]:
        processes = {}
        for process in self.app.applicationProcesses():
            name = process.name()
            assert isinstance(name, str)
            try:
                processes[name].append(process)
            except KeyError:
                processes[name] = [process]
        for key in processes:
            processes[key] = sorted(processes[key], key=lambda val: val.frontmost())
        return processes

    def get_process_by_name(self, name):
        name = name.lower()
        for proc_name, app in self.processes.iteritems():
            if proc_name.lower() == name:
                return app
        raise KeyError('{} not found!'.format(name))

    def get_processes_by_bundle(self, name):
        name = name.lower()
        for process in self.app.applicationProcesses():
            if not process.bundleIdentifier():
                continue
            if process.bundleIdentifier().lower() == name:
                yield process

    def cast_process_to_class(self, class_type):
        app = SBApplication.applicationWithBundleIdentifier_(class_type.bundle_id)
        started = bool(app.valueForKey_('running'))
        if not started:
            app.activate()
        for process in self.get_processes_by_bundle(class_type.bundle_id):
            t = class_type(self, process)
            if not started:
                t.hide()
            yield t


class CommonApp(object):
    bundle_id: str = None

    def __init__(self,
                 event_system: SystemEvent,
                 process: Optional[SBObject]=None):
        assert self.bundle_id is not None, 'Requires a bundle_id to be in class type!'
        self.app = SBApplication.applicationWithBundleIdentifier_(self.bundle_id)
        self.app_props = list_unique_properties(self.app)
        self._events: ReferenceType[SystemEvent] = weakref.ref(event_system)
        self._process = process
        self._caffeine_fh = None
        super().__init__()

    def start(self):
        if not self.running:
            self.app.activate()

    def quit(self):
        if self.running:
            self.app.sendEvent_id_format_(APPLE_EVENT_CODE, QUIT_EVENT_ID, 0)

    @property
    def process(self):
        if self._process is not None:
            if self._process.get() is None:
                self._process = None
            elif self._process.bundleIdentifier() != self.bundle_id:
                self._process = None
        if self._process is None:
            ref = self._events()
            self._process = first(ref.get_processes_by_bundle(self.bundle_id))
        return self._process

    @property
    def pid(self):
        process = self.process
        if process is None:
            raise ValueError('{} is not running'.format(self.__class__.__name__))
        return process.unixId()

    @property
    def windows(self) -> List[SBObject]:
        process = self.process
        windows = list(process.windows())
        if not windows:
            raise ValueError(
                '{} either does not have any windows or '
                'does not allow you to query them'.format(self.__class__.__name__))
        return windows

    def sizes(self) -> Generator[Geometry, None, None]:
        for window in self.windows:
            item = window.propertyWithCode_(SIZE_CODE).get()
            x, y = window.propertyWithCode_(POSITION_CODE).get()
            if item is None:
                break
            width, height = item
            yield Geometry(x, y, SIZE(width, height))

    def hide(self):
        self.process.setVisible_(0)

    def show(self):
        self.process.setVisible_(1)

    def send_keystroke(self, char):
        self.app.keystroke_using_(char, None)

    @property
    def running(self):
        return bool(self.app.valueForKey_('running'))

    def caffeinate(self):
        ref = self._events()
        ref.stop_screen_saver()
        self.uncaffeinate()
        self._caffeine_fh = subprocess.Popen(shlex.split(
            'caffeinate -d -w {}'.format(self.pid)), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, close_fds=True)

    def uncaffeinate(self):
        if self._caffeine_fh and self._caffeine_fh.poll() is None:
            self._caffeine_fh.terminate()
        self._caffeine_fh = None

    @contextmanager
    def halt_saver(self):
        '''
        >>> with spotify.halt_saver():
        ...     # do something
        ...     pass
        '''
        self.caffeinate()
        yield self._caffeine_fh
        self.uncaffeinate()


class Spotify(CommonApp):
    bundle_id = 'com.spotify.client'

    def __init__(self, event_system, process=None):
        super().__init__(event_system, process)
        if not self.running:
            self.start()

    @property
    def current_track(self):
        track = self.app.currentTrack()
        if track:
            kwargs = {
                'artist': track.artist(),
                'album': track.album(),
                'disc_number': track.discNumber(),
                'play_count': track.playedCount(),
                'track_number': track.trackNumber(),
                'starred': track.starred(),
                'popularity': track.popularity(),
                'title': track.name(),
                'cover_url': track.artworkUrl(),
                'album_artist': track.albumArtist(),
                'url': track.spotifyUrl(),
            }
            for key in kwargs:
                if not isinstance(kwargs[key], (str, int, float)):
                    kwargs[key] = str(kwargs[key])
            return TrackInfo(**kwargs)
        return None

    @property
    def position(self):
        duration = self.app.currentTrack().duration()
        position = int(self.app.playerPosition() * 1000)
        return TrackPosition(position, duration, float(position) / duration * 100)

    @property
    def volume(self):
        return self.app.soundVolume()

    @volume.setter
    def volume(self, val):
        if not isinstance(val, int):
            raise TypeError('Must be an int')
        if not (0 <= val <= 100):
            raise ValueError('Must be between 0-100')
        self.app.setSoundVolume_(val)

    @property
    def status(self):
        status = SpotifyPlayStates(self.app.playerState())
        return status

    def next(self):
        self.app.nextTrack()

    def previous(self):
        self.app.previousTrack()

    @property
    def shuffle(self):
        return self.app.shuffling()

    @shuffle.setter
    def shuffle(self, val):
        if not isinstance(val, bool):
            raise TypeError('Only bools allowed')
        self.app.setShuffling_(int(val))

    def play(self, track_url=None, context_url=None, shuffle=False):
        self.caffeinate()
        self.shuffle = shuffle
        if track_url is not None:
            assert track_url.startswith('spotify:track:'), 'not a track url'
            self.app.playTrack_inContext_(track_url, context_url)
        else:
            self.app.play()

    def pause(self):
        if self.status is SpotifyPlayStates.PAUSED:
            self.app.play()
            return
        self.app.pause()
        self.uncaffeinate()


if __name__ == '__main__':
    evt = SystemEvent()
    client = Spotify(evt)
    client.play()
