from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_, select

from db_config import get_db
from dependencies import get_current_user, get_note_or_404, require_note_owner
from models import Note, User
from schemas import NoteCreate, NoteResponse, NoteUpdate

notes_router = APIRouter(tags=["Notes"])


@notes_router.post("/", status_code=201, response_model=NoteResponse)
def create_note(body: NoteCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    note = Note(**body.model_dump(), owner=current_user.username)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@notes_router.get("/", response_model=list[NoteResponse])
def get_all_notes(tag: str | None = None, search_term: str | None = None,
                  current_user: User = Depends(get_current_user), db=Depends(get_db)):
    query = select(Note)
    if current_user.role != "admin":
        query = query.where(or_(Note.owner == current_user.username, Note.is_public.is_(True)))
    if search_term:
        query = query.where(or_(Note.title.icontains(search_term, autoescape=True),
                                Note.content.icontains(search_term, autoescape=True)))
    notes = db.execute(query.order_by(Note.created_at.desc(), Note.id.desc())).scalars().all()
    if tag is not None:
        notes = [note for note in notes if tag in note.tags]
    return notes


@notes_router.get("/{note_id}", response_model=NoteResponse)
def get_note_by_id(current_user: User = Depends(get_current_user), note: Note = Depends(get_note_or_404)):
    if note.owner != current_user.username and current_user.role != "admin" and not note.is_public:
        raise HTTPException(status_code=403, detail="You do not have permission to view this note.")
    return note


@notes_router.put("/{note_id}", response_model=NoteResponse)
def update_note(body: NoteUpdate, note: Note = Depends(require_note_owner), db=Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    db.commit()
    db.refresh(note)
    return note


@notes_router.delete("/{note_id}", status_code=204)
def delete_note(note: Note = Depends(require_note_owner), db=Depends(get_db)):
    db.delete(note)
    db.commit()
    return Response(status_code=204)
