#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

PLUGINS = [ 'tipue_search' ]
PLUGIN_PATH = 'plugins'

DIRECT_TEMPLATES = (('index', 'tags', 'categories', 'authors', 'archives', 'search'))

# Metadata
AUTHOR = 'Alejandro Gómez'
SITENAME = 'dialelo'
SITESUBTITLE = ''
ALTNAME = ''
DESCRIPTION = ''
SITEURL = 'http://dialelo.github.io'
FAVICON = 'favicon.ico'

# Content
PATH = 'content'

# Lang and locale
TIMEZONE = 'Europe/Paris'
DEFAULT_LANG = 'en'
LOCALE = 'en'

# Feed
FEED_ALL_ATOM = 'feeds/atom.xml'
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Search
TIPUE_SEARCH_SAVE_AS = 'tipuesearch_content.json'

# Social
SOCIAL = (
    ('github', 'https://github.com/dialelo'),
    ('twitter', 'https://twitter.com/dialelo'),
)
SHARE = False

# Appearance
DEFAULT_PAGINATION = 10
DISPLAY_PAGES_ON_MENU = False
THEME = 'theme'

DEFAULT_DATE = 'fs'

# Footer
FOOTER = ("""
(\u0254) 2015 Alejandro Gómez. All the content licensed under a
<a href='http://creativecommons.org/licenses/by/4.0/'>
Creative Commons Attribution</a> license.<br>
Code snippets in the pages are released under
<a href=\"http://opensource.org/licenses/BSD-2-clause\" target=\"_blank\">
 The simplified BSD License</a>, unless otherwise specified.
""")
