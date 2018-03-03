# -*- coding: utf-8 -*-

"""
This file is part of the Mouseover Dictionary add-on for Anki.

Main Module, hooks add-on methods into Anki.

Copyright: (c) 2018 Glutanimate <https://glutanimate.com/>
License: GNU AGPLv3 <https://www.gnu.org/licenses/agpl.html>
"""

from __future__ import unicode_literals

import re

from aqt.qt import *
from aqt import mw
from aqt.reviewer import Reviewer
from anki.hooks import wrap, addHook

from .js import html
from .consts import *
from .config import (MODE, DECK, NOTETYPE, TERM_FIELD,
                     DEFINITION_FIELD, USER_STYLES,
                     EXCLUDED_FIELDS, ALWAYS_SHOW)
from .template import addModel


# support for JS Booster add-on
try:
    from jsbooster import review_hack
    JSBOOSTER = True
except ImportError:
    JSBOOSTER = False

class DictionaryLookup(QObject):
    """
    A single instance of the class is created and stored in the module's dictLookup
    variable. This instance is then added as a javascript object to the reviewer's
    main frame. We then get callbacks from qtip's set functions requesting
    the html to display
    """

    def __init__(self):
        QObject.__init__(self)

    @pyqtSlot(str, result=str)
    def definitionFor(self, term):
        return self.generateDefinition(term)

    def generateDefinition(self, term):
        return getNoteSnippetsFor(term.strip())


dictLookup = DictionaryLookup()


html_reslist = """<div class="tt-reslist">{}</div>"""
html_snippet = """<div class="tt-res">{}</div>"""
html_field = """<div class="tt-fld">{}</div>"""

cloze_re_str = r"\{\{c(\d+)::(.*?)(::(.*?))?\}\}"
cloze_re = re.compile(cloze_re_str)

def getNoteSnippetsFor(term):
    """Find relevant note snippets for search term"""
    print("getNoteSnippetsFor")
    # exclude current note
    current_nid = mw.reviewer.card.note().id
    exclusion_string = "-nid:{} ".format(current_nid)
    # exclude matches in predefined fields
    # exclusion_string += " ".join(['''-"{}:*{}*"'''.format(fld, term)
    #                             for fld in EXCLUDED_FIELDS])
    # construct query string
    query = u'''deck:current "{}" {}'''.format(term, exclusion_string)

    # NOTE: performing the SQL query directly might be faster
    res = sorted(mw.col.findNotes(query))  
    if not res:
        if ALWAYS_SHOW:
            return "No results found."
        else:
            return ""
    
    print("Query finished.")

    content = []
    for nid in res:
        note = mw.col.getNote(nid)
        valid_flds = [html_field.format(i[1]) for i in note.items() if i[0] not in EXCLUDED_FIELDS]
        joined_flds = "".join(valid_flds)
        filtered_flds = cloze_re.sub(r"\2", joined_flds)
        content.append(html_snippet.format(filtered_flds))
    
    html = html_reslist.format("".join(content))

    print("Html compiled")
    return html

def searchDefinitionFor(term):
    """Look up search term in dictionary deck"""
    query = u"""note:"{}" {}:"{}" """.format(NOTETYPE, TERM_FIELD, term)
    res = mw.col.findNotes(query)
    if res:
        nid = res[0]
        note = mw.col.getNote(nid)
        return note[DEFINITION_FIELD]
    return "No dictionary entry found."


def addJavascriptObjects(self):
    """Add python object to JS"""
    self.web.page().mainFrame().addToJavaScriptWindowObject("pyDictLookup", dictLookup)


def setupAddon():
    """Setup hooks, prepare note type and deck"""
    Reviewer._initWeb = wrap(Reviewer._initWeb, addJavascriptObjects, "after")
    # JSBooster support:
    if not JSBOOSTER:
        Reviewer._revHtml += html + "<style>{}</style>".format(USER_STYLES) 
    else:
        review_hack.review_html_scripts += html + "<style>{}</style>".format(USER_STYLES)

    if MODE == "dictionary":
        did = mw.col.decks.byName(DECK)
        if not did:
            mw.col.decks.id(DECK)
        mid = mw.col.models.byName(NOTETYPE)
        if not mid:
            addModel(mw.col)
        if not did or not mid:
            mw.reset()


# Hooks

addHook("profileLoaded", setupAddon)
