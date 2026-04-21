import React, { createContext, useContext, useState } from 'react';
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

const SelectContext = createContext({});

export const Select = ({ children, value, onValueChange }) => {
    const [open, setOpen] = useState(false);
    const [label, setLabel] = useState("");

    return (
        <SelectContext.Provider value={{ value, onValueChange, open, setOpen, label, setLabel }}>
            <div className="relative">{children}</div>
        </SelectContext.Provider>
    );
};

export const SelectTrigger = ({ children, className }) => {
    const { open, setOpen, value, label } = useContext(SelectContext);
    return (
        <button
            type="button"
            onClick={() => setOpen(!open)}
            className={cn(
                "flex h-9 w-full items-center justify-between rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-950 disabled:cursor-not-allowed disabled:opacity-50",
                className
            )}
        >
            {/* If we have a selected value's label, show it, otherwise show children (placeholder likely) */}
            {value ? (label || value) : children}
            <ChevronDown className="h-4 w-4 opacity-50" />
        </button>
    );
};

export const SelectValue = ({ placeholder }) => {
    // This is just a placeholder rendering component in this simplified version
    return <span>{placeholder}</span>;
};

export const SelectContent = ({ children, className }) => {
    const { open } = useContext(SelectContext);
    if (!open) return null;
    return (
        <div className={cn("absolute z-50 min-w-[8rem] overflow-hidden rounded-md border bg-white text-slate-950 shadow-md animate-in fade-in-80", className)}>
            <div className="p-1">{children}</div>
        </div>
    );
};

export const SelectItem = ({ children, value, className }) => {
    const { onValueChange, setOpen, setLabel } = useContext(SelectContext);
    return (
        <div
            onClick={() => {
                onValueChange(value);
                setLabel(children); // Capture the label
                setOpen(false);
            }}
            className={cn(
                "relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-2 pr-2 text-sm outline-none hover:bg-slate-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
                className
            )}
        >
            <span className="truncate">{children}</span>
        </div>
    );
};
