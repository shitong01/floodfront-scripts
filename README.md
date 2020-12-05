# Setup

1. Install requirements.
2. Configure `config.ini` to fit your installation of the floodfront-django project.

# Usage

Scripts detect whether they're being run in a terminal or as part of a pipe.

`./marker2kml.py --since 2019-01-30`

This will export markers created after the date specified, inclusively. The default behavior is to write to `markers.kml`. You can specify an output file with either the `-o/--output` tag, or through redirection, e.g.:

`./marker2kml.py --since 2019-01-30 -o out.kml`

or

`./marker2csv.py --since 2019-01-30 | grep example@gmail.com`

# Tips

The GNU Date program (`date` on Linux distros, `gdate` on OS X) may be useful for semantic dates:

`date -I --date="2 days ago"` which makes a `YYYY-MM-DD` string, and can be substituted:

`./marker2csv.py --since $(date -I --date='5 months ago') > out.csv`

