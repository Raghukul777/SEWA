import * as React from "react"
import { cn } from "@/lib/utils"

const Button = React.forwardRef(({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
        <button
            className={cn(
                "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
                {
                    "bg-slate-900 text-white shadow hover:bg-slate-900/90": variant === "default",
                    "border border-slate-200 bg-transparent shadow-sm hover:bg-slate-100 hover:text-slate-900": variant === "outline",
                    "hover:bg-slate-100 hover:text-slate-900": variant === "ghost",
                    "h-9 px-4 py-2": size === "default",
                    "h-8 rounded-md px-3 text-xs": size === "sm",
                    "h-10 rounded-md px-8": size === "lg",
                },
                className
            )}
            ref={ref}
            {...props}
        />
    )
})
Button.displayName = "Button"

export { Button }
