"""Flet interface. Practice rules and persisted scores live in separate modules."""
from __future__ import annotations

import inspect
import math
import random
from collections import Counter

import flet as ft

from .curriculum import Curriculum, Entry
from .practice import CoreSession, DrillSession, MatchSession, normalize_reading
from .progress import Progress, STORAGE_KEY

LIGHT = dict(bg="#F6F5F0", surface="#FFFFFF", ink="#202F2C", muted="#64746E", line="#DDE5DE", accent="#15756C", soft="#E6F2EA", red="#A52E37", redbg="#FCE8E9", green="#17683D", greenbg="#DDF4E5")
DARK = dict(bg="#121D1B", surface="#1D2B27", ink="#E9F2EC", muted="#A9BAB1", line="#354740", accent="#7FD7BE", soft="#263E35", red="#FFAFB5", redbg="#4D272E", green="#9AE2B2", greenbg="#244633")
MODE_NAMES = {"core": "Core quiz", "drill": "Character drill", "match": "Matching game", "flashcards": "Flashcards"}


class App:
    def __init__(self, page: ft.Page, curriculum: Curriculum, preferences=None):
        self.page, self.curriculum = page, curriculum
        self.preferences = preferences or ft.SharedPreferences()
        self.clipboard = ft.Clipboard()
        self.progress = Progress()
        self.screen = "home"
        self.selected: set[str] = {"core-01"}
        self.category_id = "core-01"
        self.category_query, self.category_kind, self.category_page = "", "all", 0
        self.dictionary_query, self.dictionary_sort = "", "frequency"
        self.dictionary_category, self.dictionary_hsk, self.dictionary_page = "all", "all", 0
        self.drill_mode = "typed"
        self.session = None
        self.session_ids: list[str] = []
        self.input_value = ""
        self.feedback = ""
        self.feedback_correct = None
        self.result = None
        self.flash_items: list[Entry] = []
        self.flash_index, self.flash_known, self.flash_revealed = 0, 0, False
        self.match_left = None
        self.busy = False
        self.storage_error = ""
        self.root = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.page.title = "First 1000 · Mandarin & Cantonese"
        self.page.padding = 0
        self.page.fonts = {"Inter": "fonts/Inter.ttf", "Hanzi": "fonts/First1000Hanzi.otf"}
        self.page.theme = ft.Theme(font_family="Inter", color_scheme_seed=LIGHT["accent"])
        self.page.dark_theme = ft.Theme(font_family="Inter", color_scheme_seed=DARK["accent"])
        self.page.on_resize = self.on_resize
        self.page.add(self.root)
        self.breakpoint = self.narrow

    @property
    def language(self):
        return self.progress.settings["language"]

    @property
    def traditional(self):
        return self.progress.settings["traditional"]

    @property
    def colors(self):
        return DARK if self.progress.settings["dark"] else LIGHT

    @property
    def narrow(self):
        return (self.page.width or 1100) < 700

    @property
    def active(self):
        return self.screen in ("core", "drill", "match", "flashcards")

    @property
    def language_label(self):
        return "Cantonese · Jyutping" if self.language == "cantonese" else "Mandarin · Pinyin"

    async def initialize(self):
        try:
            saved = await self.preferences.get(STORAGE_KEY)
            if saved:
                self.progress = Progress.from_json(saved)
        except Exception:
            self.storage_error = "Your saved progress could not be loaded. You can restore a backup in Progress."
        self.render()

    async def save(self):
        try:
            saved = await self.preferences.set(STORAGE_KEY, self.progress.export())
            if saved is False:
                raise RuntimeError("Storage unavailable")
            self.storage_error = ""
        except Exception:
            self.storage_error = "Progress is in memory, but this browser could not save it. Copy a backup from Progress before closing."

    def action(self, callback, *args):
        async def handler(event=None):
            if self.busy:
                return
            self.busy = True
            try:
                result = callback(*args)
                if inspect.isawaitable(result):
                    await result
            except ValueError as error:
                self.feedback, self.feedback_correct = str(error), None
            finally:
                self.busy = False
                self.render()
        return handler

    def event_action(self, callback, extract):
        async def handler(event):
            await self.action(callback, *extract(event))(event)
        return handler

    def on_resize(self, event=None):
        if self.breakpoint != self.narrow:
            self.breakpoint = self.narrow
            self.render()

    def text(self, value, size=16, muted=False, bold=False, hanzi=False, **kwargs):
        return ft.Text(str(value), size=size, color=self.colors["muted" if muted else "ink"],
                       font_family="Hanzi" if hanzi else "Inter", weight=ft.FontWeight.W_600 if bold else ft.FontWeight.W_400, **kwargs)

    def button(self, label, callback, *args, primary=False, disabled=False, icon=None, content=None):
        return ft.Button(content=content or label, on_click=self.action(callback, *args), disabled=disabled, icon=icon,
            color=self.colors["bg"] if primary else self.colors["accent"], bgcolor=self.colors["accent"] if primary else self.colors["soft"],
            elevation=0, style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=18, vertical=14), shape=ft.RoundedRectangleBorder(radius=12)))

    def panel(self, controls, color=None, padding=24, **kwargs):
        return ft.Container(ft.Column(controls, spacing=14), padding=padding, bgcolor=color or self.colors["surface"],
            border=ft.Border.all(1, self.colors["line"]), border_radius=20, **kwargs)

    def tag(self, label):
        return ft.Container(self.text(label, 12, bold=True), padding=ft.Padding.symmetric(horizontal=10, vertical=6), bgcolor=self.colors["soft"], border_radius=8)

    def heading(self, title, subtitle=""):
        return ft.Column([self.text(title, 30 if self.narrow else 36, bold=True), self.text(subtitle, 15, muted=True)] if subtitle else [self.text(title, 32, bold=True)], spacing=6)

    def dropdown(self, label, value, options, change, width=210):
        return ft.Dropdown(label=label, value=value, width=width, options=[ft.DropdownOption(key=k, text=v) for k, v in options], on_select=change,
            border_radius=12, border_color=self.colors["line"], color=self.colors["ink"], bgcolor=self.colors["surface"], text_size=14, menu_height=350)

    def navigate(self, screen):
        self.screen, self.session, self.result = screen, None, None
        self.feedback, self.feedback_correct = "", None
        self.input_value = ""

    async def set_switch(self, key, value):
        if self.active and key != "dark":
            return
        self.progress.settings[key] = value
        await self.save()

    def header(self):
        brand = ft.Row([ft.Container(self.text("千", 28, hanzi=True), width=50, height=50, alignment=ft.Alignment.CENTER, bgcolor=self.colors["soft"], border_radius=14),
            ft.Column([self.text("First 1000", 22, bold=True), self.text("Small sessions. Lasting characters.", 12, muted=True)], spacing=3)], spacing=12)
        switch_style = ft.TextStyle(size=12, color=self.colors["ink"])
        switches = ft.Row([
            ft.Switch(label="Dark", value=self.progress.settings["dark"], label_text_style=switch_style, on_change=self.event_action(self.set_switch, lambda e: ("dark", e.control.value))),
            ft.Switch(label="Cantonese", value=self.language == "cantonese", label_text_style=switch_style, disabled=self.active, on_change=self.event_action(self.set_switch, lambda e: ("language", "cantonese" if e.control.value else "mandarin"))),
            ft.Switch(label="HK traditional", value=self.traditional, label_text_style=switch_style, disabled=self.active, on_change=self.event_action(self.set_switch, lambda e: ("traditional", e.control.value)))], wrap=True, spacing=6)
        nav = ft.Row([self.button(label, self.navigate, screen, primary=self.screen == screen) for label, screen in [
            ("Home", "home"), ("Categories", "categories"), ("Dictionary", "dictionary"), ("Character driller", "drill_setup"), ("Progress", "progress")]], wrap=True, spacing=8)
        return ft.Column([ft.Row([brand, switches], wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, run_spacing=14), nav,
            ft.Row([self.tag(self.language_label), self.tag("HK traditional" if self.traditional else "Simplified")], wrap=True)], spacing=20)

    def render(self):
        self.page.bgcolor = self.colors["bg"]
        self.page.theme_mode = ft.ThemeMode.DARK if self.progress.settings["dark"] else ft.ThemeMode.LIGHT
        builders = {"home": self.home, "categories": self.categories, "category": self.category_detail, "dictionary": self.dictionary,
            "drill_setup": self.drill_setup, "core": self.core, "drill": self.drill, "match": self.match, "flashcards": self.flashcards, "progress": self.progress_view, "result": self.result_view}
        controls = [self.header()]
        if self.storage_error:
            controls.append(self.panel([self.text(self.storage_error, 13)], color=self.colors["redbg"], padding=14))
        controls += [builders[self.screen](), ft.Container(height=12),
            self.text("Character first. Mandarin and Cantonese scores stay separate. HSK labels use the 2012 syllabus.", 11, muted=True),
            self.button("Content sources & notes", self.show_sources)]
        self.root.controls = [ft.Container(ft.Column(controls, spacing=28), width=min(max((self.page.width or 1200)-24, 280), 1160), padding=ft.Padding.symmetric(vertical=24, horizontal=10))]
        self.page.update()

    def home(self):
        summary = self.progress.summary(self.language, self.curriculum)
        hero = self.panel([
            self.tag("YOUR FIRST 1,000 CHARACTERS"),
            self.text("A thousand characters.\nOne small win at a time.", 32 if self.narrow else 46, bold=True),
            self.text("Bring your Mandarin and Cantonese back into your everyday life. Pick a small set, drill it, and earn a perfect-run trophy.", 16, muted=True),
            ft.Row([self.button("Start a 25-character drill", self.start, "drill", ["core-01"], primary=True), self.button("Explore categories", self.navigate, "categories")], wrap=True),
            ft.Row([self.text("學" if self.traditional else "学", 72, hanzi=True), ft.Column([self.text("Characters take the lead.", 18, bold=True), self.text("Pronunciation appears when it helps you learn.", 13, muted=True)])], wrap=True)
        ], color=self.colors["soft"], padding=28)
        values = [(f'{summary["characters"]}/1000', "Characters practised"), (f'{summary["trophies"]}/{len(self.curriculum.categories)}', "Core trophies"),
                  ("—" if summary["accuracy"] is None else f'{summary["accuracy"]:.0%}', "Answer accuracy"), (str(summary["sessions"]), "Completed sessions")]
        stats = ft.ResponsiveRow([self.panel([self.text(value, 27, bold=True), self.text(label, 12, muted=True)], padding=18, col={"xs": 6, "md": 3}) for value, label in values], spacing=12, run_spacing=12)
        features = [
            ("01", "Categories", "93 themed vocabulary sets and 40 character sets. Pick one or mix a few.", "categories"),
            ("02", "General dictionary", "1,231 words and phrases, plus the 1,000 character cards. Search, sort, and read examples.", "dictionary"),
            ("03", "Character driller", "Type a tone-number reading or choose from eight answers. See each character once.", "drill_setup")]
        cards = ft.ResponsiveRow([self.panel([self.text(n, 14, muted=True, bold=True), self.text(title, 22, bold=True), self.text(detail, 14, muted=True), self.button("Open →", self.navigate, screen)], col={"xs":12,"md":4}) for n,title,detail,screen in features], spacing=12, run_spacing=12)
        return ft.Column([hero, stats, cards], spacing=20)

    def filtered_categories(self):
        categories = self.curriculum.categories
        if self.category_kind != "all":
            categories = [x for x in categories if x.kind == self.category_kind or (self.category_kind.isdigit() and x.hsk == int(self.category_kind))]
        if self.category_query.strip():
            query = self.category_query.strip().lower()
            categories = [x for x in categories if query in (x.title + " " + x.description).lower() or any(query in self.curriculum.entries[y].text(self.language, self.traditional) for y in x.entry_ids)]
        return categories

    def select_category(self, category_id, value):
        if value:
            self.selected.add(category_id)
        else:
            self.selected.discard(category_id)

    def select_visible(self, all_selected=True):
        if all_selected:
            self.selected.update(x.id for x in self.filtered_categories())
        else:
            self.selected.clear()

    def search_categories(self):
        self.category_page = 0

    def filter_categories(self, event):
        self.category_kind, self.category_page = event.control.value, 0
        self.render()

    def selection_bar(self, modes=True):
        chars = self.curriculum.selected_characters(self.selected, self.language, self.traditional)
        entries = self.curriculum.selected_entries(self.selected)
        controls = [self.text(f"{len(self.selected)} categories selected · {len(entries)} cards · {len(chars)} unique characters", 14, bold=True)]
        if modes:
            controls.append(ft.Row([self.button(label, self.start, mode, list(self.selected), primary=mode=="core", disabled=not self.selected) for label,mode in
                [("Flashcards", "flashcards"), ("Core quiz", "core"), ("Drill characters", "drill"), ("Matching game", "match")]], wrap=True))
        return self.panel(controls, color=self.colors["soft"], padding=18)

    def category_grid(self):
        matches = self.filtered_categories()
        per_page = 24
        self.category_page = max(0, min(self.category_page, max(0, math.ceil(len(matches)/per_page)-1)))
        controls = []
        for cat in matches[self.category_page*per_page:(self.category_page+1)*per_page]:
            won = self.progress.has_trophy(self.language, cat.id, self.curriculum)
            samples = " · ".join(self.curriculum.entries[x].text(self.language, self.traditional) for x in cat.entry_ids[:4])
            controls.append(self.panel([
                ft.Row([ft.Checkbox(value=cat.id in self.selected, on_change=self.event_action(self.select_category, lambda e, cid=cat.id: (cid, e.control.value))), self.tag("🏆 1/1 core" if won else "0/1 core")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.text(cat.title, 18, bold=True), self.text(f"{len(cat.entry_ids)} cards · " + ("Core characters" if cat.kind=="characters" else "Hong Kong" if cat.kind=="hong_kong" else f"HSK {cat.hsk}"), 12, muted=True),
                self.text(samples, 22, hanzi=True, max_lines=2), self.button("Open category", self.open_category, cat.id)], padding=18, col={"xs":12,"sm":6,"lg":4}))
        return ft.Column([self.text(f"{len(matches)} categories", 13, muted=True), ft.ResponsiveRow(controls, spacing=12, run_spacing=12),
            self.pagination(self.category_page, len(matches), per_page, self.move_category_page)], spacing=16)

    def move_category_page(self, amount):
        self.category_page += amount

    def categories(self):
        query = ft.TextField(value=self.category_query, label="Find a category or character", expand=True, on_change=lambda e: setattr(self,"category_query",e.control.value), on_submit=self.action(self.search_categories), border_radius=12)
        return ft.Column([self.heading("Choose your next small win", "Select several categories to practise their combined vocabulary."),
            ft.Row([query, self.button("Search", self.search_categories)], vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row([self.dropdown("Show", self.category_kind, [("all","All sets"),("characters","First 1000"),("vocabulary","Vocabulary"),("hong_kong","Hong Kong"),*[(str(i),f"HSK {i}") for i in range(1,5)]], self.filter_categories),
                self.button("Select all shown", self.select_visible, True), self.button("Clear selection", self.select_visible, False)], wrap=True),
            self.selection_bar(), self.category_grid()], spacing=20)

    def open_category(self, category_id):
        self.navigate("category")
        self.category_id = category_id

    def category_detail(self):
        cat = self.curriculum.category_map[self.category_id]
        won = self.progress.has_trophy(self.language,cat.id,self.curriculum)
        return ft.Column([self.button("← All categories", self.navigate, "categories"), self.heading(cat.title, cat.description), self.tag("🏆 Core quiz completed · 1/1" if won else "Core quiz · 0/1 completed"),
            ft.Row([self.button(label,self.start,mode,[cat.id],primary=mode=="core") for label,mode in [("Train flashcards","flashcards"),("Write the characters · Core quiz","core"),("Character drill","drill"),("Matching game","match")]], wrap=True),
            self.text("Category dictionary",22,bold=True), *[self.entry_card(self.curriculum.entries[x]) for x in cat.entry_ids]], spacing=18)

    def entry_card(self, entry):
        ex = entry.example(self.language, self.traditional)
        tags = [self.tag("Character card" if entry.kind=="character" else "Hong Kong phrase" if entry.kind=="hong_kong" else f"HSK {entry.hsk}")]
        return self.panel([ft.Row([self.text(entry.text(self.language,self.traditional),30,hanzi=True),*tags], wrap=True, spacing=12),
            self.text(entry.reading(self.language),14,muted=True),self.text(entry.meaning,16),
            *([self.text(entry.data["usage_note"],12,muted=True)] if self.language=="cantonese" and entry.data.get("usage_note") else []),
            self.text(ex["text"],18,hanzi=True),self.text(ex["english"],13,muted=True),
            self.text(("Reference example" if ex["source"]=="Reference" else "Original example" if ex["source"]=="Original" else "Tatoeba example") + " · " + (entry.data.get("cantonese_register", "") if self.language=="cantonese" else "Mandarin"),11,muted=True),
            self.button("Example attribution",self.show_attribution,entry)], padding=18)

    def search_dictionary(self):
        self.dictionary_page=0

    def set_dictionary_filter(self, key, value):
        setattr(self, key, value)
        self.dictionary_page=0
        self.render()

    def move_dictionary_page(self, amount):
        self.dictionary_page+=amount

    def pagination(self, page, count, per_page, move):
        pages=max(1,math.ceil(count/per_page))
        return ft.Row([self.button("← Previous",move,-1,disabled=page<=0),self.text(f"Page {page+1} of {pages}",13,muted=True),self.button("Next →",move,1,disabled=page+1>=pages)], wrap=True)

    def dictionary(self):
        entries=self.curriculum.dictionary(self.dictionary_query,self.language,self.traditional,self.dictionary_sort,self.dictionary_category,self.dictionary_hsk)
        self.dictionary_page=max(0,min(self.dictionary_page,max(0,math.ceil(len(entries)/30)-1)))
        search=ft.TextField(value=self.dictionary_query,label="Search characters, reading, meaning, or category",expand=True,on_change=lambda e:setattr(self,"dictionary_query",e.control.value),on_submit=self.action(self.search_dictionary),border_radius=12)
        return ft.Column([self.heading("Your whole dictionary", "All vocabulary and character cards, with separate language forms and examples."),
            ft.Row([search,self.button("Search",self.search_dictionary)], vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row([self.dropdown("Sort by",self.dictionary_sort,[("frequency","Frequency"),("hsk","HSK level"),("alphabetical","Reading A–Z"),("meaning","English A–Z"),("category","Category")],lambda e:self.set_dictionary_filter("dictionary_sort",e.control.value)),
                self.dropdown("Level",self.dictionary_hsk,[("all","All levels"),*[(str(i),f"HSK {i}") for i in range(1,5)],("hong_kong","Hong Kong")],lambda e:self.set_dictionary_filter("dictionary_hsk",e.control.value)),
                self.dropdown("Category",self.dictionary_category,[("all","All categories"),*[(x.id,x.title) for x in self.curriculum.categories]],lambda e:self.set_dictionary_filter("dictionary_category",e.control.value),width=300)],wrap=True),
            self.text(f"{len(entries):,} entries · frequency uses source ranks; unranked phrases appear last",13,muted=True),
            self.pagination(self.dictionary_page,len(entries),30,self.move_dictionary_page),
            *[self.entry_card(x) for x in entries[self.dictionary_page*30:(self.dictionary_page+1)*30]],
            self.pagination(self.dictionary_page,len(entries),30,self.move_dictionary_page)],spacing=18)

    def set_drill_mode(self, mode):
        self.drill_mode=mode

    def drill_setup(self):
        return ft.Column([self.heading("Character driller", "Each unique displayed character appears once. Recorded alternative readings are accepted."),
            ft.Row([self.button("Type the reading",self.set_drill_mode,"typed",primary=self.drill_mode=="typed"),self.button("8-choice mode",self.set_drill_mode,"choice",primary=self.drill_mode=="choice")],wrap=True),
            self.selection_bar(False),self.button("Start drill →",self.start,"drill",list(self.selected),primary=True,disabled=not self.selected),
            self.button("Choose categories",self.navigate,"categories"),self.text("Current selected sets",20,bold=True),
            ft.Row([self.tag(self.curriculum.category_map[x].title) for x in self.selected],wrap=True),
            self.text("Mandarin: peng2, péng, lü4, or lv4. Cantonese: numbered Jyutping, such as pang4. Your language and script stay fixed during a session.",14,muted=True)],spacing=20)

    def start(self, mode, category_ids):
        ids=[x.id for x in self.curriculum.categories if x.id in set(category_ids)]
        entries=self.curriculum.selected_entries(ids)
        self.feedback,self.feedback_correct,self.input_value="",None,""
        self.result=None
        if mode=="core":
            self.session=CoreSession(entries,self.language,self.traditional)
        elif mode=="drill":
            chars=self.curriculum.selected_characters(ids,self.language,self.traditional)
            self.session=DrillSession(chars,self.language,list(self.curriculum.characters.values()))
        elif mode=="match":
            self.session=MatchSession(entries,self.language,self.traditional)
            self.match_left=None
        else:
            if not entries:
                raise ValueError("Select at least one category")
            self.flash_items=list(entries)
            random.shuffle(self.flash_items)
            self.flash_index,self.flash_known,self.flash_revealed=0,0,False
            self.session=None
        self.session_ids,self.screen=ids,mode

    def session_top(self, title, current, total):
        return ft.Column([ft.Row([self.text(title,26,bold=True),self.button("Leave session",self.navigate,"categories")],wrap=True,alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.text(f"{current}/{total}",14,muted=True),ft.ProgressBar(value=(current-1)/total,color=self.colors["accent"],bgcolor=self.colors["line"],height=6)],spacing=12)

    def feedback_card(self):
        if not self.feedback:
            return ft.Container()
        color=self.colors["greenbg"] if self.feedback_correct else self.colors["redbg"] if self.feedback_correct is False else self.colors["soft"]
        return self.panel([self.text(self.feedback,15,hanzi=any("\u3400"<=x<="\u9fff" for x in self.feedback))],color=color,padding=16)

    async def answer_core(self):
        session=self.session
        answer=session.answer(self.input_value)
        self.progress.record_answer(self.language,answer.correct)
        self.feedback_correct=answer.correct
        if answer.correct:
            self.input_value=""
            self.feedback="Correct. Keep going!"
            if session.finished:
                earned=self.progress.finish(self.language,"core",len(session.items),len(session.items),session.attempts,self.session_ids,session.perfect,self.curriculum)
                self.complete("core",len(session.items),len(session.items),session.attempts,session.perfect,earned,session.answers)
        else:
            self.feedback=f"Try this one again. The answer is {' / '.join(answer.accepted)}. This run has a mistake; finish it for practice, then try a perfect run."
        await self.save()

    def answer_field(self, label, handler, hanzi=False, disabled=False):
        return ft.TextField(value=self.input_value,label=label,autofocus=True,disabled=disabled,autocorrect=False,enable_suggestions=hanzi,
            text_style=ft.TextStyle(font_family="Hanzi" if hanzi else "Inter",size=24 if hanzi else 18,color=self.colors["ink"]),
            on_change=lambda e:setattr(self,"input_value",e.control.value),on_submit=self.action(handler),border_radius=14,border_color=self.colors["line"])

    def core(self):
        session=self.session
        entry=session.current
        return ft.Column([self.session_top("Write the characters · Core quiz",session.index+1,len(session.items)),
            self.panel([self.tag("ENGLISH → CHARACTERS"),self.text(entry.meaning,25,bold=True),self.text(f"Write {len(entry.text(self.language,self.traditional))} Chinese character(s).",14,muted=True),
                self.answer_field("Your answer in Chinese",self.answer_core,hanzi=True),self.button("Check answer",self.answer_core,primary=True),self.feedback_card(),
                self.text(f"{session.mistakes} mistakes · {session.attempts} attempts · all questions stay fixed",12,muted=True),
                self.text("A perfect completed run earns a trophy for every selected category. After a wrong answer, correct the same question to continue.",13,muted=True)],padding=28)],spacing=20)

    async def answer_drill(self, value=None):
        session=self.session
        char=session.current
        answer=session.answer(value if value is not None else self.input_value)
        self.progress.record_answer(self.language,answer.correct,char)
        self.feedback_correct=answer.correct
        self.feedback=("Correct! " if answer.correct else "The accepted reading(s): ")+" / ".join(answer.accepted)
        await self.save()

    async def next_drill(self):
        session=self.session
        session.advance()
        self.feedback,self.feedback_correct,self.input_value="",None,""
        if session.finished:
            self.progress.finish(self.language,"drill",len(session.items),session.correct_count,len(session.answers),self.session_ids)
            self.complete("drill",len(session.items),session.correct_count,len(session.answers),False,[],session.answers)
            await self.save()

    def drill(self):
        session=self.session
        char=session.current
        answer_controls=[]
        if self.drill_mode=="choice":
            options=[]
            for reading in session.options():
                valid=normalize_reading(reading,self.language) in {normalize_reading(x,self.language) for x in char.readings(self.language)}
                chosen=bool(session.pending and session.pending.given==reading)
                bg=self.colors["greenbg"] if session.pending and valid else self.colors["redbg"] if chosen else self.colors["surface"]
                options.append(ft.Container(self.button(reading,self.answer_drill,reading,disabled=session.pending is not None),bgcolor=bg,padding=6,border_radius=14,col={"xs":6,"md":3},border=ft.Border.all(2,self.colors["green"] if session.pending and valid else self.colors["red"] if chosen else self.colors["line"])))
            answer_controls=[ft.ResponsiveRow(options,spacing=12,run_spacing=12)]
        else:
            label="Jyutping + tone number" if self.language=="cantonese" else "Pinyin + tone number (peng2)"
            answer_controls=[self.answer_field(label,self.answer_drill,disabled=session.pending is not None),self.button("Check reading",self.answer_drill,primary=True,disabled=session.pending is not None)]
        return ft.Column([self.session_top("Character driller",session.index+1,len(session.items)),
            self.panel([self.text(char.glyph,100,hanzi=True,text_align=ft.TextAlign.CENTER),self.text("Recall the pronunciation",15,muted=True),*answer_controls,self.feedback_card(),
                self.button("Finish drill" if session.index+1==len(session.items) else "Next character →",self.next_drill,primary=True,disabled=session.pending is None),
                self.text(f"{session.correct_count}/{len(session.answers)} correct so far",13,muted=True)],padding=28)],spacing=20)

    def reveal_flashcard(self):
        self.flash_revealed=True

    async def rate_flashcard(self, known):
        if not self.flash_revealed:
            return
        self.flash_known+=int(known)
        self.flash_index+=1
        self.progress.state(self.language)["flashcards"]+=1
        self.flash_revealed=False
        if self.flash_index==len(self.flash_items):
            self.progress.finish(self.language,"flashcards",len(self.flash_items),self.flash_known,len(self.flash_items),self.session_ids)
            self.complete("flashcards",len(self.flash_items),self.flash_known,len(self.flash_items),False,[],[])
        await self.save()

    def flashcards(self):
        entry=self.flash_items[self.flash_index]
        controls=[self.text(entry.text(self.language,self.traditional),65,hanzi=True),self.text("Try to recall the reading and meaning before revealing.",14,muted=True)]
        if self.flash_revealed:
            ex=entry.example(self.language,self.traditional)
            controls += [self.text(entry.reading(self.language),20),self.text(entry.meaning,22,bold=True),self.text(ex["text"],20,hanzi=True),self.text(ex["english"],14,muted=True),
                ft.Row([self.button("Still learning",self.rate_flashcard,False),self.button("I knew it",self.rate_flashcard,True,primary=True)],wrap=True)]
        else:
            controls.append(self.button("Reveal reading & meaning",self.reveal_flashcard,primary=True))
        return ft.Column([self.session_top("Train flashcards",self.flash_index+1,len(self.flash_items)),self.panel(controls,padding=28),self.text("Flashcard ratings are self-assessments. They do not count toward graded accuracy or core trophies.",13,muted=True)],spacing=20)

    def choose_match_left(self, entry_id):
        self.match_left=entry_id
        self.feedback="Now choose its English meaning."
        self.feedback_correct=None

    async def choose_match_right(self, entry_id):
        if self.match_left is None:
            raise ValueError("Choose a character card first")
        session=self.session
        answer=session.answer(self.match_left,entry_id)
        self.progress.record_answer(self.language,answer.correct)
        self.feedback="Matched!" if answer.correct else "Those do not match. Try another pair."
        self.feedback_correct=answer.correct
        self.match_left=None
        if session.finished:
            self.progress.finish(self.language,"match",len(session.items),len(session.items),session.attempts,self.session_ids)
            self.complete("match",len(session.items),len(session.items),session.attempts,False,[],session.answers)
        await self.save()

    def match(self):
        session=self.session
        left=[]
        for x in session.left:
            label=self.text(x.text(self.language,self.traditional),26,hanzi=True)
            if x.id==self.match_left:
                label.color=self.colors["bg"]
            left.append(self.button("",self.choose_match_left,x.id,primary=x.id==self.match_left,disabled=x.id in session.matched,content=label))
        right=[self.button(x.meaning,self.choose_match_right,x.id,disabled=x.id in session.matched) for x in session.right]
        return ft.Column([self.heading("Match characters to meaning", "Choose a character card, then its English match."),
            self.text(f"{len(session.matched)}/{len(session.items)} pairs · {session.attempts} attempts",14,muted=True),
            ft.Row([ft.Column(left,expand=True,spacing=12),ft.Column(right,expand=True,spacing=12)],vertical_alignment=ft.CrossAxisAlignment.START,spacing=16),self.feedback_card(),
            self.button("Leave game",self.navigate,"categories")],spacing=20)

    def complete(self, mode, total, correct, attempts, perfect, earned, answers):
        self.result=dict(mode=mode,total=total,correct=correct,attempts=attempts,perfect=perfect,earned=earned,answers=answers,ids=list(self.session_ids))
        self.screen="result"

    def result_view(self):
        r=self.result
        score=r["correct"]/r["attempts"] if r["attempts"] else 0
        headline="Perfect run. Trophy earned!" if r["perfect"] else "A small session, completed."
        controls=[self.tag(MODE_NAMES[r["mode"]].upper()),self.text(headline,30,bold=True),self.text(f"{score:.0%}",58,bold=True),
            self.text(f'{r["correct"]}/{r["total"]} '+("self-rated known" if r["mode"]=="flashcards" else "correct")+f' · {r["attempts"]} attempts',16,muted=True)]
        if r["mode"]=="core":
            controls.append(self.text(f'{len(r["earned"])} new category trophies. All {len(r["ids"])} selected categories have a completed core quiz.' if r["perfect"] else "You corrected every question. Try again with no mistakes to earn the category trophy.",15))
        controls.append(ft.Row([self.button("Practise again",self.start,r["mode"],r["ids"],primary=True),self.button("Choose categories",self.navigate,"categories"),self.button("View progress",self.navigate,"progress")],wrap=True))
        wrong={a.item_id:a for a in r["answers"] if not a.correct}
        if wrong:
            controls += [self.text("Review missed answers",20,bold=True)]
            for a in list(wrong.values())[:40]:
                name=a.item_id if r["mode"]=="drill" else self.curriculum.entries[a.item_id].text(self.language,self.traditional)
                expected=" / ".join(a.accepted) if r["mode"]!="match" else self.curriculum.entries[a.item_id].meaning
                controls.append(self.text(f"{name} → {expected}",17,hanzi=True))
        return self.panel(controls,padding=28)

    def progress_view(self):
        summary=self.progress.summary(self.language,self.curriculum)
        state=self.progress.state(self.language)
        trophies=[cat for cat in self.curriculum.categories if self.progress.has_trophy(self.language,cat.id,self.curriculum)]
        controls=[self.heading("Your progress", self.language_label + " · saved in this browser; copy a backup to move devices"),
            self.panel([self.text(f'{summary["characters"]} of 1,000 target characters practised',25,bold=True),ft.ProgressBar(value=summary["characters"]/1000,color=self.colors["accent"]),
                self.text(f'{summary["trophies"]} core trophies · {summary["attempts"]} graded attempts · '+("no graded answers yet" if summary["accuracy"] is None else f'{summary["accuracy"]:.1%} accuracy'),15),
                self.text(f'{state["flashcards"]} flashcards reviewed. “Practised” counts characters attempted in drills, including their traditional forms.',13,muted=True)]),
            ft.Row([self.button("Copy / view progress backup",self.show_export,primary=True),self.button("Restore backup",self.show_import)],wrap=True),
            self.text("Core quiz trophies",22,bold=True),ft.Row([self.tag("🏆 "+cat.title) for cat in trophies],wrap=True) if trophies else self.text("Your first trophy is waiting. Complete one core quiz with no mistakes.",15,muted=True),
            self.text("Recent completed sessions",22,bold=True)]
        for row in reversed(state["sessions"][-12:]):
            score=row["correct"]/row["attempts"] if row["attempts"] else 0
            controls.append(self.panel([self.text(MODE_NAMES[row["mode"]],17,bold=True),self.text(f'{row["correct"]}/{row["total"]} · {score:.0%} · {row["finished_at"][:16].replace("T"," ")} UTC',13,muted=True)],padding=16))
        return ft.Column(controls,spacing=20)

    def close_dialog(self):
        self.page.pop_dialog()

    def dialog(self,title,controls,actions=None):
        self.page.show_dialog(ft.AlertDialog(title=self.text(title,22,bold=True),content=ft.Container(ft.Column(controls,spacing=14,tight=True,scroll=ft.ScrollMode.AUTO),width=min((self.page.width or 800)-100,650),height=430),
            bgcolor=self.colors["surface"],actions=actions or [self.button("Close",self.close_dialog)],scrollable=False))

    def show_export(self):
        backup=self.progress.export()
        async def copy_backup():
            await self.clipboard.set(backup)
            self.backup_notice.value="Copied. Save this JSON in a file for safekeeping."
            self.page.update()
        self.backup_notice=self.text("The backup includes both languages, trophies, scores, and settings.",13,muted=True)
        self.dialog("Progress backup",[self.backup_notice,ft.TextField(value=backup,multiline=True,min_lines=8,max_lines=12,read_only=True,text_size=11)],
            [self.button("Copy JSON",copy_backup,primary=True),self.button("Close",self.close_dialog)])

    def show_import(self):
        field=ft.TextField(label="Paste a First 1000 JSON backup",multiline=True,min_lines=8,max_lines=12,text_size=12)
        notice=self.text("Restoring replaces this browser’s saved progress with the backup, for both languages.",13,muted=True)
        async def restore():
            try:
                restored=Progress.from_json(field.value)
            except ValueError as error:
                notice.value=str(error)
                self.page.update()
                return
            self.progress=restored
            await self.save()
            self.close_dialog()
        self.dialog("Restore progress",[notice,field],[self.button("Restore this backup",restore,primary=True),self.button("Cancel",self.close_dialog)])

    def show_attribution(self,entry):
        ex=entry.example(self.language,self.traditional)
        self.dialog("Example source",[self.text(ex["text"],22,hanzi=True),self.text(ex["english"],16),self.text(ex["attribution"],13),self.text("License: "+ex["license"],13,muted=True),
            self.text("Character conversion adapts the source spelling to the selected simplified or Hong Kong traditional script.",13,muted=True)])

    def show_sources(self):
        coverage=self.curriculum.meta["example_coverage"]
        self.dialog("Curriculum sources & notes",[
            self.text("1,000 frequency-ranked characters · 1,193 unique HSK words · 38 Hong Kong phrases · 133 categories",17,bold=True),
            self.text("This edition reconstructs the saved requirements. The interrupted conversation’s source files were unavailable.",13,muted=True),
            self.text("HSK 2012 levels 1–4: clem109/hsk-vocabulary and drkameleon/complete-hsk-vocabulary, with CC-CEDICT definitions (CC BY-SA 3.0). Themes are editorial groupings.",13),
            self.text("HanziDB / Jun Da provides the character frequency ranking. Unihan (Unicode 18) and Pleco’s CC-Canto provide character readings. Pleco content: © 2015–2017 Pleco Inc., CC BY-SA 3.0.",13),
            self.text("Mandarin and Cantonese Tatoeba examples retain the authors and sentence IDs in each entry. License: CC BY 2.0 FR. Uncovered items use clearly marked original reference examples.",13),
            self.text(f'Example sources — Mandarin: {coverage["mandarin"]}; Cantonese: {coverage["cantonese"]}.',12,muted=True),
            self.text(self.curriculum.meta["cantonese_note"],13),
            self.text("Full notices, source URLs, and build provenance are included with the downloadable project. Font: Noto Sans CJK HK and Inter, SIL OFL 1.1.",13)])


async def main(page: ft.Page):
    app=App(page,Curriculum.load())
    await app.initialize()
