#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Alejandro Gómez'
SITENAME = 'dialelo'
SITESUBTITLE = ''
ALTNAME = ''
DESCRIPTION = ''

#SITEURL = 'http://dialelo.github.io'
SITEURL = ''
FAVICON = 'favicon.ico'

PATH = 'content'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'en'
LOCALE = 'en_US'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = []

# Social widget
SOCIAL = (
    ('twitter', 'https://twitter.com/dialelo'),
    ('github', 'https://github.com/dialelo'),
)
SHARE = False

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

THEME = 'theme'

DEFAULT_DATE = 'fs'

FOOTER = ("""
(\u0254) 2015 Alejandro Gómez. All the content licensed under a
<a href='http://creativecommons.org/licenses/by/4.0/'>
Creative Commons Attribution</a> license.<br>
Code snippets in the pages are released under
<a href=\"http://opensource.org/licenses/BSD-2-clause\" target=\"_blank\">
 The simplified BSD License</a>, unless otherwise specified.
""")
