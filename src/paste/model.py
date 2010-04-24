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


from google.appengine.ext import db
import random

import paste
import smoid.languages


kPASTE_STATUS_PUBLIC = 0
kPASTE_STATUS_PRIVATE = 1
kPASTE_STATUS_MODERATED = 1


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
    indirect_forks = db.IntegerProperty(default=0)
    is_moderated = db.BooleanProperty(default=False)
    language = db.StringProperty(choices=["html", "java", "perl", "php", "python", "python_console", "ruby", "scala", "sh", "xml"])
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
    status = db.IntegerProperty(default=0, choices=[kPASTE_STATUS_PUBLIC, kPASTE_STATUS_PRIVATE, kPASTE_STATUS_MODERATED])
    user = db.ReferenceProperty(User)

    @staticmethod
    def make_secret_key (length = 16):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        char_count = len(chars)
        key = ""
        for i in xrange(0, length):
            pos = random.randint(0, char_count)
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

    def get_code (self):
        code = ""
        if self.status == kPASTE_STATUS_PUBLIC:
            code = self.code
        return code

    def get_fork_url (self):
        return paste.url("%s/fork", self.slug)

    def get_icon_url (self):
        url = ""

        if self.status == kPASTE_STATUS_PRIVATE:
            url = paste.url("images/silk/lock.png")
        elif self.language and self.status == kPASTE_STATUS_PUBLIC:
            if smoid.languages.languages.has_key(self.language) and smoid.languages.languages[self.language].has_key("u_icon"):
                url = paste.url(smoid.languages.languages[self.language]["u_icon"])
        return url

    def get_language_name (self):
        lang = self.language

        if smoid.languages.languages.has_key(lang) and smoid.languages.languages[lang].has_key("name"):
            lang = smoid.languages.languages[lang]["name"]

        return lang

    def get_title (self):
        """
        Gets the title if there is one and the status allows it.
        """

        title = self.slug
        if self.status == kPASTE_STATUS_PUBLIC and self.title:
            title = self.title
        return title

    def get_snippet (self):
        """
        Gets the snippet if there is one and the status allows it.
        """
        snippet = ""
        if self.status == kPASTE_STATUS_PUBLIC and self.snippet:
            snippet = self.snippet
        return snippet

    def get_url (self):
        return paste.url("%s", self.slug)

    def is_code_viewable (self):
        return self.status == kPASTE_STATUS_PUBLIC

    def is_diffable (self):
        return self.status == kPASTE_STATUS_PUBLIC

    def is_private (self):
        return self.status == kPASTE_STATUS_PRIVATE

    def is_public (self):
        return self.status == kPASTE_STATUS_PUBLIC

class Log (db.Model):
   type = db.StringProperty(choices=["paste_add", "paste_fork", "user_register"])
   user = db.ReferenceProperty(User)
   item1_slug = db.StringProperty()
   item1_name = db.StringProperty()
   item2_slug = db.StringProperty()
   item2_name = db.StringProperty()
