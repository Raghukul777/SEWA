import React, { useState } from 'react';
import { Button } from "@/Components/ui/button";
import { Textarea } from "@/Components/ui/textarea";
import { ScrollArea } from "@/Components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/Components/ui/avatar";
import { format } from 'date-fns';
import { Send, User } from 'lucide-react';

export default function ClinicalNotes({ notes, onAddNote, currentUser = "Dr. Current User" }) {
    const [newNote, setNewNote] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!newNote.trim()) return;

        onAddNote({
            text: newNote,
            author: currentUser,
            timestamp: new Date().toISOString()
        });
        setNewNote('');
    };

    return (
        <div className="flex flex-col h-[500px] bg-white rounded-xl border border-slate-200">
            <div className="p-4 border-b border-slate-100">
                <h3 className="font-semibold text-slate-800">Clinical Notes</h3>
                <p className="text-xs text-slate-500">Record and view patient progress</p>
            </div>

            <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                    {notes && notes.length > 0 ? (
                        notes.map((note) => (
                            <div key={note.id || note.timestamp} className="flex gap-3">
                                <Avatar className="h-8 w-8">
                                    <AvatarFallback className="bg-slate-100 text-slate-600 text-xs">
                                        {note.author.split(' ').map(n => n[0]).join('').slice(0, 2)}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1 space-y-1">
                                    <div className="flex items-center justify-between">
                                        <p className="text-sm font-medium text-slate-900">{note.author}</p>
                                        <span className="text-xs text-slate-500">
                                            {format(new Date(note.timestamp), 'MMM d, h:mm a')}
                                        </span>
                                    </div>
                                    <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg rounded-tl-none">
                                        {note.text}
                                    </div>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-8 text-slate-400 text-sm">
                            No clinical notes recorded yet.
                        </div>
                    )}
                </div>
            </ScrollArea>

            <div className="p-4 border-t border-slate-100 bg-slate-50 rounded-b-xl">
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <Textarea
                        value={newNote}
                        onChange={(e) => setNewNote(e.target.value)}
                        placeholder="Type clinical note..."
                        className="min-h-[2.5rem] max-h-32 bg-white resize-none"
                        rows={1}
                    />
                    <Button type="submit" size="icon" disabled={!newNote.trim()}>
                        <Send className="h-4 w-4" />
                    </Button>
                </form>
            </div>
        </div>
    );
}
