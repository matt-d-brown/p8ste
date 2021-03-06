# Copyright 2008 Thomas Quemard
#
# Paste-It is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 3.0, or (at your option)
# any later version.
#
# Paste-It is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for more details.


import cgi
import google.appengine.api.users
from google.appengine.ext import db
import pygments.lexer
import random

import app
import app.user
import settings
import smoid.languages


kPASTE_STATUS_PUBLIC = 0
kPASTE_STATUS_PRIVATE = 1
kPASTE_STATUS_MODERATED = 2
kPASTE_STATUS_WAITING_FOR_APPROVAL = 3


class Form (db.Model):
    token           = db.StringProperty()
    created_at      = db.DateTimeProperty()
    created_by_ip   = db.StringProperty()
    expired_at      = db.DateTimeProperty()


class PasteCount (db.Model):
    count = db.IntegerProperty(default=0)
    last_checked = db.DateTimeProperty()
    path = db.StringProperty()


class PasteStats(db.Model):
    paste_count = db.IntegerProperty()
    last_posted_at = db.DateTimeProperty(auto_now=True)
    last_edited_at = db.DateTimeProperty(auto_now=True)


class User (db.Model):
    id = db.StringProperty()
    google_id = db.StringProperty()
    email = db.StringProperty()
    gravatar_id = db.TextProperty()
    paste_count = db.IntegerProperty()
    registered_at = db.DateTimeProperty()

    def get_gravatar (self, size):
        return "http://www.gravatar.com/avatar/" + self.gravatar_id + ".jpg?s=" + str(size)


class Pasty (db.Model):
    characters = db.IntegerProperty(default=0)
    code = db.TextProperty(default="")
    code_colored = db.TextProperty(default="")
    forks = db.IntegerProperty(default=0)
    highlights = db.TextProperty(default="")
    indirect_forks = db.IntegerProperty(default=0)
    is_moderated = db.BooleanProperty(default=False)
    language = db.StringProperty(choices=["ada", "html", "java", "lua", "perl", "php", "python", "python_console", "ruby", "scala", "sh", "sql", "xml"])
    lines = db.IntegerProperty(default=0)
    posted_at = db.DateTimeProperty()
    posted_by_ip = db.StringProperty(default="")
    posted_by_user_name = db.StringProperty(default="")
    edited_at = db.DateTimeProperty()
    edited_by_ip = db.StringProperty(default="")
    edited_by_user_name = db.StringProperty(default="")
    expired_at = db.DateTimeProperty()
    parent_paste = db.StringProperty(default="")
    secret_key = db.TextProperty(default="")
    slug = db.StringProperty(default="")
    snippet = db.TextProperty(default="")
    tags = db.TextProperty(default="")
    thread = db.StringProperty(default="")
    thread_level = db.IntegerProperty(default=0)
    thread_position = db.IntegerProperty(default=0)
    title = db.TextProperty(default="")
    status = db.IntegerProperty(default=0, choices=[kPASTE_STATUS_PUBLIC, kPASTE_STATUS_PRIVATE, kPASTE_STATUS_MODERATED, kPASTE_STATUS_WAITING_FOR_APPROVAL])
    user = db.ReferenceProperty(User)

    def _is_current_user_author_or_admin (self):
        cuser = app.user.get_current_user()
        is_author = self.user and self.user.id == cuser.id
        return cuser.is_google_admin or is_author

    @staticmethod
    def make_secret_key (length = 16):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        char_count = len(chars)
        key = ""
        for i in xrange(0, length):
            pos = random.randint(0, char_count - 1)
            key += chars[pos]
        return key

    @staticmethod
    def make_snippet (code, snippet_len):
        snippet = ""
        newline_block = False
        char_count = 0
        last_char = ""
        whitespaces = ["\n", "\r", "\t", " "]

        for c in code:
            if c in whitespaces:
                if last_char != " ":
                    snippet += " "
                    last_char = " "
                    char_count += 1
            else:
                snippet += c
                last_char = c
                char_count += 1

            if char_count > snippet_len:
                snippet = snippet[0: char_count - 3] + "..."
                break

        return snippet

    @staticmethod
    def parse_highlights (hl_str, line_count):
        highlights = []
        hls = hl_str.split(",")

        for hl in hls:
            # Highlight a given line
            if hl.isdigit():
                highlights.append(str(hl))

            # Reset highlights
            elif hl == "-":
                highlights = []

            # Unhighlight a given line
            elif hl[0:1] == "!" and hl[1:] in highlights:
                highlights.remove(hl[1:])

        return highlights

    def extract_highlights_from_code (self, code):
        raw_code = ""
        highlights = []
        lines = code.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("@h@"):
                highlights.append(i)
                raw_code += line[3:]
            else:
                raw_code += line
            raw_code += "\n"

        return raw_code, highlights

    def get_code (self):
        code = ""
        if self.status == kPASTE_STATUS_PUBLIC:
            code = self.code
        return code

    def get_fork_url (self):
        return app.url("%s/fork", self.slug)

    def get_icon_url (self):
        url = ""

        if self.status == kPASTE_STATUS_PRIVATE:
            url = app.image_url("silk/lock.png")
        elif self.status == kPASTE_STATUS_MODERATED:
            url = app.image_url("silk/flag_red.png")
        elif self.status == kPASTE_STATUS_WAITING_FOR_APPROVAL:
            url = app.image_url("silk/hourglass.png")
        elif self.status == kPASTE_STATUS_PUBLIC:
            if self.language and self.language in smoid.languages.languages:
                url = app.image_url("languages/%s.png", self.language)
            else:
                url = app.image_url("silk/page_white_text.png")
        return url

    def get_language_name (self):
        lang = self.language

        if smoid.languages.languages.has_key(lang) and smoid.languages.languages[lang].has_key("name"):
            lang = smoid.languages.languages[lang]["name"]

        return lang

    def get_language_url (self):
        lang = self.language
        url = ""
        if smoid.languages.languages.has_key(lang) and smoid.languages.languages[lang].has_key("home_url"):
            url = smoid.languages.languages[lang]["home_url"]

        return url

    def get_moderate_url (self):
        return app.url("%s/moderate", self.slug)

    def get_parsed_highlights (self):
        return Pasty.parse_highlights(self.highlights, self.code.count("\n"))

    def get_private_url (self):
        return app.url("%s?key=%s", self.slug, self.secret_key)

    def get_raw_code (self):
        raw_code = ""
        if self.highlights:
            lines = self.code.splitlines()
            for i, line in enumerate(lines):
                if line.startswith("@h@"):
                    raw_code += line[3:]
                else:
                    raw_code += line
                raw_code += "\r\n"
        else:
            raw_code = self.code

        return raw_code

    def get_real_moderate_url (self):
        return app.url("%s/moderate?sure=yes", self.slug)

    def get_title (self):
        """
        Gets the title if there is one and the status allows it.
        """

        title = self.slug
        if self.title:
            if self.status == kPASTE_STATUS_PUBLIC or self._is_current_user_author_or_admin():
                title = self.title
        return title

    def get_snippet (self):
        """
        Gets the snippet if there is one and the status allows it.
        """
        snippet = ""
        if self.snippet:
            if self.status == kPASTE_STATUS_PUBLIC or self._is_current_user_author_or_admin():
                snippet = self.snippet
            elif self.status == kPASTE_STATUS_PRIVATE:
                snippet = "[[ PRIVATE ]]"
        return snippet

    def get_url (self):
        return app.url("%s", self.slug)

    def is_code_viewable (self):
        return self.status == kPASTE_STATUS_PUBLIC or self._is_current_user_author_or_admin()

    def is_diffable (self):
        return self.status == kPASTE_STATUS_PUBLIC

    def is_forkable (self):
        return self.status == kPASTE_STATUS_PUBLIC

    def is_private (self):
        return self.status == kPASTE_STATUS_PRIVATE

    def is_public (self):
        return self.status == kPASTE_STATUS_PUBLIC

    def is_moderated (self):
        return self.status == kPASTE_STATUS_MODERATED

    def is_waiting_for_approval (self):
        return self.status == kPASTE_STATUS_WAITING_FOR_APPROVAL

    def set_code (self, code):
        raw_code, highlights = self.extract_highlights_from_code(code)

        self.code = code
        self.highlights = ",".join([str(line) for line in highlights])
        self.characters = len(code)
        self.snippet = Pasty.make_snippet(raw_code, settings.PASTE_SNIPPET_MAX_LENGTH)
        self.language = smoid.GrandChecker().find_out_language(raw_code)
        self.code_colored = self.syntax_highlight_code(raw_code, self.language)
        self.lines = raw_code.count("\n") + 1

    def syntax_highlight_code (self, code, language_name):
        result = ""

        if language_name != "" and language_name in smoid.languages.languages:
            language = smoid.languages.languages[language_name]
            if "lexer" in language:
                lexer = pygments.lexers.get_lexer_by_name(language["lexer"])
                if lexer:
                    formatter = app.syhili.HtmlFormatter(linenos=True, cssclass="code")
                    result = pygments.highlight(code, lexer, formatter)

        if result == "":
            result = cgi.escape(code)

        return result

class Log (db.Model):
   type = db.StringProperty(choices=["paste_add", "paste_fork", "user_register"])
   user = db.ReferenceProperty(User)
   item1_slug = db.StringProperty()
   item1_name = db.StringProperty()
   item2_slug = db.StringProperty()
   item2_name = db.StringProperty()
