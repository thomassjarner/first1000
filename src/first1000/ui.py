"""Flet interface. Practice rules and persisted scores live in separate modules."""
from __future__ import annotations

import inspect
import math
import random
from collections import Counter

import flet as ft

from .curriculum import Curriculum, Entry
from .practice import CoreSession, DrillSession, MatchSession, normalize_reading, SentenceSession
from .progress import Progress, now
from .character_framework import groups as character_groups,session_key,snapshot,restore
from .storage import ProgressStore

LIGHT = dict(bg="#F6F5F0", surface="#FFFFFF", ink="#202F2C", muted="#64746E", line="#DDE5DE", accent="#15756C", soft="#E6F2EA", red="#A52E37", redbg="#FCE8E9", green="#17683D", greenbg="#DDF4E5")
DARK = dict(bg="#121D1B", surface="#1D2B27", ink="#E9F2EC", muted="#A9BAB1", line="#354740", accent="#7FD7BE", soft="#263E35", red="#FFAFB5", redbg="#4D272E", green="#9AE2B2", greenbg="#244633")
LIGHT.update(amber="#8C5D00",amberbg="#FFF1CC")
DARK.update(amber="#F2C66D",amberbg="#453719")
MODE_NAMES = {"core": "Recognition quiz", "drill": "Character drill", "match": "Matching game", "flashcards": "Flashcards", "sentence": "Sentence practice"}


class App:
    def __init__(self, page: ft.Page, curriculum: Curriculum, preferences=None):
        self.ready = False
        curriculum.add_everyday_content()
        self.page, self.curriculum = page, curriculum
        self.preferences = preferences or ft.SharedPreferences()
        self.progress_store = ProgressStore(self.preferences)
        self.clipboard = ft.Clipboard()
        self.progress = Progress()
        self.screen = "home"
        self.selected: set[str] = {"situation-paying-the-bill"}
        self.category_id = "situation-paying-the-bill"
        self.category_query, self.category_kind, self.category_page = "", "all", 0
        self.category_theme, self.category_sort = "all", "recommended"
        self.dictionary_query, self.dictionary_sort = "", "frequency"
        self.dictionary_category, self.dictionary_hsk, self.dictionary_page = "all", "all", 0
        self.dictionary_reverse = False
        self.dictionary_learned = "all"
        self.character_group_id="common-1000"
        self.character_session_group=None
        self.character_group_cache={}
        self.dictionary_known_characters=False
        self.drill_mode = "typed"
        self.drill_filter = "all"
        self.drill_page = 0
        self.review_page = 0
        self.learned_page = 0
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
        self.root = ft.Column(tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.page.title = "First 1000 · Mandarin & Cantonese"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.page.scroll = ft.Scrollbar(thumb_visibility=True, interactive=True, thickness=8, orientation=ft.ScrollbarOrientation.RIGHT)
        self.page.fonts = {"Inter": "fonts/Inter.ttf", "Hanzi": "fonts/First1000Hanzi.otf"}
        self.page.theme = ft.Theme(font_family="Inter", color_scheme_seed=LIGHT["accent"])
        self.page.dark_theme = ft.Theme(font_family="Inter", color_scheme_seed=DARK["accent"])
        self.page.on_resize = self.on_resize
        self.page.on_keyboard_event = self.on_keyboard
        self.page.add(self.root)
        self.layout_size = self.viewport_size

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
        return self.screen in ("core", "drill", "match", "flashcards", "sentence")

    @property
    def language_label(self):
        return "Cantonese · Jyutping" if self.language == "cantonese" else "Mandarin · Pinyin"

    async def initialize(self):
        self.progress = await self.progress_store.load()
        self.storage_error = self.progress_store.message
        self.progress.migrate_drill_outcomes(self.curriculum)
        self.progress.migrate_frameworks(self.curriculum)
        if self.language == "cantonese":
            self.selected = {"cant-core-" + cid[-2:] if cid.startswith("core-") else cid for cid in self.selected}
        self.ready = True
        self.render()

    async def save(self):
        saved = await self.progress_store.save(self.progress)
        self.storage_error = self.progress_store.message
        return saved

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

    @property
    def viewport_size(self):
        return (self.page.width or 1100, getattr(self.page, "height", None) or 800)

    @property
    def content_width(self):
        # Reserve a gutter for the viewport scrollbar even on very small screens.
        return min(1160, max(160, self.viewport_size[0] - 32))

    def on_resize(self, event=None):
        if self.ready and self.layout_size != self.viewport_size:
            self.layout_size = self.viewport_size
            self.render()

    def column(self, controls, **kwargs):
        # Content must shrink to its children inside the page's scroll view.
        kwargs.setdefault("tight", True)
        return ft.Column(controls, **kwargs)

    async def on_keyboard(self, event):
        if getattr(event, "key", "") != "Enter" or any(getattr(event, key, False) for key in ("ctrl", "alt", "meta", "shift")):
            return
        if self.ready and self.screen == "core" and self.session.pending is not None:
            await self.action(self.next_core)()
        elif self.ready and self.screen == "drill" and self.drill_mode == "choice":
            await self.action(self.submit_drill)()

    def text(self, value, size=16, muted=False, bold=False, hanzi=False, **kwargs):
        return ft.Text(str(value), size=size, color=self.colors["muted" if muted else "ink"],
                       font_family="Hanzi" if hanzi else "Inter", weight=ft.FontWeight.W_600 if bold else ft.FontWeight.W_400, **kwargs)

    def button(self, label, callback, *args, primary=False, disabled=False, icon=None, content=None):
        return ft.Button(content=content or label, on_click=self.action(callback, *args), disabled=disabled, icon=icon,
            color=self.colors["bg"] if primary else self.colors["accent"], bgcolor=self.colors["accent"] if primary else self.colors["soft"],
            elevation=0, style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=18, vertical=14), shape=ft.RoundedRectangleBorder(radius=12)))

    def panel(self, controls, color=None, padding=24, **kwargs):
        return ft.Container(self.column(controls, spacing=14), padding=padding, bgcolor=color or self.colors["surface"],
            border=ft.Border.all(1, self.colors["line"]), border_radius=20, **kwargs)

    def tag(self, label):
        return ft.Container(self.text(label, 12, bold=True), padding=ft.Padding.symmetric(horizontal=10, vertical=6), bgcolor=self.colors["soft"], border_radius=8)

    def heading(self, title, subtitle=""):
        return self.column([self.text(title, 30 if self.narrow else 36, bold=True), self.text(subtitle, 15, muted=True)] if subtitle else [self.text(title, 32, bold=True)], spacing=6)

    def dropdown(self, label, value, options, change, width=210):
        return ft.Dropdown(label=label, value=value, width=min(width, max(120,self.content_width-20)), options=[ft.DropdownOption(key=k, text=v) for k, v in options], on_select=change,
            border=ft.OutlineInputBorder(border_radius=12, side=ft.BorderSide(color=self.colors["line"])), color=self.colors["ink"], bgcolor=self.colors["surface"], text_size=14, menu_height=350)

    def navigate(self, screen):
        self.screen, self.session, self.result = screen, None, None
        self.feedback, self.feedback_correct = "", None
        self.input_value = ""

    async def set_switch(self, key, value):
        if self.active and key != "dark":
            return
        if key == "language":
            self.selected = {("cant-core-" + cid[-2:]) if value == "cantonese" and cid.startswith("core-") else ("core-" + cid[-2:]) if value == "mandarin" and cid.startswith("cant-core-") else cid for cid in self.selected}
            if value == "cantonese" and self.category_id.startswith("core-"):
                self.category_id = "cant-core-" + self.category_id[-2:]
            elif value == "mandarin" and self.category_id.startswith("cant-core-"):
                self.category_id = "core-" + self.category_id[-2:]
            self.dictionary_category = "all"
            self.category_kind, self.category_theme, self.category_page = "all", "all", 0
        self.progress.settings[key] = value
        await self.save()

    def header(self):
        brand = ft.Row([ft.Container(self.text("千", 28, hanzi=True), width=50, height=50, alignment=ft.Alignment.CENTER, bgcolor=self.colors["soft"], border_radius=14),
            self.column([self.text("First 1000", 22, bold=True), self.text("Small sessions. Lasting characters.", 12, muted=True)], spacing=3, width=max(120,min(self.content_width-82,280)))], spacing=12, tight=True)
        switch_style = ft.TextStyle(size=12, color=self.colors["ink"])
        switches = ft.Row([
            ft.Switch(label="Dark", value=self.progress.settings["dark"], label_text_style=switch_style, on_change=self.event_action(self.set_switch, lambda e: ("dark", e.control.value))),
            ft.Switch(label="Cantonese", value=self.language == "cantonese", label_text_style=switch_style, disabled=self.active, on_change=self.event_action(self.set_switch, lambda e: ("language", "cantonese" if e.control.value else "mandarin"))),
            ft.Switch(label="Traditional", value=self.traditional, label_text_style=switch_style, disabled=self.active, on_change=self.event_action(self.set_switch, lambda e: ("traditional", e.control.value)))], wrap=True, spacing=6)
        nav = ft.Row([self.button(label, self.navigate, screen, primary=self.screen == screen) for label, screen in [
            ("Home", "home"), ("Categories", "categories"), ("Dictionary", "dictionary"), ("Character driller", "drill_setup"), ("Sentences", "sentence_setup"), ("Progress", "progress")]], wrap=True, spacing=8)
        return self.column([(self.column([brand,switches],spacing=12) if self.narrow else ft.Row([brand,switches],wrap=True,alignment=ft.MainAxisAlignment.SPACE_BETWEEN,run_spacing=14)), nav,
            ft.Row([self.tag(self.language_label), self.tag("Traditional" if self.traditional else "Simplified")], wrap=True)], spacing=20)

    def render(self):
        self.page.bgcolor = self.colors["bg"]
        self.page.theme_mode = ft.ThemeMode.DARK if self.progress.settings["dark"] else ft.ThemeMode.LIGHT
        builders = {"home": self.home, "categories": self.categories, "category": self.category_detail, "dictionary": self.dictionary,
            "drill_setup": self.drill_setup, "character_group": self.character_group_view, "core": self.core, "drill": self.drill, "match": self.match, "flashcards": self.flashcards, "progress": self.progress_view, "result": self.result_view, "sentence_setup": self.sentence_setup, "sentence": self.sentence}
        controls = [self.header()]
        if self.storage_error:
            controls.append(self.panel([self.text(self.storage_error, 13)], color=self.colors["redbg"], padding=14))
        controls += [builders[self.screen](), ft.Container(height=12),
            self.text("First 1000 · v0.5.0 · Mandarin and Cantonese scores stay separate. HSK labels use the 2012 syllabus.", 11, muted=True),
            self.button("Content sources & notes", self.show_sources)]
        self.root.controls = [ft.Container(self.column(controls, spacing=24, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), width=self.content_width, padding=ft.Padding.symmetric(vertical=24, horizontal=10))]
        self.page.update()

    def home(self):
        summary = self.progress.summary(self.language, self.curriculum)
        hero = self.panel([
            self.tag("YOUR FIRST 1,000 CHARACTERS"),
            self.text("A thousand characters.\nOne small win at a time.", 32 if self.narrow else 46, bold=True),
            self.text("Bring your Mandarin and Cantonese back into your everyday life. Pick a small set, drill it, and earn a perfect-run trophy.", 16, muted=True),
            ft.Row([self.button("Open character tests",self.navigate,"drill_setup",primary=True), self.button("Explore categories", self.navigate, "categories")], wrap=True),
            ft.Row([self.text("學" if self.traditional else "学", 72, hanzi=True), self.column([self.text("Characters take the lead.", 18, bold=True), self.text("Pronunciation appears when it helps you learn.", 13, muted=True)])], wrap=True)
        ], color=self.colors["soft"], padding=28)
        values=[(str(len(self.progress.state(self.language)["character_learning"])),"Characters learned by typing"),(str(len(self.progress.state(self.language)["word_learning"])),"Words / phrases marked learned"),(str(sum(not value["completed"] for value in self.progress.state(self.language)["character_sessions"].values())),"Character tests to resume")]
        stats = ft.ResponsiveRow([self.panel([self.text(value, 27, bold=True), self.text(label, 12, muted=True)], padding=18, col={"xs": 6, "md": 3}) for value, label in values], spacing=12, run_spacing=12)
        features = [
            ("01", "Categories", "Browse situations, topics, and language-specific character sets. Pick one or mix a few.", "categories"),
            ("02", "General dictionary", "Words and phrases only. Search, sort, mark learned, and read examples.", "dictionary"),
            ("03", "Character driller", "Type a tone-number reading or choose from eight answers. See each character once.", "drill_setup")]
        cards = ft.ResponsiveRow([self.panel([self.text(n, 14, muted=True, bold=True), self.text(title, 22, bold=True), self.text(detail, 14, muted=True), self.button("Open →", self.navigate, screen)], col={"xs":12,"md":4}) for n,title,detail,screen in features], spacing=12, run_spacing=12)
        return self.column([hero, stats, cards], spacing=20)

    def visible_categories(self):
        return [cat for cat in self.curriculum.categories if cat.kind in ("vocabulary","hong_kong","situations")]

    def category_title(self, cat):
        return cat.title.replace("Hong Kong · ", "Everyday · ")

    def filtered_categories(self):
        categories = self.visible_categories()
        if self.category_kind != "all":
            categories = [cat for cat in categories if cat.kind == self.category_kind or (self.category_kind == "characters" and cat.kind == "cantonese_characters") or (self.category_kind.isdigit() and cat.hsk == int(self.category_kind))]
        if self.category_theme != "all":
            categories = [cat for cat in categories if cat.theme == self.category_theme]
        query = self.category_query.strip().lower()
        if query:
            categories = [cat for cat in categories if query in (self.category_title(cat) + " " + cat.theme + " " + cat.description).lower() or any(query in (self.curriculum.entries[eid].text(self.language, self.traditional) + " " + self.curriculum.entries[eid].meaning).lower() for eid in cat.entry_ids)]
        if self.category_sort == "name":
            return sorted(categories, key=lambda cat: self.category_title(cat).lower())
        if self.category_sort == "size":
            return sorted(categories, key=lambda cat: (len(self.curriculum.practice_entries([cat.id])), self.category_title(cat)))
        if self.category_sort == "unfinished":
            return sorted(categories, key=lambda cat: (self.progress.has_trophy(self.language, cat.id, self.curriculum), self.category_title(cat)))
        order = {"situations": 0, "cantonese_characters": 1, "characters": 1, "hong_kong": 2, "vocabulary": 3}
        return sorted(categories, key=lambda cat: (order.get(cat.kind, 9), cat.hsk or 0, cat.title))

    def set_category_filter(self, key, value):
        setattr(self, key, value)
        self.category_page = 0

    def reset_category_filters(self):
        self.category_query, self.category_kind, self.category_theme = "", "all", "all"
        self.category_sort, self.category_page = "recommended", 0

    def select_category(self, category_id, value):
        if value:
            self.selected.add(category_id)
        else:
            self.selected.discard(category_id)

    def pick_all(self):
        self.selected = {cat.id for cat in self.visible_categories()}

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
        chars = self.curriculum.selected_characters(self.selected, self.language, self.traditional, enriched=True)
        entries = self.curriculum.practice_entries(self.selected)
        controls = [self.text(f"{len(self.selected)} word/phrase categories selected · {len(entries)} cards",14,bold=True)]
        if modes:
            controls.append(ft.Row([self.button(label, self.start, mode, list(self.selected), primary=mode=="core", disabled=not self.selected) for label,mode in
                [("Flashcards", "flashcards"), ("Recognition quiz", "core"), ("Matching game", "match")]], wrap=True))
        if modes:
            controls.append(self.button("Practise sentence meanings", self.start, "sentence", list(self.selected), disabled=not any(entry.kind == "sentence" for entry in entries)))
        return self.panel(controls, color=self.colors["soft"], padding=18)

    def category_grid(self):
        matches=self.filtered_categories()
        per_page=16
        self.category_page=max(0,min(self.category_page,max(0,math.ceil(len(matches)/per_page)-1)))
        rows=[]
        for cat in matches[self.category_page*per_page:(self.category_page+1)*per_page]:
            won=self.progress.has_trophy(self.language,cat.id,self.curriculum)
            sample=" · ".join(self.curriculum.entries[eid].text(self.language,self.traditional) for eid in cat.entry_ids[:2])
            checkbox=ft.Checkbox(value=cat.id in self.selected,on_change=self.event_action(self.select_category,lambda e,cid=cat.id:(cid,e.control.value)))
            label=self.column([self.text(self.category_title(cat),17,bold=True),self.text(f"{cat.theme} · {len(self.curriculum.practice_entries([cat.id]))} cards"+(" · 🏆" if won else ""),12,muted=True)],expand=True,spacing=4)
            preview=self.text(sample,15,hanzi=True,max_lines=2)
            opened=self.button("Open",self.open_category,cat.id)
            if self.narrow:
                content=self.column([ft.Row([checkbox,label]),preview,opened],spacing=6)
            else:
                label.controls.append(preview)
                content=ft.Row([checkbox,label,opened])
            rows.append(ft.Container(content,padding=12,border=ft.Border.only(bottom=ft.BorderSide(width=1,color=self.colors["line"]))))
        return self.column([self.text(f"{len(matches)} categories",13,muted=True),self.pagination(self.category_page,len(matches),per_page,self.move_category_page),*rows,self.pagination(self.category_page,len(matches),per_page,self.move_category_page)],spacing=8,horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def move_category_page(self, amount):
        self.category_page += amount

    def categories(self):
        query = ft.TextField(value=self.category_query, label="Search situations, topics, or meanings", height=56, col={"xs":12,"md":9}, on_change=lambda e:setattr(self,"category_query",e.control.value), on_submit=self.action(self.search_categories), border=ft.OutlineInputBorder(border_radius=12))
        search_button = self.button("Search", self.search_categories)
        search_button.col = {"xs":12,"md":3}
        themes = sorted({cat.theme for cat in self.visible_categories()})
        topic = self.dropdown("Topic", self.category_theme, [("all","All topics"),*[(theme,theme) for theme in themes]], self.event_action(self.set_category_filter,lambda e:("category_theme",e.control.value)))
        sort = self.dropdown("Sort", self.category_sort, [("recommended","Recommended"),("name","Name A–Z"),("size","Small sets first"),("unfinished","Unfinished first")], self.event_action(self.set_category_filter,lambda e:("category_sort",e.control.value)))
        for control in (topic, sort):
            control.width = None
            control.height = 56
            control.col = {"xs":12,"sm":6}
        type_buttons=[]
        for label,kind in [("All", "all"), ("Situations", "situations"), ("Vocabulary", "vocabulary"), ("Spoken expressions", "hong_kong")]:
            button=self.button(label,self.set_category_filter,"category_kind",kind,primary=self.category_kind==kind)
            button.col={"xs":12,"sm":6,"lg":3}
            type_buttons.append(button)
        return self.column([self.heading("Words & phrases", "Choose a situation or vocabulary topic. Character drilling has its own section and progress."),
            ft.ResponsiveRow([query,search_button],spacing=12,run_spacing=12),
            ft.ResponsiveRow(type_buttons,spacing=8,run_spacing=8),
            ft.ResponsiveRow([topic,sort],spacing=12,run_spacing=12),
            ft.Row([self.button("Reset filters",self.reset_category_filters),self.button("Pick all categories",self.pick_all),self.button("Select filtered sets",self.select_visible,True),self.button("Clear selection",self.select_visible,False)],wrap=True,run_spacing=8),
            self.selection_bar(),self.category_grid()],spacing=16,horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def adjacent_category(self, amount):
        matches = self.filtered_categories()
        index = next((i for i,cat in enumerate(matches) if cat.id == self.category_id), None)
        if index is not None and 0 <= index + amount < len(matches):
            self.open_category(matches[index + amount].id)

    def open_category(self, category_id):
        self.navigate("category")
        self.category_id = category_id

    def category_detail(self):
        cat = self.curriculum.category_map[self.category_id]
        won = self.progress.has_trophy(self.language,cat.id,self.curriculum)
        matches = self.filtered_categories()
        position = next((i for i, item in enumerate(matches) if item.id == cat.id), -1)
        return self.column([ft.Row([self.button("← All categories", self.navigate, "categories"), self.button("← Previous set", self.adjacent_category, -1, disabled=position<=0), self.button("Next set →", self.adjacent_category, 1, disabled=position<0 or position+1>=len(matches))], wrap=True), self.heading(self.category_title(cat), cat.description.replace("Hong Kong Cantonese", "Cantonese") + (" · Expanded with related vocabulary from other levels." if len(self.curriculum.practice_entries([cat.id])) > len(cat.entry_ids) else "")), self.tag("🏆 Core quiz completed · 1/1" if won else "Core quiz · 0/1 completed"),
            ft.Row([self.button(label,self.start,mode,[cat.id],primary=mode=="core") for label,mode in [("Train flashcards","flashcards"),("Recognition quiz","core"),("Matching game","match")]], wrap=True),
            *([self.button("Practise sentence meanings", self.start, "sentence", [cat.id], primary=True)] if cat.kind == "situations" else []), self.text("Category dictionary",22,bold=True), *[self.entry_row(entry) for entry in self.curriculum.practice_entries([cat.id])]], spacing=18)

    def entry_card(self, entry):
        ex = entry.example(self.language, self.traditional)
        tags = [self.tag("Sentence" if entry.kind=="sentence" else "Character card" if entry.kind in ("character", "cantonese_character") else "Spoken expression" if entry.kind=="hong_kong" else f"HSK {entry.hsk}")]
        return self.panel([ft.Row([self.text(entry.text(self.language,self.traditional),30,hanzi=True),*tags], wrap=True, spacing=12),
            self.text(entry.reading(self.language),14,muted=True),self.text(entry.meaning,16),
            *([self.text(entry.data["usage_note"],12,muted=True)] if self.language=="cantonese" and entry.data.get("usage_note") else []),
            self.text(ex["text"],18,hanzi=True),self.text(ex["english"],13,muted=True),
            self.text(("Reference example" if ex["source"]=="Reference" else "Original example" if ex["source"]=="Original" else "Tatoeba example") + " · " + (entry.data.get("cantonese_register", "") if self.language=="cantonese" else "Mandarin"),11,muted=True),
            self.learned_control(entry),self.button("Example attribution",self.show_attribution,entry)], padding=18)

    async def mark_learned(self, entry, value):
        self.progress.set_word_learned(self.language,entry.id,value)
        await self.save()

    def learned_control(self, entry):
        key=entry.id
        return ft.Checkbox(label="Learned",value=self.progress.is_word_learned(self.language,key),on_change=self.event_action(self.mark_learned,lambda event:(entry,event.control.value)))

    def entry_row(self, entry):
        details=self.button("Details",self.show_entry,entry)
        text=self.column([self.text(entry.text(self.language,self.traditional),23,hanzi=True),*([self.example_text(entry.text(self.language,self.traditional))] if len(entry.text(self.language,self.traditional))==1 else []),self.text(entry.reading(self.language),13,muted=True),self.text(entry.meaning,14),self.learned_control(entry)],spacing=4)
        if self.narrow:
            content=self.column([text,details],spacing=8)
        else:
            text.expand=True
            content=ft.Row([text,details],vertical_alignment=ft.CrossAxisAlignment.CENTER)
        return ft.Container(content,padding=12,border=ft.Border.only(bottom=ft.BorderSide(width=1,color=self.colors["line"])))

    def show_entry(self, entry):
        self.dialog(entry.text(self.language, self.traditional), [self.entry_card(entry)])

    def sentence_setup(self):
        situations = [cat for cat in self.curriculum.categories if cat.kind == "situations"]
        return self.column([self.heading("Understand whole sentences", "Read a Mandarin or spoken Cantonese sentence, choose its meaning, then review its pronunciation."),
            self.button("Mix all situations", self.start, "sentence", [cat.id for cat in situations], primary=True),
            *[self.panel([self.text(cat.title, 20, bold=True), self.text(cat.theme + " · 4 sentences", 13, muted=True), self.button("Practise this situation", self.start, "sentence", [cat.id])], padding=16) for cat in situations]], spacing=12)

    async def answer_sentence(self, value):
        answer = self.session.answer(value)
        self.progress.record_answer(self.language, answer.correct)
        self.feedback_correct = answer.correct
        self.feedback = ("Correct. " if answer.correct else "Meaning: ") + self.session.current.meaning
        await self.save()

    async def next_sentence(self):
        session = self.session
        session.advance()
        self.feedback, self.feedback_correct = "", None
        if session.finished:
            self.progress.finish(self.language, "sentence", len(session.items), session.correct_count, len(session.answers), self.session_ids)
            self.complete("sentence", len(session.items), session.correct_count, len(session.answers), False, [], session.answers)
            await self.save()

    def sentence(self):
        session = self.session
        entry = session.current
        return self.column([self.session_top("Sentence meaning", session.index+1, len(session.items)),
            self.panel([self.text(entry.text(self.language,self.traditional),32,hanzi=True), self.text("What does this sentence mean?",15,muted=True),
                *[self.button(meaning,self.answer_sentence,meaning,disabled=session.pending is not None) for meaning in session.options()],
                self.feedback_card(), *([self.text(entry.reading(self.language),17), self.text("Original learning sentence · other natural phrasings are possible.",12,muted=True)] if session.pending else []),
                self.button("Finish" if session.index+1==len(session.items) else "Next sentence →",self.next_sentence,primary=True,disabled=session.pending is None)],padding=24)],spacing=20)

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

    def sort_dictionary(self, order):
        self.dictionary_reverse = not self.dictionary_reverse if order == self.dictionary_sort else False
        self.dictionary_sort=order
        self.dictionary_page=0

    def word_uses_known_characters(self,entry):
        glyphs={glyph for glyph in entry.text(self.language,self.traditional) if "\u3400"<=glyph<="\u9fff"}
        return bool(glyphs) and all(self.progress.is_character_learned(self.language,glyph) for glyph in glyphs)

    def toggle_known_words(self):
        self.dictionary_known_characters=not self.dictionary_known_characters
        self.dictionary_page=0

    def dictionary_entries(self):
        entries=self.curriculum.dictionary(self.dictionary_query,self.language,self.traditional,self.dictionary_sort,self.dictionary_category,self.dictionary_hsk)
        entries=[entry for entry in entries if entry.kind in ("vocabulary","hong_kong","sentence")]
        if self.dictionary_learned != "all":
            known=self.dictionary_learned=="learned"
            entries=[entry for entry in entries if self.progress.is_word_learned(self.language,entry.id)==known]
        if self.dictionary_known_characters:
            entries=[entry for entry in entries if self.word_uses_known_characters(entry)]
        if self.dictionary_reverse:
            if self.dictionary_sort=="frequency":
                entries=list(reversed([entry for entry in entries if entry.data.get("frequency")]))+[entry for entry in entries if not entry.data.get("frequency")]
            else:entries.reverse()
        return entries

    def dictionary(self):
        entries=self.dictionary_entries()
        self.dictionary_page=max(0,min(self.dictionary_page,max(0,math.ceil(len(entries)/30)-1)))
        search=ft.TextField(value=self.dictionary_query,label="Search characters, reading, meaning, or category",expand=True,on_change=lambda e:setattr(self,"dictionary_query",e.control.value),on_submit=self.action(self.search_dictionary),border=ft.OutlineInputBorder(border_radius=12))
        return self.column([self.heading("Word & phrase dictionary","Word learning is separate from character learning. Open Details for examples and source notes."),
            self.button("Show all words" if self.dictionary_known_characters else "Words using characters I have learned",self.toggle_known_words,primary=self.dictionary_known_characters),
            ft.Row([search,self.button("Search",self.search_dictionary)], vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row([self.button(label+(" ↓" if self.dictionary_reverse else " ↑") if key==self.dictionary_sort else label,self.sort_dictionary,key,primary=key==self.dictionary_sort) for key,label in [("frequency","Frequency"),("hsk","HSK level"),("alphabetical","Reading"),("meaning","Meaning"),("category","Category")]],wrap=True),
            self.text("Click the active sort again to reverse it. Frequency ↑ = most common first; ↓ = least common first. Unranked entries stay last.",12,muted=True),
            ft.Row([self.dropdown("Learning",self.dictionary_learned,[("all","All entries"),("learned","Learned"),("learning","Still learning")],lambda e:self.set_dictionary_filter("dictionary_learned",e.control.value)),
                self.dropdown("Level",self.dictionary_hsk,[("all","All levels"),*[(str(i),f"HSK {i}") for i in range(1,5)],("hong_kong","Spoken expressions")],lambda e:self.set_dictionary_filter("dictionary_hsk",e.control.value)),
                self.dropdown("Category",self.dictionary_category,[("all","All categories"),*[(x.id,x.title) for x in self.visible_categories()]],lambda e:self.set_dictionary_filter("dictionary_category",e.control.value),width=300)],wrap=True),
            self.text(f"{len(entries):,} entries · " + ("Cantonese character cards use their provisional learning order; vocabulary ranks come from the original sources." if self.language == "cantonese" else "Frequency uses source ranks; unranked sentences appear last."),13,muted=True),
            self.pagination(self.dictionary_page,len(entries),30,self.move_dictionary_page),
            *[self.entry_row(x) for x in entries[self.dictionary_page*30:(self.dictionary_page+1)*30]],
            self.pagination(self.dictionary_page,len(entries),30,self.move_dictionary_page)],spacing=18)

    def set_drill_mode(self, mode):
        self.drill_mode=mode

    def available_character_groups(self):
        key=(self.language,self.traditional)
        if key not in self.character_group_cache:self.character_group_cache[key]={group.id:group for group in character_groups(self.curriculum,*key)}
        return self.character_group_cache[key]

    def select_full_track(self):
        self.character_group_id="common-1000"
        self.drill_page=0;self.drill_filter="all"

    def open_character_group(self,group_id):
        self.character_group_id=group_id
        self.drill_page=0;self.drill_filter="all"
        self.navigate("character_group")

    def set_drill_filter(self,value):
        self.drill_filter,self.drill_page=value,0

    def drill_candidates(self,category_ids=None,filtered=True):
        group=self.available_character_groups()[self.character_group_id]
        chars=[self.curriculum.characters[glyph] for glyph in group.glyphs]
        if filtered and self.drill_filter!="all":chars=[char for char in chars if self.progress.drill_status(self.language,self.curriculum.drill_key(char.glyph))==self.drill_filter]
        return chars

    def saved_character_session(self,group_id):
        values=[value for value in self.progress.state(self.language)["character_sessions"].values() if value["traditional"]==self.traditional and value["group_id"].split("--")[0]==group_id]
        unfinished=[value for value in values if not value["completed"]]
        return max(unfinished or values,key=lambda value:value.get("updated_at",""),default=None)

    def checkpoint_character_session(self):
        if not self.character_session_group or not isinstance(self.session,DrillSession):return
        value=snapshot(self.session,self.character_session_group,self.traditional,self.drill_mode)
        value["updated_at"]=now()
        self.progress.state(self.language)["character_sessions"][session_key(self.character_session_group,self.traditional)]=value

    async def begin_character_group(self,group_id,resume=False,review=False):
        base=group_id.split("--")[0]
        group=self.available_character_groups()[base]
        saved=self.saved_character_session(base) if resume else None
        if resume:
            if not saved:raise ValueError("No saved session for this group")
            session=restore(saved,self.curriculum,self.language)
            mode=saved["mode"];actual=saved["group_id"]
        else:
            chars=[self.curriculum.characters[glyph] for glyph in group.glyphs]
            actual=base
            if review and self.drill_filter!="all":
                chars=[char for char in chars if self.progress.drill_status(self.language,self.curriculum.drill_key(char.glyph))==self.drill_filter]
                actual=base+"--"+self.drill_filter
            session=DrillSession(chars,self.language,list(self.curriculum.characters.values()))
            mode=self.drill_mode
        self.session=session;self.character_group_id=base;self.character_session_group=actual
        self.drill_mode=mode;self.session_ids=[];self.screen="drill";self.result=None
        self.input_value=session.pending.given if session.pending else ""
        self.feedback_correct=session.pending.correct if session.pending else None
        self.feedback=("Correct! " if session.pending and session.pending.correct else "Correct reading(s): ")+" / ".join(session.pending.accepted) if session.pending else ""
        self.checkpoint_character_session()
        await self.save()

    def status_tag(self,status):
        labels={"correct":"Correct","almost":"Almost · tone","incorrect":"Incorrect","unseen":"Not attempted"}
        color={"correct":"green","almost":"amber","incorrect":"red","unseen":"muted"}[status]
        text=self.text(labels[status],12,bold=True);text.color=self.colors[color]
        return text

    def example_text(self,glyph,language=None,traditional=None):
        example=self.curriculum.character_example(glyph,language or self.language,self.traditional if traditional is None else traditional)
        text=example["text"]+(" · Reference example" if example["source"]=="Reference" else "")
        label=self.text(text,13,muted=True,hanzi=True,max_lines=3)
        label.color="#A7ADB4" if self.progress.settings["dark"] else "#7D838A"
        return label

    def move_drill_page(self,amount):
        self.drill_page+=amount

    async def set_character_learned(self,glyph,value,language=None):
        self.progress.set_learned(language or self.language,self.curriculum.character_key(glyph),value)
        await self.save()

    def drill_learned_control(self,char):
        language=self.language
        return ft.Checkbox(label="Learned",value=self.progress.is_learned(language,self.curriculum.character_key(char.glyph)),on_change=self.event_action(self.set_character_learned,lambda event:(char.glyph,event.control.value,language)))

    def character_group_view(self):
        all_chars=self.drill_candidates(filtered=False)
        counts=Counter(self.progress.drill_status(self.language,self.curriculum.drill_key(char.glyph)) for char in all_chars)
        chars=self.drill_candidates()
        self.drill_page=max(0,min(self.drill_page,max(0,math.ceil(len(chars)/24)-1)))
        cards=[]
        for char in chars[self.drill_page*24:(self.drill_page+1)*24]:
            status=self.progress.drill_status(self.language,self.curriculum.drill_key(char.glyph))
            glyph=self.text(char.glyph,36,hanzi=True)
            glyph.color=self.colors[{"correct":"green","almost":"amber","incorrect":"red","unseen":"ink"}[status]]
            cards.append(self.panel([glyph,self.text(("Pinyin" if self.language=="mandarin" else "Jyutping")+": "+" / ".join(char.readings(self.language)),15),self.example_text(char.glyph),self.status_tag(status),self.text("Learned by typing" if self.progress.is_character_learned(self.language,char.glyph) else "Type correctly to learn",12,muted=True)],padding=14,col={"xs":12,"sm":6,"md":4}))
        return self.column([self.heading(self.available_character_groups()[self.character_group_id].title,"Character progress only. A fully correct typed answer automatically learns the character."),
            self.button("← Character groups",self.navigate,"drill_setup"),
            ft.Row([self.button("Type the reading",self.set_drill_mode,"typed",primary=self.drill_mode=="typed"),self.button("8-choice mode",self.set_drill_mode,"choice",primary=self.drill_mode=="choice")],wrap=True),
            ft.Row([self.button(label+f" ({len(all_chars) if value=='all' else counts[value]})",self.set_drill_filter,value,primary=self.drill_filter==value) for value,label in [("all","All"),("correct","Correct"),("almost","Almost correct"),("incorrect","Incorrect"),("unseen","Not attempted")]],wrap=True),
            self.text(f"{len(chars)} characters match this filter",14,bold=True),self.button("Drill this filtered list",self.begin_character_group,self.character_group_id,False,True,primary=True,disabled=not chars),
            ft.Row([self.button("Restart this group",self.begin_character_group,self.character_group_id),self.button("Resume this group",self.begin_character_group,self.character_group_id,True,disabled=not self.saved_character_session(self.character_group_id) or self.saved_character_session(self.character_group_id)["completed"])],wrap=True),
            self.pagination(self.drill_page,len(chars),24,self.move_drill_page),ft.ResponsiveRow(cards,spacing=12,run_spacing=12),self.pagination(self.drill_page,len(chars),24,self.move_drill_page),
            self.text("Word marks do not affect character learning. Only fully correct typed answers learn characters; choice mode remains practice. Restart creates a fresh test without clearing learned characters.",13,muted=True)],spacing=18)

    def drill_setup(self):
        rows=[]
        for group in self.available_character_groups().values():
            if group.id=="common-100":rows.append(self.heading("Common-character groups","Cantonese uses its provisional curriculum order; Mandarin uses the bundled source frequency order."))
            value=self.saved_character_session(group.id)
            status="Completed" if value and value["completed"] else f"Saved at {value['index']+1}/{value['total']}" if value else "Not started"
            learned=sum(self.progress.is_character_learned(self.language,glyph) for glyph in group.glyphs)
            text=self.column([self.text(group.title,18,bold=True),self.text(f"{learned}/{len(group.glyphs)} learned · {status}",13,muted=True),self.text(group.description,12,muted=True)],spacing=4)
            actions=ft.Row([self.button("Restart" if value else "Start",self.begin_character_group,group.id,primary=True),self.button("Resume",self.begin_character_group,group.id,True,disabled=not value or value["completed"]),self.button("Browse",self.open_character_group,group.id)],wrap=True)
            rows.append(self.panel([text,actions],padding=16))
        return self.column([self.heading("Characters","Independent character tests. Typing the pronunciation and tone correctly learns a character. Sessions save after every answer and Next."),
            ft.Row([self.button("Typed tests",self.set_drill_mode,"typed",primary=self.drill_mode=="typed"),self.button("Choice practice",self.set_drill_mode,"choice",primary=self.drill_mode=="choice")],wrap=True),
            self.heading("HSK character groups","HSK 2012 levels 1–4 are bundled. Groups contain characters from words at that level, not word quizzes."),*rows],spacing=16)

    def start(self, mode, category_ids):
        ids=[x.id for x in self.curriculum.categories if x.id in set(category_ids)]
        entries=self.curriculum.practice_entries(ids)
        self.feedback,self.feedback_correct,self.input_value="",None,""
        self.result=None
        self.character_session_group=None
        if mode=="sentence":
            self.session=SentenceSession(entries)
        elif mode=="core":
            self.session=CoreSession(entries,self.language,self.traditional,meaning_pool=list(self.curriculum.entries.values()))
        elif mode=="drill":
            chars=self.curriculum.selected_characters(ids,self.language,self.traditional,enriched=True)
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
        return self.column([ft.Row([self.text(title,26,bold=True),self.button("Leave session",self.navigate,"drill_setup" if self.screen=="drill" else "categories")],wrap=True,alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.text(f"{current}/{total}",14,muted=True),ft.ProgressBar(value=(current-1)/total,color=self.colors["accent"],bgcolor=self.colors["line"],height=6)],spacing=12)

    def feedback_card(self):
        if not self.feedback:
            return ft.Container()
        if self.screen=="drill" and self.session.pending and self.session.pending.status=="almost":
            return self.panel([self.text(self.feedback,15)],color=self.colors["amberbg"],padding=16)
        color=self.colors["greenbg"] if self.feedback_correct else self.colors["redbg"] if self.feedback_correct is False else self.colors["soft"]
        return self.panel([self.text(self.feedback,15,hanzi=any("\u3400"<=x<="\u9fff" for x in self.feedback))],color=color,padding=16)

    async def answer_core(self, value=None):
        session=self.session
        entry=session.current
        answer=session.answer(value if value is not None else self.input_value)
        self.progress.record_answer(self.language,answer.correct)
        self.feedback_correct=answer.correct
        self.feedback=("Correct. " if answer.correct else "Correct meaning: ")+entry.meaning
        await self.save()

    async def next_core(self):
        session=self.session
        session.advance()
        self.feedback,self.feedback_correct,self.input_value="",None,""
        if session.finished:
            earned=self.progress.finish(self.language,"core",len(session.items),session.correct_count,session.attempts,self.session_ids,session.perfect,self.curriculum)
            self.complete("core",len(session.items),session.correct_count,session.attempts,session.perfect,earned,session.answers)
            await self.save()

    def answer_field(self, label, handler, hanzi=False, disabled=False):
        return ft.TextField(value=self.input_value,label=label,max_length=100,autofocus=True,disabled=disabled,autocorrect=False,enable_suggestions=hanzi,
            text_style=ft.TextStyle(font_family="Hanzi" if hanzi else "Inter",size=24 if hanzi else 18,color=self.colors["ink"]),
            on_change=lambda e:setattr(self,"input_value",e.control.value),on_submit=self.action(handler),border=ft.OutlineInputBorder(border_radius=14, side=ft.BorderSide(color=self.colors["line"])))

    def core(self):
        session=self.session
        entry=session.current
        example=entry.example(self.language,self.traditional)
        context=[self.text(example["text"],18,hanzi=True)] if example.get("source")!="Reference" and example["text"]!=entry.text(self.language,self.traditional) else []
        revealed=[self.text(entry.reading(self.language),17),*([self.text(example["english"],14,muted=True)] if context else [])] if session.pending else []
        return self.column([self.session_top("Recognise the meaning",session.index+1,len(session.items)),
            self.panel([self.text(entry.text(self.language,self.traditional),42,hanzi=True),*context,self.text("Choose the meaning. Each card is answered once.",14,muted=True),
                *[self.button(meaning,self.answer_core,meaning,disabled=session.pending is not None) for meaning in session.options()],
                self.feedback_card(),*revealed,self.button("Finish quiz" if session.index+1==len(session.items) else "Next card →",self.next_core,primary=True,disabled=session.pending is None),
                self.text("A perfect first-answer run earns a trophy. Wrong answers show the correction; continue without retrying.",13,muted=True)],padding=24)],spacing=20)

    async def answer_drill(self, value=None):
        session=self.session
        char=session.current
        answer=session.answer((value if value is not None else self.input_value) or "—")
        self.progress.record_answer(self.language,answer.correct,char,status=answer.status,status_key=self.curriculum.drill_key(char.glyph))
        if self.language == "cantonese":
            targets = [glyph for glyph in self.curriculum.cantonese_targets if glyph == char.glyph or self.curriculum.entries["cant-char:" + glyph].text("cantonese", False) == char.glyph]
            record = self.progress.state(self.language)["characters"][char.glyph]
            record["target_ids"] = list(dict.fromkeys(record["target_ids"] + targets))
        if self.drill_mode=="typed" and answer.correct:self.progress.learn_typed_character(self.language,char.glyph)
        self.checkpoint_character_session()
        self.feedback_correct=answer.correct
        self.feedback=("Correct! " if answer.status=="correct" else "Almost correct — check the tone: " if answer.status=="almost" else "Correct reading(s): ")+" / ".join(answer.accepted)+" · "+char.meaning
        await self.save()

    async def submit_drill(self):
        if self.session.pending is None:
            await self.answer_drill()
        else:
            await self.next_drill()

    async def next_drill(self):
        session=self.session
        session.advance()
        self.checkpoint_character_session()
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
                bg=self.colors["greenbg"] if session.pending and valid else self.colors["amberbg"] if chosen and session.pending.status=="almost" else self.colors["redbg"] if chosen else self.colors["surface"]
                options.append(ft.Container(self.button(reading,self.answer_drill,reading,disabled=session.pending is not None),bgcolor=bg,padding=6,border_radius=14,col={"xs":6,"md":3},border=ft.Border.all(2,self.colors["green"] if session.pending and valid else self.colors["amber"] if chosen and session.pending.status=="almost" else self.colors["red"] if chosen else self.colors["line"])))
            answer_controls=[ft.ResponsiveRow(options,spacing=12,run_spacing=12)]
        else:
            label="Jyutping + tone number" if self.language=="cantonese" else "Pinyin + tone number (peng2)"
            answer_controls=[self.answer_field(label if session.pending is None else "Press Enter for the next character",self.submit_drill),self.button("Check reading",self.answer_drill,primary=True,disabled=session.pending is not None)]
        glyph=self.text(char.glyph,100,hanzi=True,text_align=ft.TextAlign.CENTER)
        if session.pending:glyph.color=self.colors[{"correct":"green","almost":"amber","incorrect":"red"}[session.pending.status]]
        return self.column([self.session_top("Character test",session.index+1,len(session.items)),
            self.panel([glyph,self.example_text(char.glyph),*([self.status_tag(session.pending.status)] if session.pending else []),self.text("Enter checks your answer (or reveals it when blank). Enter again continues.",15,muted=True),*answer_controls,self.feedback_card(),
                self.button("Finish drill" if session.index+1==len(session.items) else "Next character →",self.next_drill,primary=True,disabled=session.pending is None),
                self.text("Fully correct typed answers learn characters automatically. Your position is saved for Resume.",13,muted=True)],padding=28)],spacing=20)

    def reveal_flashcard(self):
        self.flash_revealed=True

    async def rate_flashcard(self, known):
        if not self.flash_revealed:
            return
        entry=self.flash_items[self.flash_index]
        self.progress.set_word_learned(self.language,entry.id,known)
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
        controls=[self.text(entry.text(self.language,self.traditional),65,hanzi=True),*([self.example_text(entry.text(self.language,self.traditional))] if len(entry.text(self.language,self.traditional))==1 else []),self.text("Try to recall the reading and meaning before revealing.",14,muted=True)]
        if self.flash_revealed:
            ex=entry.example(self.language,self.traditional)
            controls += [self.text(entry.reading(self.language),20),self.text(entry.meaning,22,bold=True),self.learned_control(entry),self.text(ex["text"],20,hanzi=True),self.text(ex["english"],14,muted=True),
                ft.Row([self.button("Still learning",self.rate_flashcard,False),self.button("I knew it",self.rate_flashcard,True,primary=True)],wrap=True)]
        else:
            controls.append(self.button("Reveal reading & meaning",self.reveal_flashcard,primary=True))
        return self.column([self.session_top("Train flashcards",self.flash_index+1,len(self.flash_items)),self.panel(controls,padding=28),self.text("“I knew it” marks this card learned; “Still learning” clears that mark. These choices do not affect quiz accuracy or trophies.",13,muted=True)],spacing=20)

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
        self.feedback="Matched!" if answer.correct else "Correct pair: "+self.curriculum.entries[answer.item_id].text(self.language,self.traditional)+" → "+self.curriculum.entries[answer.item_id].meaning+". That card is now finished."
        self.feedback_correct=answer.correct
        self.match_left=None
        if session.finished:
            self.progress.finish(self.language,"match",len(session.items),session.correct_count,session.attempts,self.session_ids)
            self.complete("match",len(session.items),session.correct_count,session.attempts,False,[],session.answers)
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
        return self.column([self.heading("Match characters to meaning", "Choose a character card, then its English match."),
            self.text(f"{len(session.matched)}/{len(session.items)} pairs · {session.attempts} attempts",14,muted=True),
            ft.Row([self.column(left,expand=True,spacing=12),self.column(right,expand=True,spacing=12)],vertical_alignment=ft.CrossAxisAlignment.START,spacing=16),self.feedback_card(),
            self.button("Leave game",self.navigate,"categories")],spacing=20)

    def complete(self, mode, total, correct, attempts, perfect, earned, answers):
        if mode=="drill":glyphs=[char.glyph for char in self.session.items]
        else:
            entries=self.flash_items if mode=="flashcards" else self.session.items
            glyphs=list(dict.fromkeys(glyph for entry in entries for glyph in entry.text(self.language,self.traditional) if "\u3400"<=glyph<="\u9fff"))
        self.review_page=0
        self.result=dict(mode=mode,total=total,correct=correct,attempts=attempts,perfect=perfect,earned=earned,answers=answers,ids=list(self.session_ids),language=self.language,traditional=self.traditional,review_glyphs=glyphs,character_group=self.character_session_group,word_ids=[entry.id for entry in (self.flash_items if mode=="flashcards" else self.session.items) if hasattr(entry,"id")])
        self.screen="result"

    async def mark_review_character(self,glyph,value):
        language=self.result["language"]
        self.progress.set_learned(language,self.curriculum.character_key(glyph),value)
        await self.save()

    def move_review_page(self,amount):
        self.review_page+=amount

    async def learn_review_page(self):
        for glyph in self.result["review_glyphs"][self.review_page*24:(self.review_page+1)*24]:
            self.progress.set_learned(self.result["language"],self.curriculum.character_key(glyph),True)
        await self.save()

    def character_review(self):
        result=self.result
        glyphs=result["review_glyphs"]
        self.review_page=max(0,min(self.review_page,max(0,math.ceil(len(glyphs)/24)-1)))
        cards=[]
        for glyph in glyphs[self.review_page*24:(self.review_page+1)*24]:
            key=self.curriculum.character_key(glyph)
            status=self.progress.drill_status(result["language"],self.curriculum.drill_key(glyph))
            checkbox=ft.Checkbox(label="I know this character",value=self.progress.is_learned(result["language"],key),on_change=self.event_action(self.mark_review_character,lambda event,g=glyph:(g,event.control.value)))
            cards.append(self.panel([self.text(glyph,36,hanzi=True),self.example_text(glyph,result["language"],result["traditional"]),*([self.status_tag(status)] if result["mode"]=="drill" else []),checkbox],padding=14,col={"xs":12,"sm":6,"md":4}))
        return self.column([self.heading("Which characters do you know?",f"{result['language'].title()} · tick only the characters you know. Correct answers do not automatically mark them learned. Choices save immediately."),
            self.button("Mark this page learned",self.learn_review_page),self.pagination(self.review_page,len(glyphs),24,self.move_review_page),ft.ResponsiveRow(cards,spacing=12,run_spacing=12),self.pagination(self.review_page,len(glyphs),24,self.move_review_page)],spacing=16)

    async def repeat_current_result(self):
        if self.result["mode"]=="drill" and self.result.get("character_group"):
            await self.begin_character_group(self.result["character_group"].split("--")[0])
        else:self.start(self.result["mode"],self.result["ids"])

    def character_result_review(self):
        glyphs=self.result["review_glyphs"]
        self.review_page=max(0,min(self.review_page,max(0,math.ceil(len(glyphs)/24)-1)))
        language=self.result["language"]
        return self.column([self.heading("Character results","Fully correct typed answers are recorded as learned. Word knowledge is unchanged."),
            self.pagination(self.review_page,len(glyphs),24,self.move_review_page),
            *[self.panel([self.text(glyph,30,hanzi=True),self.example_text(glyph,language,self.result["traditional"]),self.status_tag(self.progress.drill_status(language,self.curriculum.drill_key(glyph))),self.text("Learned by typing" if self.progress.is_character_learned(language,glyph) else "Not yet learned by typing",13,muted=True)],padding=12) for glyph in glyphs[self.review_page*24:(self.review_page+1)*24]],self.pagination(self.review_page,len(glyphs),24,self.move_review_page)],spacing=12)

    def word_result_review(self):
        ids=self.result.get("word_ids",[])
        self.review_page=max(0,min(self.review_page,max(0,math.ceil(len(ids)/24)-1)))
        return self.column([self.heading("Word & phrase review","Mark the words you know. This does not mark their individual characters learned."),self.pagination(self.review_page,len(ids),24,self.move_review_page),*[self.entry_row(self.curriculum.entries[eid]) for eid in ids[self.review_page*24:(self.review_page+1)*24]],self.pagination(self.review_page,len(ids),24,self.move_review_page)],spacing=12)

    def result_view(self):
        r=self.result
        score=r["correct"]/r["attempts"] if r["attempts"] else 0
        headline="Perfect run. Trophy earned!" if r["perfect"] else "A small session, completed."
        controls=[self.tag(MODE_NAMES[r["mode"]].upper()),self.text(headline,30,bold=True),self.text(f"{score:.0%}",58,bold=True),
            self.text(f'{r["correct"]}/{r["total"]} '+("self-rated known" if r["mode"]=="flashcards" else "correct")+f' · {r["attempts"]} attempts',16,muted=True)]
        if r["mode"]=="core":
            controls.append(self.text(f'{len(r["earned"])} new category trophies. All {len(r["ids"])} selected categories have a completed core quiz.' if r["perfect"] else "Every card was answered once. Start a fresh run to try for a perfect trophy.",15))
        controls.append(ft.Row([self.button("Practise again",self.repeat_current_result,primary=True),self.button("Choose categories",self.navigate,"categories"),self.button("View progress",self.navigate,"progress")],wrap=True))
        wrong={a.item_id:a for a in r["answers"] if not a.correct}
        if wrong:
            controls += [self.text("Review missed answers",20,bold=True)]
            for a in list(wrong.values())[:40]:
                name=a.item_id if r["mode"]=="drill" else self.curriculum.entries[a.item_id].text(self.language,self.traditional)
                expected=" / ".join(a.accepted) if r["mode"]!="match" else self.curriculum.entries[a.item_id].meaning
                controls.append(self.text(f"{name} → {expected}",17,hanzi=True))
        controls.append(self.character_result_review() if r["mode"]=="drill" else self.word_result_review())
        return self.panel(controls,padding=28)

    def learned_character_entries(self):
        return [char for glyph,char in self.curriculum.characters.items() if self.progress.is_character_learned(self.language,glyph)]

    def move_learned_page(self,amount):
        self.learned_page+=amount

    def learned_character_list(self):
        glyphs=list(self.progress.state(self.language)["character_learning"])
        self.learned_page=max(0,min(self.learned_page,max(0,math.ceil(len(glyphs)/24)-1)))
        return self.column([self.heading("Characters learned by typing",f"{len(glyphs)} forms in {self.language.title()}"),self.pagination(self.learned_page,len(glyphs),24,self.move_learned_page),*[self.panel([self.text(glyph,30,hanzi=True),self.text(" / ".join(self.curriculum.characters[glyph].readings(self.language)),16),self.example_text(glyph,self.language,self.traditional)],padding=12) for glyph in glyphs[self.learned_page*24:(self.learned_page+1)*24] if glyph in self.curriculum.characters]],spacing=14)

    def progress_view(self):
        state=self.progress.state(self.language)
        target=self.available_character_groups()["common-1000"].glyphs
        learned=sum(self.progress.is_character_learned(self.language,glyph) for glyph in target)
        words=len(state["word_learning"])
        legacy=sum(key.startswith("character:") for key in state.get("learned",{}))
        controls=[self.heading("Your progress",self.language_label+" · saved in this browser"),self.panel([self.text("Characters",24,bold=True),self.text(f"{learned} / {len(target)} target characters learned",22),ft.ProgressBar(value=learned/len(target) if target else 0,color=self.colors["green"]),self.text("A fully correct typed reading, including tones, records a character as learned. Restarting a test keeps learned characters.",14,muted=True),self.button("Character tests: restart or resume",self.navigate,"drill_setup")],padding=24),self.learned_character_list(),self.panel([self.text("Words & phrases",24,bold=True),self.text(f"{words} words / phrases marked learned",22),self.text("Your word knowledge is separate. Mark words learned in the dictionary or after a word quiz.",14,muted=True),self.button("Word dictionary",self.navigate,"dictionary")],padding=24),ft.Row([self.button("Copy / view progress backup",self.show_export),self.button("Restore backup",self.show_import)],wrap=True)]
        if legacy:controls.append(self.text(f"{legacy} earlier manual character marks remain preserved in your backup. New character counts use fully correct typed answers.",14,muted=True))
        trophies=[cat for cat in self.visible_categories() if self.progress.has_trophy(self.language,cat.id,self.curriculum)]
        controls.extend([self.text("Word quiz trophies",22,bold=True),ft.Row([self.tag("🏆 "+cat.title) for cat in trophies],wrap=True) if trophies else self.text("No word trophies yet.",14,muted=True)])
        if self.progress_store.blocked or self.progress_store.recovery_snapshot:controls.append(self.button("Copy preserved browser data",self.show_storage_backup))
        return self.column(controls,spacing=20)

    def close_dialog(self):
        self.page.pop_dialog()

    def dialog(self,title,controls,actions=None):
        self.page.show_dialog(ft.AlertDialog(title=self.text(title,22,bold=True),content=ft.Container(self.column(controls,spacing=14,tight=True,scroll=ft.ScrollMode.AUTO),width=min(max(self.viewport_size[0]-64,160),650),height=min(max(self.viewport_size[1]-180,160),430)),
            bgcolor=self.colors["surface"],actions=actions or [self.button("Close",self.close_dialog)],scrollable=False))

    def show_export(self):
        self.show_json_backup("Progress backup",self.progress.export(),"The backup includes both languages, trophies, scores, and settings.")

    def show_storage_backup(self):
        self.show_json_backup("Preserved browser data",self.progress_store.recovery_export(),"Keep this file for data recovery. To use Restore backup, copy a normal progress backup separately.")

    def show_json_backup(self,title,backup,explanation):
        notice=self.text(explanation,13,muted=True)
        async def copy_backup():
            try:
                await self.clipboard.set(backup)
                notice.value="Copied. Save this JSON in a file for safekeeping."
            except Exception:
                notice.value="The browser could not copy automatically. Select the JSON below and copy it manually."
            self.page.update()
        self.dialog(title,[notice,ft.TextField(value=backup,multiline=True,min_lines=8,max_lines=12,read_only=True,text_size=11)],
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
            if not await self.progress_store.restore(restored):
                self.storage_error=self.progress_store.message
                notice.value="The backup is valid, but this browser could not save it. Your current progress is unchanged. Keep the backup and try again."
                self.page.update()
                return
            restored.migrate_frameworks(self.curriculum)
            self.progress=restored
            self.storage_error=self.progress_store.message
            self.close_dialog()
        self.dialog("Restore progress",[notice,field],[self.button("Restore this backup",restore,primary=True),self.button("Cancel",self.close_dialog)])

    def show_attribution(self,entry):
        ex=entry.example(self.language,self.traditional)
        self.dialog("Example source",[self.text(ex["text"],22,hanzi=True),self.text(ex["english"],16),self.text(ex["attribution"],13),self.text("License: "+ex["license"],13,muted=True),
            self.text("Character conversion adapts the source spelling to the selected simplified or traditional script.",13,muted=True)])

    def show_sources(self):
        coverage=self.curriculum.meta["example_coverage"]
        self.dialog("Curriculum sources & notes",[
            self.text("Separate 1,000-character tracks · 12 situations · 48 original sentences · vocabulary and expressions",17,bold=True),
            self.text("This edition reconstructs the saved requirements. The interrupted conversation’s source files were unavailable.",13,muted=True),
            self.text("HSK 2012 levels 1–4: clem109/hsk-vocabulary and drkameleon/complete-hsk-vocabulary, with CC-CEDICT definitions (CC BY-SA 3.0). Themes are editorial groupings.",13),
            self.text("HanziDB / Jun Da provides the character frequency ranking. Unihan (Unicode 18) and Pleco’s CC-Canto provide character readings. Pleco content: © 2015–2017 Pleco Inc., CC BY-SA 3.0.",13),
            self.text("Mandarin and Cantonese Tatoeba examples retain the authors and sentence IDs in each entry. License: CC BY 2.0 FR. Uncovered items use clearly marked original reference examples.",13),
            self.text(f'Example sources — Mandarin: {coverage["mandarin"]}; Cantonese: {coverage["cantonese"]}.',12,muted=True),
            self.text("Cantonese characters use a separate provisional order: spoken essentials first, then occurrence counts in the bundled Cantonese examples. This is not a representative general-language frequency ranking.",13),
            self.text("Full notices, source URLs, and build provenance are included with the downloadable project. Font: Noto Sans CJK HK and Inter, SIL OFL 1.1.",13)])


async def main(page: ft.Page):
    app=App(page,Curriculum.load())
    await app.initialize()
