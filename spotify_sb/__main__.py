import os
import json
import ipaddress
from urllib.parse import urlparse
import socket
from .spotify import Spotify, SystemEvent
try:
    from .routes import routes
except ImportError:
    routes = None
    print('Unable to import routes, disabling rest api support')
else:
    from sanic import Sanic


def make_app(system_events, spotify):
    app = Sanic('spotify_sb')
    app.blueprint(routes)
    app.system_events = system_events
    app.spotify = spotify
    return app


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-j', '--json', action='store_true', help='json output')
    subparsers = parser.add_subparsers()

    if routes is not None:
        api = subparsers.add_parser('rest-api')
        api.set_defaults(mode='api')
        api.add_argument('host', default='0.0.0.0', nargs='?')
        api.add_argument('port', default=0, nargs='?', type=int)

    play = subparsers.add_parser('play')
    play.set_defaults(mode='play')
    play.add_argument('-s', '--shuffle', action='store_true', default=False)
    play.add_argument('track_uri', type=str, default=None, nargs='?')
    play.add_argument('context_uri', type=str, nargs='?', default=None)

    pause = subparsers.add_parser('pause')
    pause.set_defaults(mode='pause')
    info = subparsers.add_parser('info')
    info.set_defaults(mode='info')
    next_ = subparsers.add_parser('next')
    next_.set_defaults(mode='next')
    previous = subparsers.add_parser('previous')
    previous.set_defaults(mode='previous')

    args = parser.parse_args()
    if not hasattr(args, 'mode'):
        raise ValueError('Must use a subcommand!')

    evt = SystemEvent()
    client = Spotify(evt)

    if args.mode == 'play':
        client.play(track_url=args.track_uri, context_url=args.context_uri, shuffle=args.shuffle)
    elif args.mode in ('pause', 'next', 'previous'):
        getattr(client, args.mode)()
    elif args.mode == 'info':
        ...
    elif args.mode == 'api':
        app = make_app(evt, client)
        assert args.port > -1
        try:
            addr = ipaddress.ip_address(args.host)
        except ValueError as e:
            parsed_uri = urlparse(args.host)
            if parsed_uri.scheme not in ('file', ''):
                raise ValueError(f'Invalid scheme {parsed_uri.scheme} (from {parsed_uri})') from e
            if parsed_uri.netloc not in ('', 'localhost', '::1', '127.0.0.1'):
                raise ValueError(
                    'Unix domain sockets only work on localhost, not '
                    f'{parsed_uri.netloc} (from {parsed_uri})') from e
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                os.unlink(parsed_uri.path)
            except FileNotFoundError:
                pass
            print(f'Binding to unix socket {parsed_uri.path}')
            sock.bind(parsed_uri.path)
        else:
            if isinstance(addr, ipaddress.IPv6Address):
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((str(addr), args.port))
        print(f'Bonded to {sock.getsockname()}')
        app.run(workers=1, sock=sock)
    else:
        raise NotImplementedError(args.mode)
    if args.json:
        print(json.dumps({'running': client.running, 'status': client.status.name, 'track': client.current_track._asdict(), 'position': client.position._asdict()}, indent=4, sort_keys=True))
    else:
        print(f'Running: {client.running}\nStatus: {client.status}\nCurrent Track: {client.current_track}\nPosition: {client.position}')
