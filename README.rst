Spotify scripting bridge
==========================

I've a Mac Mini that's connected to a TV. I also have a user logged into Spotify but it's not
the same user as on my laptop. I'd like to be able to instruct it to play a playlist, stop, et al.

Requires
----------

Python 3.7 (for API mode)
Python 3.6?


API mode
-----------

Start up an API::

    (cpython37) InvincibleReason:~/software/pfstatsd [master]$ python -m spotify_sb rest-api ::1 8080
    Bonded to ('::1', 8080, 0, 0)
    [2019-03-24 20:53:38 -0700] [37059] [INFO] Starting worker [37059]


List status::

    (cpython36) InvincibleReason:~/software/instruct [master]$ curl -s http://[::1]:8080/ | python -m json.tool
    {
        "running": true,
        "status": "PLAYING",
        "track": {
            "title": "Syringe Nation - Unreleased Demo",
            "artist": "Omega Lithium",
            "album": "Colossus",
            "disc_number": 1,
            "track_number": 2,
            "starred": false,
            "popularity": 2,
            "play_count": 0,
            "cover_url": "http://i.scdn.co/image/bbe81f5d897a4a515e84441bd012e6a7f0fcb6b8",
            "album_artist": "Omega Lithium",
            "url": "spotify:track:2Yxrh3XT83QfxNbc5ynmoa"
        },
        "position": {
            "current_ms": 8786,
            "duration_ms": 220032,
            "percentage": 3.9930555556
        }
    }

Play a track on it's album::

    (cpython36) InvincibleReason:~/software/instruct [master]$ curl -L -s -d '{"track_uri": "spotify:track:2rg4YOksNwINIP5wEEkKz4"}' -L -X POST http://[::1]:8080/play   | python -m json.tool

    {
        "running": true,
        "status": "PLAYING",
        "track": {
            "title": "Out!",
            "artist": "Lunatica",
            "album": "The Edge Of Infinity",
            "disc_number": 1,
            "track_number": 5,
            "starred": false,
            "popularity": 22,
            "play_count": 0,
            "cover_url": "http://i.scdn.co/image/5df01289f29c0155e4a06e5736a35b6afc84a2af",
            "album_artist": "Lunatica",
            "url": "spotify:track:2rg4YOksNwINIP5wEEkKz4"
        },
        "position": {
            "current_ms": 462,
            "duration_ms": 222200,
            "percentage": 0.2079207921
        }
    }

Play a specific track in a playlist, album, etc::

    (cpython36) InvincibleReason:~/software/instruct [master]$ curl -L -s -d '{"track_uri": "spotify:track:3V417nSM4Ilh0Tt5CqustV", "context_uri": "spotify:user:XXXXXXXXXX:playlist:YYYYYYYYYYYYYYYYYYYYYY"}' -L -X POST http://[::1]:8080/play   | python -m json.tool
    {
        "running": true,
        "status": "PLAYING",
        "track": {
            "title": "Yggdrasil",
            "artist": "Brothers of Metal",
            "album": "Prophecy of Ragnar\u00f6k",
            "disc_number": 1,
            "track_number": 6,
            "starred": false,
            "popularity": 57,
            "play_count": 0,
            "cover_url": "http://i.scdn.co/image/1fbf2f93c5e3f893903a8fbf5532c47035a4f4d2",
            "album_artist": "Brothers of Metal",
            "url": "spotify:track:3V417nSM4Ilh0Tt5CqustV"
        },
        "position": {
            "current_ms": 504,
            "duration_ms": 272292,
            "percentage": 0.1850954123
        }
    }

Skip to prev(ious) / next::

    (cpython36) InvincibleReason:~/software/instruct [master]$ curl -sL -X POST -s http://[::1]:8080/prev | python -m json.tool
    {
        "running": true,
        "status": "PLAYING",
        "track": {
            "title": "Out!",
            "artist": "Lunatica",
            "album": "The Edge Of Infinity",
            "disc_number": 1,
            "track_number": 5,
            "starred": false,
            "popularity": 22,
            "play_count": 0,
            "cover_url": "http://i.scdn.co/image/5df01289f29c0155e4a06e5736a35b6afc84a2af",
            "album_artist": "Lunatica",
            "url": "spotify:track:2rg4YOksNwINIP5wEEkKz4"
        },
        "position": {
            "current_ms": 515,
            "duration_ms": 222200,
            "percentage": 0.2317731773
        }
    }
    (cpython36) InvincibleReason:~/software/instruct [master]$ curl -sL -X POST -s http://[::1]:8080/next | python -m json.tool
    {
        "running": true,
        "status": "PLAYING",
        "track": {
            "title": "Eine Rose F\u00fcr Den Abschied",
            "artist": "Erben der Schopfung",
            "album": "Twilight",
            "disc_number": 1,
            "track_number": 4,
            "starred": false,
            "popularity": 6,
            "play_count": 0,
            "cover_url": "http://i.scdn.co/image/e67a54c0f69d52dca22e0e952e780788a28246fc",
            "album_artist": "Erben der Schopfung",
            "url": "spotify:track:2ly5pc8LOeM5aVQpuVVmCg"
        },
        "position": {
            "current_ms": 514,
            "duration_ms": 349560,
            "percentage": 0.1470419957
        }
    }


Pause/un-Pause::

    (cpython36) InvincibleReason:~/software/instruct [master]$ curl -sL -X POST -s http://[::1]:8080/pause | python -m json.tool
    {
        "running": true,
        "status": "PAUSED",
        "track": {
            "title": "Eine Rose F\u00fcr Den Abschied",
            "artist": "Erben der Schopfung",
            "album": "Twilight",
            "disc_number": 1,
            "track_number": 4,
            "starred": false,
            "popularity": 6,
            "play_count": 0,
            "cover_url": "http://i.scdn.co/image/e67a54c0f69d52dca22e0e952e780788a28246fc",
            "album_artist": "Erben der Schopfung",
            "url": "spotify:track:2ly5pc8LOeM5aVQpuVVmCg"
        },
        "position": {
            "current_ms": 40229,
            "duration_ms": 349560,
            "percentage": 11.5084677881
        }
    }
    (cpython36) InvincibleReason:~/software/instruct [master]$ curl -sL -X POST -s http://[::1]:8080/pause | python -m json.tool
    {
        "running": true,
        "status": "PLAYING",
        "track": {
            "title": "Eine Rose F\u00fcr Den Abschied",
            "artist": "Erben der Schopfung",
            "album": "Twilight",
            "disc_number": 1,
            "track_number": 4,
            "starred": false,
            "popularity": 6,
            "play_count": 0,
            "cover_url": "http://i.scdn.co/image/e67a54c0f69d52dca22e0e952e780788a28246fc",
            "album_artist": "Erben der Schopfung",
            "url": "spotify:track:2ly5pc8LOeM5aVQpuVVmCg"
        },
        "position": {
            "current_ms": 40742,
            "duration_ms": 349560,
            "percentage": 11.6552237098
        }
    }
