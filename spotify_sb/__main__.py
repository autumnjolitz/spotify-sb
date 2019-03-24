from .spotify import Spotify, SystemEvent


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    play = subparsers.add_parser('play')
    play.set_defaults(mode='play')
    play.add_argument('-s', '--shuffle', action='store_true', default=False)
    play.add_argument('track_uri', type=str, default=None, nargs='?')
    play.add_argument('context_uri', type=str, nargs='?', default=None)

    pause = subparsers.add_parser('pause')
    pause.set_defaults(mode='pause')

    args = parser.parse_args()
    if hasattr(args, 'mode'):
        raise ValueError('Must use a subcommand!')

    evt = SystemEvent()
    client = Spotify(evt)

    if args.mode == 'play':
        client.play(track_url=args.track_uri, context_url=args.context_url, shuffle=args.shuffle)
    elif args.mode == 'pause':
        client.pause()
    else:
        raise NotImplementedError(args.mode)
