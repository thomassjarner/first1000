import random

import pytest

from first1000.curriculum import Curriculum
from first1000.practice import CoreSession, DrillSession, MatchSession, normalize_reading
from first1000.progress import Progress


@pytest.fixture(scope="session")
def curriculum():
    return Curriculum.load()


@pytest.mark.parametrize("given,expected", [("péng","peng2"),("peng2","peng2"),("lǜ","lv4"),("lü4","lv4"),("lu:4","lv4"),("lv4","lv4"),("ma0","ma5"),("ma","ma5"),("péng yǒu","peng2you3")])
def test_mandarin_normalization(given,expected):
    assert normalize_reading(given)==expected


def test_core_wrong_locks_then_advances_and_disqualifies_trophy(curriculum):
    entries=curriculum.selected_entries(["core-01"])
    session=CoreSession(entries,"mandarin",False,shuffle=False)
    first=session.current
    with pytest.raises(ValueError):session.answer(" ")
    assert session.attempts==0
    wrong=next(meaning for meaning in session.options() if meaning!=first.meaning)
    assert not session.answer(wrong).correct
    with pytest.raises(ValueError):session.answer(first.meaning)
    assert session.current.id==first.id
    session.advance()
    while not session.finished:
        assert session.answer(session.current.meaning).correct
        session.advance()
    assert not session.perfect and session.correct_count==24
    assert session.attempts==25 and session.mistakes==1
    progress=Progress()
    progress.finish("mandarin","core",25,24,25,["core-01"],session.perfect,curriculum)
    assert not progress.has_trophy("mandarin","core-01",curriculum)


def test_fixed_questions_perfect_trophy_language_separation(curriculum):
    entries=curriculum.selected_entries(["core-01","core-02"])
    a=CoreSession(entries,"mandarin",True,random.Random(4))
    b=CoreSession(entries,"mandarin",True,random.Random(7))
    assert {x.id for x in a.items}=={x.id for x in b.items} and [x.id for x in a.items]!=[x.id for x in b.items]
    progress=Progress()
    while not a.finished:
        result=a.answer(a.current.meaning);progress.record_answer("mandarin",result.correct);a.advance()
    progress.finish("mandarin","core",50,50,50,["core-01","core-02"],a.perfect,curriculum)
    assert progress.has_trophy("mandarin","core-01",curriculum)
    assert progress.has_trophy("mandarin","core-02",curriculum)
    assert not progress.has_trophy("cantonese","core-01",curriculum)
    assert progress.state("cantonese")["attempts"]==0


@pytest.mark.parametrize("language,traditional", [("mandarin",False),("mandarin",True),("cantonese",False),("cantonese",True)])
def test_mixed_drill_deduplicates_and_eight_options(curriculum,language,traditional):
    cats=["core-01","core-02","core-01"]
    chars=curriculum.selected_characters(cats,language,traditional)
    assert len(chars)==len({x.glyph for x in chars})
    session=DrillSession(chars,language,list(curriculum.characters.values()),random.Random(12))
    seen=set()
    while not session.finished:
        char=session.current
        assert char.glyph not in seen
        seen.add(char.glyph)
        options=session.options()
        assert len(options)==len(set(options))==8
        assert options==session.options()
        normalized={normalize_reading(x,language) for x in char.readings(language)}
        assert sum(normalize_reading(x,language) in normalized for x in options)==1
        assert session.answer(char.readings(language)[-1]).correct
        with pytest.raises(ValueError):session.answer(options[0])
        session.advance()
    assert session.correct_count==len(chars)


def test_polyphonic_and_wrong_drill_do_not_retry(curriculum):
    char=curriculum.characters["行"]
    assert "xing2" in char.pinyin and "hang2" in char.pinyin
    assert "hang4" in char.jyutping and "hang6" in char.jyutping
    session=DrillSession([char],"cantonese",list(curriculum.characters.values()))
    assert not session.answer("wrong9").correct
    session.advance()
    assert session.finished and session.correct_count==0


def test_match_errors_and_completion(curriculum):
    session=MatchSession(curriculum.selected_entries(["core-01"]),"mandarin",False,random.Random(2))
    assert len({x.meaning for x in session.items})==len(session.items)
    assert not session.answer(session.items[0].id,session.items[1].id).correct
    assert session.items[0].id in session.matched
    with pytest.raises(ValueError):session.answer(session.items[0].id,session.items[0].id)
    for item in session.items[1:]:assert session.answer(item.id,item.id).correct
    assert session.finished and session.attempts==len(session.items)
    assert session.correct_count==len(session.items)-1


def test_progress_roundtrip_and_target_variants(curriculum):
    progress=Progress()
    progress.record_answer("cantonese",False,curriculum.characters["國"])
    progress.record_answer("cantonese",True,curriculum.characters["国"])
    assert progress.summary("cantonese",curriculum)["characters"]==1
    restored=Progress.from_json(progress.export())
    assert restored.data==progress.data
    assert restored.summary("mandarin",curriculum)["characters"]==0


@pytest.mark.parametrize("mutation", [
    lambda x:x.update(app="other"),
    lambda x:x["settings"].update(language="mixed"),
    lambda x:x["languages"]["mandarin"].update(correct=1),
    lambda x:x["languages"]["mandarin"].update(attempts=-1),
    lambda x:x["languages"]["mandarin"].update(attempts=True),
    lambda x:x["languages"].pop("cantonese"),
])
def test_invalid_backup_rejected_without_mutation(mutation):
    import json
    progress=Progress();original=progress.export();incoming=json.loads(original)
    mutation(incoming)
    with pytest.raises(ValueError):Progress.from_json(json.dumps(incoming))
    assert progress.export()==original


def test_curriculum_coverage_and_dictionary(curriculum):
    assert len(curriculum.vocabulary_ids)==1231
    core=[x for x in curriculum.categories if x.kind=="characters"]
    assert len(core)==40 and all(len(x.entry_ids)==25 for x in core)
    assert len(curriculum.categories)==133 and len(set(curriculum.target_characters))==1000
    assert len(set(x for cat in core for x in cat.entry_ids))==1000
    for entry in curriculum.entries.values():
        assert entry.meaning and entry.reading("mandarin") and entry.reading("cantonese")
        for language in ("mandarin","cantonese"):
            example=entry.example(language,True)
            assert example["english"] and example["attribution"] and example["text"]
            for traditional in (False,True):
                for char in entry.text(language,traditional):
                    if "\u3400"<=char<="\u9fff":assert char in curriculum.characters
    assert curriculum.entries["w:现在"].text("cantonese",True)=="而家"
    assert curriculum.entries["w:什么"].reading("cantonese")=="mat1 je5"
    assert curriculum.entries["hk:唔該"].text("mandarin",False)=="谢谢"
    assert curriculum.entries["w:吧"].data["pinyin_numbers"]=="ba5"
    assert curriculum.entries["w:深"].text("mandarin",True)=="深"
    assert any(x.id=="c:朋" for x in curriculum.dictionary("peng2"))
    assert all(x.hsk==2 for x in curriculum.dictionary(hsk="2"))
    alphabet=curriculum.dictionary(sort="alphabetical")
    assert alphabet.index(curriculum.entries["w:爱"])<alphabet.index(curriculum.entries["w:北京"])


def test_font_covers_displayed_chinese(curriculum):
    import json
    from pathlib import Path
    from fontTools.ttLib import TTFont
    font=TTFont(Path(__file__).parents[1]/"src/assets/fonts/First1000Hanzi.otf")
    cmap=font.getBestCmap()
    strings=json.dumps([x.data for x in curriculum.entries.values()],ensure_ascii=False)+"千學学"
    assert all(ord(ch) in cmap for ch in strings if "\u3400"<=ch<="\u9fff")
