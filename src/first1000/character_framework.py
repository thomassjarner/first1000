"""Character-only groups and resumable sessions; independent of word mastery."""
from dataclasses import dataclass

from .practice import Answer,DrillSession

@dataclass(frozen=True)
class CharacterGroup:
    id: str
    title: str
    description: str
    glyphs: tuple[str,...]


def groups(curriculum,language,traditional):
    prefix='cant-char:' if language=='cantonese' else 'c:'
    ranked=list(dict.fromkeys(curriculum.entries[prefix+glyph].text(language,traditional) for glyph in curriculum.targets(language)))
    ranked=[glyph for glyph in ranked if glyph in curriculum.characters and curriculum.characters[glyph].readings(language)]
    order={glyph:i for i,glyph in enumerate(ranked)}
    result=[]
    for level in range(1,5):
        glyphs={glyph for entry in curriculum.entries.values() if entry.kind=='vocabulary' and entry.hsk==level for glyph in entry.text(language,traditional) if glyph in curriculum.characters and curriculum.characters[glyph].readings(language)}
        result.append(CharacterGroup(f'hsk-{level}',f'Drill HSK {level}',f'Characters appearing in HSK 2012 level {level} words; levels can overlap.',tuple(sorted(glyphs,key=lambda glyph:(order.get(glyph,99999),glyph)))))
    for count in range(100,1001,100):
        title='First 1000 — sets 1–40' if count==1000 else f'{count} most common'
        note='Mandarin source-frequency order.' if language=='mandarin' else 'Cantonese curriculum order; provisional, not a general spoken-frequency ranking.'
        result.append(CharacterGroup(f'common-{count}',title,note+' Duplicate displayed script forms appear once.',tuple(ranked[:count])))
    return result


def session_key(group_id,traditional):
    return group_id+('::traditional' if traditional else '::simplified')


def snapshot(session,group_id,traditional,mode):
    base=dict(group_id=group_id,traditional=traditional,mode=mode,completed=session.finished,total=len(session.items),index=session.index)
    if not session.finished:
        base.update(glyphs=[char.glyph for char in session.items],outcomes=[answer.status for answer in session.answers],pending=session.pending is not None,pending_given=session.pending.given if session.pending else '',options=session.options() if mode=='choice' else None)
    return base


def validate_snapshot(value):
    if not isinstance(value,dict) or not isinstance(value.get('group_id'),str) or not 1<=len(value['group_id'])<=100 or type(value.get('traditional')) is not bool or value.get('mode') not in ('typed','choice') or type(value.get('completed')) is not bool:
        raise ValueError('Invalid saved character session')
    total,index=value.get('total'),value.get('index')
    if type(total) is not int or type(index) is not int or not 0<=index<=total<=5000 or total==0:raise ValueError('Invalid saved character position')
    if value['completed']:
        if index!=total:raise ValueError('Invalid completed character session')
        return
    glyphs=value.get('glyphs');outcomes=value.get('outcomes');pending=value.get('pending');given=value.get('pending_given');options=value.get('options')
    if not isinstance(glyphs,list) or len(glyphs)!=total or any(not isinstance(glyph,str) or len(glyph)!=1 for glyph in glyphs) or len(set(glyphs))!=total:raise ValueError('Invalid saved character list')
    if type(pending) is not bool or not isinstance(outcomes,list) or len(outcomes)!=index+int(pending) or index>=total or any(status not in ('correct','almost','incorrect') for status in outcomes):raise ValueError('Invalid saved character answers')
    if not isinstance(given,str) or len(given)>256 or (pending and not given):raise ValueError('Invalid pending character answer')
    if value['mode']=='choice' and (not isinstance(options,list) or len(options)!=8 or any(not isinstance(item,str) or len(item)>100 for item in options) or len(set(options))!=8):raise ValueError('Invalid saved answer options')
    if value['mode']=='typed' and options is not None:raise ValueError('Invalid typed session options')


def restore(value,curriculum,language):
    validate_snapshot(value)
    if value['completed']:raise ValueError('This set is completed. Choose Restart to practise again.')
    if any(glyph not in curriculum.characters or not curriculum.characters[glyph].readings(language) for glyph in value['glyphs']):raise ValueError('Some saved characters are unavailable. Your saved session is preserved; choose another group.')
    session=DrillSession([curriculum.characters[glyph] for glyph in value['glyphs']],language,list(curriculum.characters.values()))
    session.items=[curriculum.characters[glyph] for glyph in value['glyphs']]
    session.index=value['index']
    session.answers=[Answer(value['glyphs'][i],status=='correct',value['pending_given'] if value['pending'] and i==value['index'] else '',tuple(curriculum.characters[value['glyphs'][i]].readings(language)),status) for i,status in enumerate(value['outcomes'])]
    session.pending=session.answers[-1] if value['pending'] else None
    session._options=value['options']
    return session
