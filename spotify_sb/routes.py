import asyncio
import time
import json as std_json
from instruct import Base as _Base
from sanic import Blueprint
from typing import Optional
from sanic.response import json, redirect
from .spotify import SpotifyPlayStates

routes = Blueprint(__name__)


class APIError(Exception):
    def _asdict(self):
        return {
            'type': type(self).__name__,
            'message': str(self)
        }


class ValidationError(APIError, ValueError, TypeError):
    def __init__(self, message, *errors):
        assert errors
        self.message = message
        self.errors = errors

        super().__init__(message, *errors)

    def _asdict(self):
        return {
            'type': type(self).__name__,
            'errors': [error._asdict() for error in self.errors],
            'message': self.message
        }


class InvalidValue(APIError, ValueError):
    ...


class InvalidType(APIError, ValueError):
    ...


class Base(_Base):
    __slots__ = ()

    def validate(self, *, errors=None):
        if errors is None:
            errors = []
        for key in self._column_types.keys():
            type_check = self._column_types[key]
            if not isinstance(self[key], type_check):
                errors.append(InvalidType(f'{key} should be a {type_check}'))
        if errors:
            raise ValidationError(f'Unable to parse {type(self).__name__}', *errors)
        return self

    @classmethod
    def from_json(cls, data):
        if isinstance(data, (str, bytes)):
            data = std_json.loads(data)
        if isinstance(data, list):
            return [cls(**item) for item in data]
        return cls(**data)


class PlayTrackRequest(Base):
    __slots__ = {
        'track_uri': str,
        'context_uri': Optional[str],
        'shuffle': bool
    }

    def __init__(self, **data):
        self._shuffle_ = False
        super().__init__(**data)

    def validate(self, *, errors=None):
        if self.track_uri is not None and not self.track_uri.startswith('spotify:'):
            errors.append(InvalidValue(f'track_uri must start with spotify:'))
        if self.context_uri is not None and not self.context_uri.startswith('spotify:'):
            errors.append(InvalidValue(f'context_uri must start with spotify:'))
        return super().validate(errors=errors)


@routes.exception(APIError)
def handle_error(request, exception):
    return json(exception._asdict(), status=400)


@routes.middleware('request')
async def setup_spotify(request):
    request['system_events'] = request.app.system_events
    request['spotify'] = request.app.spotify


@routes.get('/')
async def current_status(request):
    spotify = request['spotify']

    return json({
        'running': spotify.running,
        'status': spotify.status.name,
        'track': spotify.current_track._asdict(),
        'position': spotify.position._asdict()
    })


@routes.post('/play')
async def play(request):
    spotify = request['spotify']
    if not request.body:
        if spotify.status is not SpotifyPlayStates.PLAYING:
            spotify.pause()
    else:
        current_track = spotify.current_track
        post = PlayTrackRequest.from_json(request.body).validate()
        spotify.play(post.track_uri, post.context_uri, post.shuffle)
        await wait_for_change(spotify, current_track)
    return await current_status(request)


async def wait_for_change(spotify, previous_track, *, delay=5):
    t_s = time.time()
    while time.time() - t_s < delay and spotify.current_track == previous_track:
        await asyncio.sleep(0.5)


@routes.post('/prev')
async def handle_alias(request):
    return redirect(request.app.url_for(f'{__name__}.next_or_prev_track'), status=307)


@routes.post('/next')
@routes.post('/pause')
@routes.post('/previous')
async def next_or_prev_track(request):
    spotify = request['spotify']
    current_track = spotify.current_track
    _, action = request.path.rsplit('/', 1)
    getattr(spotify, action)()
    await wait_for_change(spotify, current_track)
    return await current_status(request)
